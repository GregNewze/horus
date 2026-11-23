"""Testa o Ouroboros no IBM AMLworld (HI-Small), que tem 54 ciclos de lavagem rotulados.

Pergunta: dos ciclos que o detector acha, quantos são lavagem (precisão)? Dos ciclos rotulados,
quantos ele acha (recall)? E quantos dos ciclos de lavagem só fecham com o consórcio?

Uso: .venv/bin/python -m validacao.ouroboros_aml --csv .../HI-Small_Trans.csv --patterns .../HI-Small_Patterns.txt
"""

import argparse
import json
import time
from collections import Counter

import numpy as np
import pandas as pd

from motor.ouroboros import achar_ciclos, visivel_para
from validacao.amlworld import INSTITUICOES, ler, montar


def ciclos_rotulados(patterns):
    ciclos, atual = [], None
    for linha in open(patterns):
        if linha.startswith("BEGIN LAUNDERING ATTEMPT - CYCLE"):
            atual = []
        elif linha.startswith("END LAUNDERING ATTEMPT"):
            if atual is not None:
                ciclos.append(atual)
            atual = None
        elif atual is not None and linha.strip():
            c = linha.strip().split(",")
            atual.append((pd.Timestamp(c[0].replace("/", "-")), f"{c[1]}:{c[2]}", f"{c[3]}:{c[4]}"))
    return ciclos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--patterns", required=True)
    ap.add_argument("--semente", type=int, default=1)
    ap.add_argument("--janela", type=float, default=120)
    ap.add_argument("--saida", default="data/externo/ouroboros_amlworld.json")
    a = ap.parse_args()

    t_ini = time.time()
    d, banco_da_conta, _, nomes = ler(a.csv, com_nomes=True)
    contas, txs, *_ = montar(d, banco_da_conta, a.semente)
    inst = contas["banco"].astype(str).values
    membros = {k for k, v in INSTITUICOES.items() if v[1]}
    o, dd, v = d["o"].values, d["dd"].values, d["valor"].values
    ts_h = (d["ts"].values - d["ts"].values.min()) / np.timedelta64(1, "h")
    lav = d["lav"].values
    print(f"lido em {time.time() - t_ini:.0f} s, {len(d):,} Pix")

    t_ini = time.time()
    ciclos = achar_ciclos(o, dd, ts_h, v, janela_h=a.janela)
    seg = time.time() - t_ini
    print(f"{len(ciclos):,} ciclos em {seg:.0f} s")

    # Gabarito: arestas dos ciclos rotulados, pela chave (origem, destino, hora)
    cod = {n: i for i, n in enumerate(nomes)}
    chave = pd.Series(np.arange(len(d)), index=pd.MultiIndex.from_arrays([o, dd, d["ts"].values]))
    chave = chave[~chave.index.duplicated()]
    rot = []
    for c in ciclos_rotulados(a.patterns):
        pos = []
        for ts, x, y in c:
            k = (cod.get(x), cod.get(y), ts)
            if k in chave.index:
                pos.append(int(chave.loc[k]))
        rot.append(pos)
    aresta_rot = {e: i for i, c in enumerate(rot) for e in c}

    tam = Counter()
    lav_tot = rot_achados = 0
    vis = Counter()
    ciclos_rot_achados = set()
    contas_ach = set()
    for c in ciclos:
        tam[len(c)] += 1
        sujo = all(lav[e] == 1 for e in c)
        for e in c:
            contas_ach.add(int(o[e]))
        if sujo:
            lav_tot += 1
            ids = {aresta_rot.get(e) for e in c}
            if len(ids) == 1 and None not in ids:
                ciclos_rot_achados.add(ids.pop())
            soz, cons = visivel_para(c, o, dd, inst, membros)
            vis["algum membro sozinho" if any(k in membros for k in soz) else
                ("só consórcio" if cons else "nem o consórcio")] += 1

    sujas_total = set(o[lav == 1]) | set(dd[lav == 1])
    rot_vis = Counter()
    for c in rot:
        if not c:
            continue
        soz, cons = visivel_para(c, o, dd, inst, membros)
        rot_vis["algum membro sozinho" if any(k in membros for k in soz) else
                ("só consórcio" if cons else "nem o consórcio")] += 1

    res = {
        "janela_h": a.janela, "segundos": round(seg),
        "ciclos_achados": len(ciclos), "ciclos_todo_lavagem": lav_tot,
        "precisao_ciclo": round(lav_tot / max(len(ciclos), 1), 3),
        "rotulados": len(rot), "rotulados_casados_no_csv": sum(1 for c in rot if len(c) >= 3),
        "rotulados_achados": len(ciclos_rot_achados),
        "contas_em_ciclo": len(contas_ach), "contas_em_ciclo_sujas": len(contas_ach & sujas_total),
        "tamanhos": dict(sorted(tam.items())),
        "quem_ve_ciclos_achados_de_lavagem": dict(vis),
        "quem_ve_ciclos_rotulados": dict(rot_vis),
    }
    print(json.dumps(res, ensure_ascii=False, indent=1))
    json.dump(res, open(a.saida, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
