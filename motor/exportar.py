"""Exporta o JSON que a tela lê: grafo, notas por foto nos dois modos, laudos e números.

A tela não calcula nada: tudo sai daqui. O gabarito entra só no campo `papel` de cada nó, para a
demo poder mostrar no final quem era laranja de verdade; o motor nunca o lê.

Uso: python -m motor.exportar [--pasta data/out] [--passo 6] [--saida ../web/public/demo.json]
"""

import argparse
import json
from pathlib import Path

import networkx as nx
import pandas as pd

from .consorcio import destokenizar, modo_consorcio, modo_sozinha, pedidos_ao_hub, token_conta
from .muninn import laudo, rastrear
from .sinais import FORTE, FRACA, carregar, pontuar_local


def pontos_do_motivo(frase):
    """Pontos que cada frase de motivo somou, com os mesmos números de sinais.py e consorcio.py."""
    import re
    if frase.startswith("repassou"):
        return 30 if int(re.search(r"(\d+)%", frase).group(1)) >= 60 else 15
    if frase.startswith("conta com"):
        return 15
    if "Pix de teste" in frase and frase.startswith("recebeu"):
        return 10
    if frase.startswith("dinheiro de"):
        return 10
    if "contestado" in frase:
        return 40
    if frase.startswith("trocou repasses"):
        return 15 * min(3, int(re.search(r"com (\d+) conta", frase).group(1)))
    if "outras instituições relataram" in frase:
        return 10
    if frase.startswith("faz parte de um anel"):
        return 10 if int(re.search(r"com (\d+) contas", frase).group(1)) >= 4 else 0
    return 0


def exportar(pasta, passo_h, n_laudos=6):
    contas, txs, contest, inst = carregar(pasta)
    gab = json.load(open(Path(pasta) / "gabarito.json", encoding="utf-8"))
    papel = gab["papeis"]
    membros = [k for k, v in inst.items() if v["consorcio"]]
    nos_membros = set(contas.index[contas["banco"].isin(membros)])
    laranja = {c for c, p in papel.items() if p in ("laranja", "coletora")}
    alvo = laranja & nos_membros
    detok = destokenizar(contas.index)  # só a demo reverte; o hub não tem esta tabela
    golpes = txs[txs["id"].map(gab["tipo_tx"]).eq("golpe") & txs["destino"].isin(nos_membros)]
    total_golpe = float(golpes["valor"].sum())

    fotos_ts = pd.date_range(txs["ts"].min().normalize() + pd.Timedelta(hours=passo_h),
                             txs["ts"].max().ceil("D"), freq=f"{passo_h}h")
    primeira = {"s": {}, "c": {}}
    fotos, motivos_finais, arestas = [], {}, {}
    for ate in fotos_ts:
        susp = pontuar_local(contas, txs, contest, ate, membros)
        susp["banco"] = contas.loc[susp.index, "banco"]
        nota_s, marc_s = {}, set()
        for b in membros:
            r = modo_sozinha(b, susp, txs, ate)
            for n, v in r["final"].items():
                if r["dono"].get(n) == b:
                    nota_s[n] = v
            marc_s |= r["marcadas"]
        rc = modo_consorcio(membros, susp, txs, ate)
        nota_c = {detok[t]: v for t, v in rc["final"].items() if t in detok}
        marc_c = {detok[t] for t in rc["marcadas_tok"] if t in detok}
        for t, m in rc["porque"].items():
            if t in detok:
                motivos_finais[detok[t]] = m
        for o, d, tipo, valor in rc["arestas"]:
            if o in detok and d in detok:
                k = (detok[o], detok[d])
                a = arestas.setdefault(k, {"o": k[0], "d": k[1], "tipo": tipo, "valor": 0.0, "n": 0, "desde": str(ate)})
                a["valor"] += valor
                a["n"] += 1
        for modo, marc in (("s", marc_s), ("c", marc_c)):
            for c in marc:
                primeira[modo].setdefault(c, ate)

        def protegido(modo):
            g = golpes[golpes["ts"] <= ate]
            ok = [primeira[modo].get(d) is not None and primeira[modo][d] <= ts for d, ts in zip(g["destino"], g["ts"])]
            return round(float(g.loc[ok, "valor"].sum()) / total_golpe, 4) if total_golpe else 0

        fotos.append({
            "ate": ate.isoformat(),
            "s": {n: int(v) for n, v in nota_s.items() if v >= FRACA},
            "c": {n: int(v) for n, v in nota_c.items() if v >= FRACA},
            "recall_s": round(len(set(primeira["s"]) & alvo) / len(alvo), 4),
            "recall_c": round(len(set(primeira["c"]) & alvo & nos_membros) / len(alvo), 4),
            "protegido_s": protegido("s"), "protegido_c": protegido("c"),
            "golpe_ate_agora": round(float(golpes.loc[golpes["ts"] <= ate, "valor"].sum()), 2),
        })

    # Nós: toda conta que passou de fraca em algum momento, mais os laranjas (para o placar final)
    ids = set(laranja)
    for f in fotos:
        ids |= set(f["s"]) | set(f["c"])
    g = nx.Graph()
    g.add_nodes_from(ids)
    g.add_edges_from((a["o"], a["d"]) for a in arestas.values() if a["o"] in ids and a["d"] in ids)
    pos = nx.spring_layout(g, seed=7, k=0.35, iterations=200)
    nos = [{"id": n, "banco": contas.at[n, "banco"], "membro": n in nos_membros, "papel": papel[n],
            "x": round(float(pos[n][0]), 4), "y": round(float(pos[n][1]), 4),
            "token": token_conta(n), "motivos": [{"frase": m, "pontos": pontos_do_motivo(m)} for m in motivos_finais.get(n, [])],
            "marcada_s": str(primeira["s"][n]) if n in primeira["s"] else None,
            "marcada_c": str(primeira["c"][n]) if n in primeira["c"] else None} for n in sorted(ids)]
    lista_arestas = [{**a, "valor": round(a["valor"], 2)} for a in arestas.values() if a["o"] in ids and a["d"] in ids]

    # Laudos do Muninn: as maiores contestações contra contas de membros
    marcadas_fim = set(primeira["c"])
    contest_m = contest[contest["destino"].isin(nos_membros)].copy()
    contest_m["valor_tx"] = contest_m["tx_id"].map(txs.set_index("id")["valor"])
    contest_m = contest_m.sort_values("valor_tx", ascending=False)
    laudos = []
    for r in contest_m.head(n_laudos).itertuples():
        raiz, saltos = rastrear(txs, r.tx_id, ate=r.aberta_em + pd.Timedelta(hours=24))
        laudos.append({"tx": r.tx_id, "aberta_em": str(r.aberta_em), "conta": raiz["destino"], "recebido_em": str(raiz["ts"]), "banco": contas.at[raiz["destino"], "banco"],
                       "valor": round(float(raiz["valor"]), 2),
                       "saltos": [{**s, "quando": str(s["quando"])} for s in saltos],
                       "texto": laudo(raiz, saltos, contas, motivos_finais, marcadas_fim)})

    # Anéis do gabarito: quando cada modo achou metade dos membros visíveis (mesma regra de avaliar.py)
    tx_dest = dict(zip(txs["id"], txs["destino"]))
    contest_dest = contest.assign(dest=contest["tx_id"].map(tx_dest))
    aneis = []
    for r in gab["redes"]:
        mem = [m for m in r["membros"] if m in nos_membros]
        datas = contest_dest.loc[contest_dest["dest"].isin(r["membros"]), "aberta_em"]
        linha = {"rede": r["rede"], "membros": r["membros"], "visiveis": len(mem),
                 "primeira_contestacao": str(datas.min()) if len(datas) else None}
        for modo in ("s", "c"):
            achados = sorted(primeira[modo][m] for m in mem if m in primeira[modo])
            meta_n = max(1, (len(mem) + 1) // 2)
            linha[f"achado_{modo}"] = str(achados[meta_n - 1]) if mem and len(achados) >= meta_n else None
        aneis.append(linha)

    sementes = None
    arq = Path("data/externo/sementes_v4.json")
    if arq.exists():
        sementes = json.load(open(arq, encoding="utf-8"))
        sementes = [{k: x[k] for k in ("semente", "recall_sozinha", "recall_consorcio", "dinheiro_sozinha",
                                       "dinheiro_consorcio", "clientes")} for x in sementes]

    return {
        "meta": {"sementes": sementes,
                 "pedidos_hub": {b: {"tokens": pedidos_ao_hub().get(b, 0), "clientes": int((contas["banco"] == b).sum())} for b in membros},
                 "inicio": str(txs["ts"].min()), "fim": str(txs["ts"].max()), "passo_h": passo_h,
                 "fraca": FRACA, "forte": FORTE, "clientes_membros": len(nos_membros), "laranjas_membros": len(alvo),
                 "golpe_total_membros": round(total_golpe, 2),
                 "instituicoes": [{"nome": k, "consorcio": v["consorcio"]} for k, v in inst.items()]},
        "nos": nos, "arestas": lista_arestas, "fotos": fotos, "laudos": laudos, "aneis": aneis,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", default="data/out")
    ap.add_argument("--passo", type=int, default=6)
    ap.add_argument("--saida", default="data/out/demo.json")
    a = ap.parse_args()
    d = exportar(a.pasta, a.passo)
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.saida).write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
    ult = d["fotos"][-1]
    print(f"{len(d['nos'])} nós, {len(d['arestas'])} arestas, {len(d['fotos'])} fotos, {len(d['laudos'])} laudos; "
          f"recall {ult['recall_s']:.0%} -> {ult['recall_c']:.0%}; dinheiro {ult['protegido_s']:.0%} -> {ult['protegido_c']:.0%}")


if __name__ == "__main__":
    main()
