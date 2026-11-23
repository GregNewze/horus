"""Validação externa do Hórus no IBM AMLworld (HI-Small), um conjunto público que não fomos nós que geramos.

O AMLworld (Altman et al., NeurIPS 2023) simula 5 milhões de transações entre 515 mil contas de
30 mil bancos, com lavagem rotulada por transação. Aqui:

- cada banco do AMLworld vira parte de uma de 6 "instituições" (4 no consórcio, 2 fora), com a
  mesma divisão de clientes do nosso gerador (cerca de 50% dos clientes no consórcio);
- valores são convertidos para reais (câmbio implícito do próprio conjunto, US$ 1 = R$ 5);
- conta laranja = conta que mandou ou recebeu alguma transação de lavagem;
- rede = componente ligado das transações de lavagem;
- as regras e os limites do motor ficam EXATAMENTE como estão; nada foi ajustado para este conjunto.

O que o AMLworld não tem, e por isso fica desligado (o resultado tende a sair PIOR que na demo):
- contestação MED (não há vítima de golpe, é lavagem);
- data de abertura da conta (a regra de conta nova não dispara);
- Pix de teste de centavos (existem cheques de 1 centavo, mas são legítimos).

Uso: .venv/bin/python -m validacao.amlworld --csv HI-Small_Trans.csv [--sementes 1 2 3] [--passo 12]
"""

import argparse
import json
import random
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from motor.avaliar import rodar_dados
from motor.sinais import marcar_repasses

REAL_POR_DOLAR = 5.0
# Mesmos pesos do gerador: 2 bancos grandes fora, 4 pequenas no consórcio.
INSTITUICOES = {"Fora A": (0.26, False), "Fora B": (0.24, False), "Membro 1": (0.12, True),
                "Membro 2": (0.12, True), "Membro 3": (0.13, True), "Membro 4": (0.13, True)}


def ler(csv, com_nomes=False):
    cols = ["ts", "bo", "co", "bd", "cd", "vr", "mr", "vp", "mp", "fmt", "lav"]
    d = pd.read_csv(csv, header=0, names=cols, usecols=["ts", "bo", "co", "bd", "cd", "vr", "mr", "vp", "mp", "lav"],
                    dtype={"bo": "string", "co": "string", "bd": "string", "cd": "string",
                           "mr": "category", "mp": "category", "vr": "float64", "vp": "float64", "lav": "int8"})
    d["ts"] = pd.to_datetime(d["ts"], format="%Y/%m/%d %H:%M")
    # Câmbio implícito: transações pagas em X e recebidas em dólar
    cambio = {"US Dollar": 1.0}
    x = d[(d["mr"] == "US Dollar") & (d["mp"] != "US Dollar")]
    for moeda, g in x.groupby("mp", observed=True):
        cambio[moeda] = float((g["vr"] / g["vp"]).median())
    d["valor"] = d["vp"] * d["mp"].astype(str).map(cambio).astype(float) * REAL_POR_DOLAR
    d = d[(d["bo"] != d["bd"]) | (d["co"] != d["cd"])]  # reinvestimento na própria conta não é transferência
    n = len(d)
    cod, contas_str = pd.factorize(pd.concat([d["bo"] + ":" + d["co"], d["bd"] + ":" + d["cd"]], ignore_index=True))
    banco = pd.concat([d["bo"], d["bd"]], ignore_index=True).values
    banco_da_conta = pd.Series(banco).groupby(cod).first().values  # cada conta pertence a um banco só
    out = pd.DataFrame({"ts": d["ts"].values, "o": cod[:n], "dd": cod[n:], "valor": d["valor"].values,
                        "lav": d["lav"].values})
    if com_nomes:
        return out, banco_da_conta, cambio, contas_str
    return out, banco_da_conta, cambio


def montar(d, banco_da_conta, semente):
    """Converte para o formato do motor, com ids inteiros para caber na memória."""
    total = len(banco_da_conta)
    banco_da_conta = pd.Series(banco_da_conta)

    # Divide os bancos entre as 6 instituições, mirando a fatia de clientes de cada uma
    rng = random.Random(semente)
    por_banco = banco_da_conta.value_counts()
    bancos = list(por_banco.index)
    rng.shuffle(bancos)
    alvo = {k: v[0] * total for k, v in INSTITUICOES.items()}
    tem = {k: 0 for k in INSTITUICOES}
    inst_do_banco = {}
    for b in bancos:
        k = max(alvo, key=lambda k: alvo[k] - tem[k])
        inst_do_banco[b] = k
        tem[k] += por_banco[b]

    contas = pd.DataFrame({"banco": banco_da_conta.map(inst_do_banco).values,
                           "criada_em": pd.Timestamp("2000-01-01")}, index=pd.RangeIndex(total, name="id"))
    contas["banco"] = contas["banco"].astype("category")
    txs = pd.DataFrame({"id": np.arange(len(d)), "ts": d["ts"].values,
                        "origem": d["o"].values, "destino": d["dd"].values, "valor": d["valor"].values})
    txs["banco_origem"] = contas["banco"].values[txs["origem"].values]
    txs["banco_destino"] = contas["banco"].values[txs["destino"].values]

    lav = txs[d["lav"].values == 1]
    sujas = set(lav["origem"]) | set(lav["destino"])
    papeis = {i: ("laranja" if i in sujas else "legitimo") for i in range(total)}
    g = nx.Graph()
    g.add_edges_from(zip(lav["origem"], lav["destino"]))
    redes = [{"rede": f"R{i + 1}", "membros": sorted(c)} for i, c in
             enumerate(sorted(nx.connected_components(g), key=len, reverse=True))]
    gab = {"papeis": papeis, "redes": redes, "tipo_tx": {i: "golpe" for i in lav["id"]}}
    inst = {k: {"consorcio": v[1]} for k, v in INSTITUICOES.items()}
    contest = pd.DataFrame({"tx_id": pd.Series(dtype="int64"), "aberta_em": pd.Series(dtype="datetime64[ns]"),
                            "destino": pd.Series(dtype="int64")})
    fatias = contas["banco"].value_counts(normalize=True).round(3).to_dict()
    return contas, txs, contest, inst, gab, fatias


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--sementes", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--passo", type=int, default=12)
    ap.add_argument("--janela", type=float, default=1, help="horas para contar repasse (motor: 1)")
    ap.add_argument("--saida", default="data/externo/amlworld_resultado.json")
    a = ap.parse_args()

    d, banco_da_conta, cambio = ler(a.csv)
    print(f"{len(d)} transações, {int(d['lav'].sum())} de lavagem; câmbio: "
          + ", ".join(f"{k} {v:.3f}" for k, v in cambio.items()), flush=True)
    resultados = {"cambio_para_dolar": cambio, "real_por_dolar": REAL_POR_DOLAR, "passo_h": a.passo, "janela_repasse_h": a.janela, "rodadas": []}
    for s in a.sementes:
        contas, txs, contest, inst, gab, fatias = montar(d, banco_da_conta, s)
        txs = marcar_repasses(txs, pd.Timedelta(hours=a.janela))
        print(f"semente {s}: fatias {fatias}; repasses rápidos {int(txs['repasse'].sum())}", flush=True)
        res = rodar_dados(contas, txs, contest, inst, gab, a.passo)
        res.pop("redes")  # centenas de redes; o resumo abaixo basta
        res["fatias"] = fatias
        res["semente"] = s
        resultados["rodadas"].append(res)
        print(json.dumps({k: res[k] for k in ("sozinha", "consorcio", "consorcio_externas", "dinheiro")},
                         ensure_ascii=False, default=str), flush=True)
        del contas, txs, gab
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.saida).write_text(json.dumps(resultados, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
