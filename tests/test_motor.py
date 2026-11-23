"""Testes do motor: contas certas, sem olhar o futuro, sem vazar dado pessoal para o hub."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "gerador"))

from gerar import gerar, salvar  # noqa: E402
from motor.consorcio import modo_consorcio, modo_sozinha, token  # noqa: E402
from motor.sinais import FORTE, carregar, marcar_repasses, pontuar_local  # noqa: E402

T0 = pd.Timestamp("2026-10-01 10:00:00")


def txs_de(linhas):
    """linhas: (minutos depois de T0, origem, destino, valor)."""
    return pd.DataFrame([{"id": f"T{i}", "ts": T0 + pd.Timedelta(minutes=m), "origem": o, "destino": d, "valor": v}
                         for i, (m, o, d, v) in enumerate(linhas)])


# --- Repasse rápido ---------------------------------------------------------------------------

def test_mesma_entrada_nao_e_repassada_duas_vezes():
    t = marcar_repasses(txs_de([(0, "V", "L", 1000), (10, "L", "X", 600), (20, "L", "Y", 600)]))
    saidas = t[t["origem"] == "L"].sort_values("ts")
    assert saidas["valor_repassado"].sum() == pytest.approx(1000)
    assert list(saidas["entrada_1h"]) == pytest.approx([1000, 400])


def test_janela_de_uma_hora():
    t = marcar_repasses(txs_de([(0, "V", "L", 1000), (61, "L", "X", 900)]))
    assert not t.loc[t["origem"] == "L", "repasse"].iloc[0]
    t = marcar_repasses(txs_de([(0, "V", "L", 1000), (59, "L", "X", 900)]))
    assert t.loc[t["origem"] == "L", "repasse"].iloc[0]


def test_entrada_e_saida_no_mesmo_segundo_conta():
    t = marcar_repasses(txs_de([(0, "V", "L", 1000), (0, "L", "X", 900)]))
    assert t.loc[t["origem"] == "L", "valor_repassado"].iloc[0] == pytest.approx(900)


def test_pix_de_centavos_nao_conta_como_entrada():
    t = marcar_repasses(txs_de([(0, "V", "L", 1.5), (5, "L", "X", 150)]))
    assert t.loc[t["origem"] == "L", "entrada_1h"].iloc[0] == 0
    assert t.loc[t["destino"] == "L", "teste"].iloc[0]


def test_saida_abaixo_de_100_nao_e_repasse_mas_gasta_a_entrada():
    t = marcar_repasses(txs_de([(0, "V", "L", 200), (5, "L", "X", 90), (10, "L", "Y", 150)]))
    s = t[t["origem"] == "L"].sort_values("ts")
    assert not s["repasse"].iloc[0]
    assert s["entrada_1h"].iloc[1] == pytest.approx(110)


def test_taxa_de_repasse_nunca_passa_de_100():
    t = marcar_repasses(txs_de([(0, "V", "L", 1000), (5, "L", "X", 700), (6, "L", "Y", 700), (7, "L", "Z", 700)]))
    assert t["valor_repassado"].sum() <= 1000 + 1e-6


# --- Dados sintéticos pequenos para os testes de ponta a ponta --------------------------------

@pytest.fixture(scope="module")
def mundo(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("mundo")
    salvar(pasta, *gerar(500, 3, 12, 7))
    return pasta


def test_gerador_e_deterministico(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    salvar(a, *gerar(300, 2, 8, 11))
    salvar(b, *gerar(300, 2, 8, 11))
    for f in ("contas.csv", "transacoes.csv", "contestacoes.json", "gabarito.json"):
        assert (a / f).read_bytes() == (b / f).read_bytes(), f


def test_arquivos_publicos_nao_tem_gabarito(mundo):
    for f in ("contas.csv", "transacoes.csv"):
        cab = (mundo / f).read_text(encoding="utf-8").splitlines()[0]
        assert "papel" not in cab and "tipo" not in cab
    for c in json.load(open(mundo / "contestacoes.json", encoding="utf-8")):
        assert set(c) == {"vitima", "valor", "aberta_em", "tx_id"}


def test_cpfs_sao_ficticios(mundo):
    contas = pd.read_csv(mundo / "contas.csv", dtype=str)
    assert contas["cpf"].str.startswith("999.").all()


def test_ordem_dos_ids_nao_entrega_laranja(mundo):
    gab = json.load(open(mundo / "gabarito.json", encoding="utf-8"))
    ids = sorted(gab["papeis"])
    pos = [i for i, c in enumerate(ids) if gab["papeis"][c] in ("laranja", "coletora")]
    # Se os laranjas estivessem no fim (ordem de criação), a posição média seria perto de 1
    assert 0.3 < (sum(pos) / len(pos)) / len(ids) < 0.7


def test_pontuacao_nao_olha_o_futuro(mundo):
    contas, txs, contest, inst = carregar(mundo)
    membros = [k for k, v in inst.items() if v["consorcio"]]
    ate = txs["ts"].min() + pd.Timedelta(days=6)
    cheio = pontuar_local(contas, txs, contest, ate, membros)
    passado = marcar_repasses(txs[txs["ts"] <= ate].drop(columns=["entrada_1h", "repasse", "valor_repassado", "teste"]))
    so_passado = pontuar_local(contas, passado, contest, ate, membros)
    pd.testing.assert_series_equal(cheio["nota"].sort_index(), so_passado["nota"].sort_index())


def test_hub_nao_recebe_id_nome_nem_cpf(mundo):
    contas_csv = pd.read_csv(mundo / "contas.csv", dtype=str)
    contas, txs, contest, inst = carregar(mundo)
    membros = [k for k, v in inst.items() if v["consorcio"]]
    ate = txs["ts"].max()
    susp = pontuar_local(contas, txs, contest, ate, membros)
    susp["banco"] = contas.loc[susp.index, "banco"]
    pacotes = json.dumps(modo_consorcio(membros, susp, txs, ate)["pacotes"], ensure_ascii=False)
    assert len(susp) > 0
    for col in ("id", "nome", "cpf"):
        vazou = [v for v in contas_csv[col] if f'"{v}"' in pacotes]
        assert not vazou, f"{col} apareceu no pacote: {vazou[:3]}"
    assert not any(f'"{t}"' in pacotes for t in txs["id"])


def test_sozinha_marca_conta_forte_sem_repasse():
    contas_banco = "Coop X"
    susp = pd.DataFrame({"nota": [70], "motivos": [["2 Pix contestados"]], "banco": [contas_banco]}, index=["C1"])
    txs = pd.DataFrame({"id": [], "ts": pd.to_datetime([]), "origem": [], "destino": [], "valor": [],
                        "banco_origem": [], "banco_destino": [], "repasse": [], "teste": []})
    r = modo_sozinha(contas_banco, susp, txs, T0)
    assert "C1" in r["marcadas"] and r["final"]["C1"] >= FORTE


def test_token_muda_com_a_chave():
    assert token("C00001") == token("C00001")
    assert token("C00001") != token("C00001", segredo=b"outra-chave")
    assert len(token("C00001")) == 16


# --- Muninn -------------------------------------------------------------------------------------

def test_muninn_segue_os_dois_ramos_e_nao_cria_dinheiro():
    from motor.muninn import rastrear
    t = txs_de([(0, "V", "L1", 8000), (10, "L1", "L2", 4000), (11, "L1", "L2", 3800),
                (13, "L2", "C", 3900), (14, "L2", "C", 3700), (300, "C", "X", 7000)])
    raiz, saltos = rastrear(t, "T0")
    assert {s["tx"] for s in saltos} == {"T1", "T2", "T3", "T4", "T5"}
    for camada in (1, 2, 3):
        assert sum(s["valor"] for s in saltos if s["camada"] == camada) <= 8000 + 1e-6


def test_muninn_respeita_janela_de_24h_e_5_camadas():
    from motor.muninn import rastrear
    t = txs_de([(0, "V", "A", 5000), (60 * 25, "A", "B", 4000)])
    assert rastrear(t, "T0")[1] == []
    cadeia = [(0, "V", "N0", 5000)] + [(i + 1, f"N{i}", f"N{i + 1}", 5000) for i in range(7)]
    assert max(s["camada"] for s in rastrear(txs_de(cadeia), "T0")[1]) == 5


def test_formato_brl():
    from motor.muninn import brl
    assert brl(8538.09) == "R$ 8.538,09" and brl(200) == "R$ 200,00"
