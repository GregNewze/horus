"""Ouroboros: acha o dinheiro que dá a volta e volta para a conta de onde saiu.

Um ciclo temporal é uma sequência de Pix A -> B -> ... -> A em que cada salto acontece depois
do anterior, dentro de uma janela curta, e o valor vai encolhendo devagar (a "taxa" de cada
laranja), sem crescer. As três travas juntas (ordem no tempo, janela e valor) é que separam o
ciclo de lavagem da volta comum do dinheiro (salário que vira compra que vira salário).

Cada instituição só enxerga os Pix que tocam os próprios clientes. Um ciclo que passa por
contas de várias instituições só fecha para quem vê todos os saltos: por isso `visivel_para`
diz se a instituição sozinha ou o consórcio conseguiria montar o ciclo.
"""

from bisect import bisect_right
from collections import defaultdict

import numpy as np

JANELA_H = 120     # o ciclo inteiro cabe em 5 dias
MAX_SALTOS = 10
MIN_SALTOS = 3     # A -> B -> A é comum demais (devolução, estorno, divisão de conta)
ENCOLHE_MIN = 0.5  # cada salto leva pelo menos metade do anterior...
CRESCE_MAX = 1.05  # ...e não mais que 5% acima (arredondamento, câmbio)
MAX_CICLOS_POR_INICIO = 5


def _indice(origem, destino, ts_h, valor):
    """Por conta de origem: tempos em ordem, destinos e valores."""
    ordem = np.lexsort((ts_h, origem))
    o, d, t, v = origem[ordem], destino[ordem], ts_h[ordem], valor[ordem]
    cortes = np.flatnonzero(np.diff(o)) + 1
    ini = np.concatenate([[0], cortes])
    fim = np.concatenate([cortes, [len(o)]])
    idx = {}
    for a, b in zip(ini, fim):
        idx[int(o[a])] = (t[a:b].tolist(), d[a:b].tolist(), v[a:b].tolist(), ordem[a:b].tolist())
    return idx


def achar_ciclos(origem, destino, ts_h, valor, janela_h=JANELA_H, max_saltos=MAX_SALTOS,
                 min_saltos=MIN_SALTOS, encolhe=ENCOLHE_MIN, cresce=CRESCE_MAX, inicios=None):
    """Devolve a lista de ciclos; cada ciclo é a lista de posições (linhas) dos Pix, em ordem.

    origem, destino: ids inteiros das contas; ts_h: horas (float); valor: R$.
    inicios: posições dos Pix que podem abrir um ciclo (padrão: todos). Cada ciclo é
    contado uma vez só, a partir do Pix mais antigo dele.
    """
    origem = np.asarray(origem)
    destino = np.asarray(destino)
    ts_h = np.asarray(ts_h, dtype=float)
    valor = np.asarray(valor, dtype=float)
    idx = _indice(origem, destino, ts_h, valor)
    if inicios is None:
        inicios = range(len(origem))
    ciclos = []
    for e0 in inicios:
        a, b, t0, v0 = int(origem[e0]), int(destino[e0]), ts_h[e0], valor[e0]
        if a == b:
            continue
        limite = t0 + janela_h
        achados = 0
        # pilha: (conta atual, tempo do último salto, valor do último salto, caminho, contas no caminho)
        pilha = [(b, t0, v0, [e0], {a, b})]
        while pilha and achados < MAX_CICLOS_POR_INICIO:
            c, t, v, cam, vistos = pilha.pop()
            saidas = idx.get(c)
            if saidas is None:
                continue
            ts_c, ds_c, vs_c, pos_c = saidas
            i = bisect_right(ts_c, t)
            while i < len(ts_c) and ts_c[i] <= limite:
                vi = vs_c[i]
                if encolhe * v <= vi <= cresce * v:
                    d = ds_c[i]
                    n = len(cam) + 1
                    if d == a:
                        if n >= min_saltos:
                            ciclos.append(cam + [pos_c[i]])
                            achados += 1
                    elif d not in vistos and n < max_saltos:
                        pilha.append((d, ts_c[i], vi, cam + [pos_c[i]], vistos | {d}))
                i += 1
    return ciclos


def visivel_para(ciclo, origem, destino, inst_da_conta, membros):
    """Quem consegue montar o ciclo inteiro: a lista de instituições sozinhas e se o consórcio vê.

    Uma instituição vê um Pix se a origem ou o destino é cliente dela. O consórcio vê um Pix
    se ele toca qualquer membro.
    """
    lados = [(inst_da_conta[origem[e]], inst_da_conta[destino[e]]) for e in ciclo]
    sozinhas = [k for k in set(x for par in lados for x in par) if all(k in par for par in lados)]
    consorcio = all(p[0] in membros or p[1] in membros for p in lados)
    return sozinhas, consorcio


def contas_em_ciclo(ciclos, origem):
    contas = defaultdict(int)
    for c in ciclos:
        for e in c:
            contas[int(origem[e])] += 1
    return contas
