"""Sinais por conta, calculados só com o que a instituição dona da conta enxerga.

Uma instituição vê todas as transações dos próprios clientes (entradas e saídas) e, de cada
contraparte externa, apenas o identificador e a instituição. Nada aqui lê o gabarito.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

JANELA_REPASSE = pd.Timedelta(minutes=60)  # dinheiro que entra e sai em até 1 hora
VALOR_TESTE = 2.0                          # Pix de centavos para testar se a conta recebe
VALOR_MIN_REPASSE = 100.0

# Pontos de cada regra. A soma vai de 0 a 100+; FRACA e FORTE definem os níveis.
FRACA, FORTE = 25, 60


def carregar(pasta="data/out"):
    pasta = Path(pasta)
    contas = pd.read_csv(pasta / "contas.csv", parse_dates=["criada_em"]).set_index("id")
    txs = pd.read_csv(pasta / "transacoes.csv", parse_dates=["ts"])
    contest = pd.DataFrame(json.load(open(pasta / "contestacoes.json", encoding="utf-8")))
    contest["aberta_em"] = pd.to_datetime(contest["aberta_em"])
    inst = json.load(open(pasta / "instituicoes.json", encoding="utf-8"))
    txs["banco_origem"] = txs["origem"].map(contas["banco"])
    txs["banco_destino"] = txs["destino"].map(contas["banco"])
    contest = contest.merge(txs[["id", "destino"]], left_on="tx_id", right_on="id").drop(columns="id")
    return contas, marcar_repasses(txs), contest, inst


def marcar_repasses(txs):
    """Para cada saída, quanto a conta tinha recebido na hora anterior.

    Um repasse é uma saída de pelo menos R$ 100 que acontece até 1 hora depois de uma entrada,
    limitada ao valor que entrou. É o padrão do laranja: o dinheiro só passa.
    """
    ent = txs[["destino", "ts", "valor"]].rename(columns={"destino": "conta"})
    sai = txs[["origem", "ts", "valor", "id"]].rename(columns={"origem": "conta"})
    ent = ent[ent["valor"] >= VALOR_TESTE].sort_values(["conta", "ts"])
    entrada_1h = np.zeros(len(sai))
    sai = sai.reset_index(drop=True)
    grupos_ent = {k: (g["ts"].values, np.cumsum(g["valor"].values)) for k, g in ent.groupby("conta")}
    for conta, g in sai.groupby("conta"):
        if conta not in grupos_ent:
            continue
        ts_e, acum = grupos_ent[conta]
        fim = np.searchsorted(ts_e, g["ts"].values, side="right")
        ini = np.searchsorted(ts_e, (g["ts"] - JANELA_REPASSE).values, side="left")
        tot = np.where(fim > 0, acum[np.maximum(fim - 1, 0)], 0) - np.where(ini > 0, acum[np.maximum(ini - 1, 0)], 0)
        entrada_1h[g.index.values] = tot
    sai["entrada_1h"] = entrada_1h
    txs = txs.merge(sai[["id", "entrada_1h"]], on="id")
    txs["repasse"] = (txs["valor"] >= VALOR_MIN_REPASSE) & (txs["entrada_1h"] >= 0.3 * txs["valor"])
    txs["valor_repassado"] = np.where(txs["repasse"], np.minimum(txs["valor"], txs["entrada_1h"]), 0.0)
    txs["teste"] = txs["valor"] < VALOR_TESTE
    return txs


def pontuar_local(contas, txs, contest, ate, donas):
    """Nota local de cada conta das instituições `donas`, com tudo o que aconteceu até `ate`.

    Devolve DataFrame com nota, motivos (lista de frases) e os números que embasam cada motivo.
    """
    t = txs[txs["ts"] <= ate]
    minhas = contas.index[contas["banco"].isin(donas)]
    ent = t[t["destino"].isin(minhas) & ~t["teste"]]
    sai = t[t["origem"].isin(minhas)]
    recebido = ent.groupby("destino")["valor"].sum()
    repassado = sai.groupby("origem")["valor_repassado"].sum()
    testes = t[t["destino"].isin(minhas) & t["teste"]].groupby("destino").size()
    semana = ent[ent["ts"] > ate - pd.Timedelta(days=7)]
    origens_7d = semana.groupby("destino")["origem"].nunique()
    contestadas = contest[(contest["aberta_em"] <= ate) & contest["destino"].isin(minhas)].groupby("destino").size()

    df = pd.DataFrame(index=minhas)
    df["recebido"] = recebido.reindex(minhas).fillna(0)
    df["repassado"] = repassado.reindex(minhas).fillna(0)
    df["taxa_repasse"] = (df["repassado"] / df["recebido"].where(df["recebido"] > 0)).fillna(0).clip(0, 1)
    df["testes"] = testes.reindex(minhas).fillna(0).astype(int)
    df["origens_7d"] = origens_7d.reindex(minhas).fillna(0).astype(int)
    df["contestacoes"] = contestadas.reindex(minhas).fillna(0).astype(int)
    df["idade_dias"] = (ate - contas.loc[minhas, "criada_em"]).dt.days

    nota = np.zeros(len(df))
    forte_rep = (df["taxa_repasse"] >= 0.6) & (df["recebido"] >= 1000)
    medio_rep = (df["taxa_repasse"] >= 0.3) & (df["recebido"] >= 1000) & ~forte_rep
    nova = (df["idade_dias"] < 90) & (df["recebido"] >= 3000)
    teste = df["testes"] > 0
    muitas = (df["origens_7d"] >= 5) & (df["taxa_repasse"] >= 0.3)
    contestada = df["contestacoes"] > 0
    for cond, pts in [(forte_rep, 30), (medio_rep, 15), (nova, 15), (teste, 10), (muitas, 10), (contestada, 40)]:
        nota += np.where(cond, pts, 0)
    df["nota"] = nota

    def motivos(r):
        m = []
        if r.taxa_repasse >= 0.3 and r.recebido >= 1000:
            m.append(f"repassou {r.taxa_repasse:.0%} do que recebeu em menos de 1 hora")
        if r.idade_dias < 90 and r.recebido >= 3000:
            m.append(f"conta com {r.idade_dias} dias já recebeu R$ {r.recebido:,.0f}".replace(",", "."))
        if r.testes:
            m.append(f"recebeu {r.testes} Pix de teste de centavos")
        if r.origens_7d >= 5 and r.taxa_repasse >= 0.3:
            m.append(f"dinheiro de {r.origens_7d} pessoas diferentes em 7 dias")
        if r.contestacoes:
            m.append(f"{r.contestacoes} Pix recebido(s) contestado(s) no MED")
        return m

    suspeitas = df[df["nota"] >= FRACA].copy()
    suspeitas["motivos"] = [motivos(r) for r in suspeitas.itertuples()]
    return suspeitas


def arestas_suspeitas(txs, ate, suspeitas_ids):
    """Repasses rápidos e Pix de teste que tocam alguma conta suspeita, até `ate`."""
    t = txs[(txs["ts"] <= ate) & (txs["repasse"] | txs["teste"])]
    t = t[t["origem"].isin(suspeitas_ids) | t["destino"].isin(suspeitas_ids)]
    return t[["id", "ts", "origem", "destino", "valor", "banco_origem", "banco_destino", "repasse", "teste"]]
