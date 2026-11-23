"""Muninn: parte de um Pix contestado e segue o dinheiro, camada por camada.

Segue as mesmas ideias do rastreio do MED 2.0 (até 5 camadas, janela de 24 h entre o dinheiro
entrar e sair de cada conta, valor mínimo), mas a partir do que a instituição e o consórcio
enxergam. O laudo é montado só com fatos calculados aqui; um modelo de linguagem, se usado,
apenas reescreve o texto, nunca decide quem é suspeito.
"""

from collections import deque

import pandas as pd

CAMADAS = 5
JANELA = pd.Timedelta(hours=24)
VALOR_MIN = 200.0


def rastrear(txs, tx_id, ate=None):
    """Árvore do dinheiro que saiu da conta que recebeu o Pix `tx_id`.

    Cada salto leva no máximo o valor que ainda resta do dinheiro rastreado (o mesmo real não é
    seguido duas vezes). Devolve lista de saltos: camada, origem, destino, valor, quando.
    """
    t = txs if ate is None else txs[txs["ts"] <= ate]
    raiz = t[t["id"] == tx_id].iloc[0]
    saidas = {k: g.sort_values("ts") for k, g in t[t["valor"] >= VALOR_MIN].groupby("origem")}
    saltos = []
    fila = deque([(raiz["destino"], raiz["ts"], float(raiz["valor"]), 1)])
    usadas = set()
    while fila:
        conta, quando, resta, camada = fila.popleft()
        if camada > CAMADAS or conta not in saidas:
            continue
        g = saidas[conta]
        g = g[(g["ts"] >= quando) & (g["ts"] <= quando + JANELA)]
        for r in g.itertuples():
            if resta < VALOR_MIN:
                break
            if r.id in usadas:  # já seguido por outro ramo: pula, não para
                continue
            leva = min(resta, r.valor)
            usadas.add(r.id)
            resta -= leva
            saltos.append({"camada": camada, "origem": r.origem, "destino": r.destino, "valor": round(leva, 2),
                           "valor_tx": round(r.valor, 2), "quando": r.ts, "tx": r.id})
            fila.append((r.destino, r.ts, leva, camada + 1))
    return raiz, saltos


def brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def laudo(raiz, saltos, contas, motivos, marcadas):
    """Texto do laudo em português, só com fatos. `motivos`: {conta: [frases]}."""
    banco = contas["banco"].to_dict()
    linhas = [f"Pix contestado de {brl(raiz['valor'])} recebido em {raiz['ts']:%d/%m %H:%M} "
              f"pela conta {raiz['destino']} ({banco.get(raiz['destino'], '?')})."]
    if not saltos:
        linhas.append("O dinheiro não saiu da conta em até 24 horas.")
    for s in saltos:
        linhas.append(f"Camada {s['camada']}: {brl(s['valor'])} foram de {s['origem']} ({banco.get(s['origem'], '?')}) "
                      f"para {s['destino']} ({banco.get(s['destino'], '?')}) às {s['quando']:%d/%m %H:%M}.")
    envolvidas = [raiz["destino"]] + [s["destino"] for s in saltos]
    vistas = []
    for c in envolvidas:
        if c in vistas:
            continue
        vistas.append(c)
        if motivos.get(c):
            marca = "marcada" if c in marcadas else "suspeita"
            linhas.append(f"Conta {c} ({marca}): " + "; ".join(motivos[c]) + ".")
    return linhas
