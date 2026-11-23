"""Mede o Hórus contra o gabarito: cada instituição sozinha contra o consórcio.

Roda a detecção em fotos a cada 6 horas, como rodaria em produção, e responde:
- quantos laranjas das instituições do consórcio cada modo marca, e com quantos alarmes falsos;
- quantas redes cada modo encontra;
- quantas horas antes da primeira contestação MED cada rede é encontrada.

Uso: python -m motor.avaliar [--pasta data/out] [--passo 6]
"""

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from .consorcio import destokenizar, modo_consorcio, modo_sozinha
from .sinais import carregar, pontuar_local


def rodar(pasta, passo_h):
    contas, txs, contest, inst = carregar(pasta)
    gab = json.load(open(Path(pasta) / "gabarito.json", encoding="utf-8"))
    return rodar_dados(contas, txs, contest, inst, gab, passo_h)


def rodar_dados(contas, txs, contest, inst, gab, passo_h):
    """Mesma avaliação, com os dados já carregados (usado também na validação externa)."""
    papel = gab["papeis"]
    membros = [k for k, v in inst.items() if v["consorcio"]]
    nos_membros = set(contas.index[contas["banco"].isin(membros)])
    laranja = {c for c, p in papel.items() if p in ("laranja", "coletora")}
    alvo = laranja & nos_membros
    detok = destokenizar(contas.index)  # só a avaliação reverte tudo; o hub não tem isso

    fotos = pd.date_range(txs["ts"].min().normalize() + pd.Timedelta(hours=passo_h),
                          txs["ts"].max().ceil("D"), freq=f"{passo_h}h")
    primeira = {"sozinha": {}, "consorcio": {}}
    ultimo = None
    compartilhadas = set()  # contas que algum dia saíram como suspeita fraca ou forte (custo de privacidade)
    for ate in fotos:
        susp = pontuar_local(contas, txs, contest, ate, membros)
        susp["banco"] = contas.loc[susp.index, "banco"]
        soz = set()
        for b in membros:
            soz |= modo_sozinha(b, susp, txs, ate)["marcadas"]
        cons = modo_consorcio(membros, susp, txs, ate)
        cons_ids = {detok[t] for t in cons["marcadas_tok"]}
        for modo, marc in (("sozinha", soz), ("consorcio", cons_ids)):
            for c in marc:
                primeira[modo].setdefault(c, ate)
        ultimo = (ate, susp, soz, cons, cons_ids)
        for c in susp.index:
            compartilhadas.add(c)

    ate, susp, soz, cons, cons_ids = ultimo
    cons_membros = cons_ids & nos_membros
    externas = cons_ids - nos_membros

    def resumo(marc):
        vp = marc & alvo
        fp = marc - laranja
        return {"marcadas": len(marc), "laranjas_achados": len(vp), "laranjas_total": len(alvo),
                "recall": round(len(vp) / len(alvo), 3) if alvo else None,
                "precisao": round(len(vp) / len(marc), 3) if marc else None,
                "falsos_por_tipo": dict(Counter(papel[c] for c in fp))}

    contest_rede = {}
    tx_destino = dict(zip(contest["tx_id"], contest["aberta_em"]))
    redes = []
    for r in gab["redes"]:
        mem = [m for m in r["membros"] if m in nos_membros]
        datas_contest = [contest.loc[i, "aberta_em"] for i in contest.index if contest.loc[i, "destino"] in r["membros"]]
        primeira_contest = min(datas_contest) if datas_contest else None
        linha = {"rede": r["rede"], "tamanho": len(r["membros"]), "no_consorcio": len(mem),
                 "primeira_contestacao": str(primeira_contest) if primeira_contest is not None else None}
        for modo in ("sozinha", "consorcio"):
            achados = sorted(primeira[modo][m] for m in mem if m in primeira[modo])
            meta = max(1, (len(mem) + 1) // 2)  # rede achada quando metade dos membros visíveis foi marcada
            linha[f"{modo}_achados"] = len([m for m in mem if m in (soz if modo == "sozinha" else cons_membros)])
            quando = achados[meta - 1] if len(achados) >= meta and mem else None
            linha[f"{modo}_quando"] = str(quando) if quando is not None else None
            linha[f"{modo}_horas_antes"] = (round((primeira_contest - quando).total_seconds() / 3600, 1)
                                           if quando is not None and primeira_contest is not None else None)
        redes.append(linha)

    # Dinheiro protegível: golpe que entrou numa conta do consórcio que JÁ estava marcada
    golpes = txs[txs["id"].map(gab["tipo_tx"]).eq("golpe") & txs["destino"].isin(nos_membros)]
    dinheiro = {"golpe_total_no_consorcio": round(golpes["valor"].sum(), 2)}
    for modo in ("sozinha", "consorcio"):
        antes = [primeira[modo].get(d) is not None and primeira[modo][d] <= ts
                 for d, ts in zip(golpes["destino"], golpes["ts"])]
        dinheiro[f"{modo}_protegivel"] = round(golpes.loc[antes, "valor"].sum(), 2)
        dinheiro[f"{modo}_pct"] = round(golpes.loc[antes, "valor"].sum() / golpes["valor"].sum(), 3)

    return {
        "membros": membros,
        "dinheiro": dinheiro,
        "compartilhadas": {"total": len(compartilhadas), "laranjas": len(compartilhadas & laranja),
                           "inocentes_por_tipo": dict(Counter(papel[c] for c in compartilhadas - laranja)),
                           "clientes_dos_membros": len(nos_membros)},
        "sozinha": resumo(soz),
        "consorcio": resumo(cons_membros),
        "consorcio_externas": {"marcadas": len(externas), "laranjas": len(externas & laranja),
                               "laranjas_externos_total": len(laranja - nos_membros)},
        "redes": redes,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", default="data/out")
    ap.add_argument("--passo", type=int, default=6)
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()
    res = rodar(a.pasta, a.passo)
    txt = json.dumps(res, ensure_ascii=False, indent=1, default=str)
    if a.saida:
        Path(a.saida).write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
