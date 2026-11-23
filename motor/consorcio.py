"""Análise de rede e consórcio de suspeitas fracas.

Modo sozinha: cada instituição roda a análise só com as próprias contas suspeitas e os Pix
que as tocam. Modo consórcio: cada membro manda ao hub apenas tokens HMAC das contas com
nota fraca ou forte, a nota, os códigos de motivo e os repasses rápidos que as tocam (com o
id fim a fim do Pix também em token). O hub junta tudo, roda a MESMA análise e devolve a
cada membro o que mudou nas contas dele. Nenhum nome, CPF ou saldo sai da instituição.
"""

import hashlib
import hmac
from collections import defaultdict

import networkx as nx
import pandas as pd
from nacl import bindings as nb

from .oprf import Hub, Membro, token_direto
from .sinais import FORTE, FRACA, arestas_suspeitas

SEGREDO = b"horus-consorcio-demo"  # chave m dos membros; na vida real fica em HSM e troca a cada rodada

# Hub da demo com k fixo, para a simulação ser reproduzível. Na vida real k é sorteado a cada rodada.
_HUB = Hub(k=nb.crypto_core_ed25519_scalar_reduce(hashlib.sha512(b"horus-hub-demo-rodada-1").digest()))
_MEMBROS: dict[str, Membro] = {}
_TABELA: dict[str, str] = {}  # conta -> token; cada membro guarda a dele, aqui é uma só por ser simulação


def token(valor, segredo=SEGREDO):
    """HMAC dos membros. Usado só no id fim a fim do Pix, para o hub não contar o mesmo Pix duas vezes."""
    return hmac.new(segredo, str(valor).encode(), hashlib.sha256).hexdigest()[:16]


def tokens_contas(contas, membro="demo"):
    """Token OPRF de cada conta (motor/oprf.py). Pede ao hub só as que o membro ainda não tem na tabela."""
    faltam = [c for c in dict.fromkeys(contas) if c not in _TABELA]
    if faltam:
        m = _MEMBROS.setdefault(membro, Membro(membro, SEGREDO))
        _TABELA.update(zip(faltam, m.tokenizar(faltam, _HUB)))
    return [_TABELA[c] for c in contas]


def token_conta(conta, membro="demo"):
    return tokens_contas([conta], membro)[0]


def pedidos_ao_hub():
    """Quantos tokens cada membro pediu ao hub: é o registro que denuncia ataque de dicionário."""
    return dict(_HUB.pedidos)


def analisar(notas, motivos, dono, arestas, relatores):
    """Análise de rede comum aos dois modos.

    notas: {nó: nota local}, só para nós cuja dona participa da análise.
    dono: {nó: instituição}, quando conhecida (externas aparecem pela instituição do Pix).
    arestas: lista de (origem, destino, tipo, valor).
    relatores: {nó: conjunto de instituições que relataram Pix tocando o nó}.
    """
    g = nx.Graph()
    for o, d, tipo, valor in arestas:
        g.add_edge(o, d)
    for n in notas:
        g.add_node(n)

    final, porque = {}, {}
    for n in g.nodes:
        base = notas.get(n, 0)
        viz = [v for v in g.neighbors(n) if notas.get(v, 0) >= FRACA]
        bonus = 15 * min(3, len(viz))
        outras = relatores.get(n, set()) - {dono.get(n)}
        extra = 10 if len(outras) >= 2 else 0
        final[n] = base + bonus + extra
        m = list(motivos.get(n, []))
        if viz:
            m.append(f"trocou repasses rápidos ou Pix de teste com {len(viz)} conta(s) suspeita(s)")
        if extra:
            m.append(f"{len(outras)} outras instituições relataram Pix suspeitos com esta conta")
        porque[n] = m

    # Anéis: só entre contas com evidência própria (alguma instituição já deu nota fraca ou forte).
    # Conta sem evidência própria, como loja ou corretora que recebe de vários laranjas, não liga anéis:
    # antes ela colava redes diferentes num "anel" de centenas de contas.
    sub = g.subgraph([n for n, v in final.items() if v >= FRACA and notas.get(n, 0) >= FRACA])
    aneis = [sorted(c) for c in nx.connected_components(sub) if len(c) >= 3]
    anel_de = {}
    for i, c in enumerate(aneis):
        for n in c:
            anel_de[n] = i
            if len(c) >= 4:
                final[n] += 10
                porque[n].append(f"faz parte de um anel com {len(c)} contas")
    # A rede reforça, não acusa sozinha: sem evidência própria a conta para em suspeita, nunca marcada.
    for n in final:
        if notas.get(n, 0) < FRACA and final[n] >= FORTE:
            final[n] = FORTE - 1
            porque[n].append("sem sinal próprio: fica como suspeita para revisão, não é marcada")
    return final, porque, aneis, anel_de


def modo_sozinha(banco, suspeitas, txs, ate):
    minhas = suspeitas[suspeitas["banco"] == banco]
    ar = arestas_suspeitas(txs, ate, set(minhas.index))
    arestas = list(zip(ar["origem"], ar["destino"], ar["repasse"].map({True: "repasse", False: "teste"}), ar["valor"]))
    dono = {**dict(zip(ar["origem"], ar["banco_origem"])), **dict(zip(ar["destino"], ar["banco_destino"]))}
    # As contas suspeitas são da própria instituição mesmo quando não têm nenhum repasse rápido
    # (por exemplo: só contestação MED). Sem isso elas nunca eram marcadas no modo sozinha.
    dono.update({i: banco for i in minhas.index})
    relatores = defaultdict(set)
    for o, d in zip(ar["origem"], ar["destino"]):
        relatores[o].add(banco)
        relatores[d].add(banco)
    final, porque, aneis, anel_de = analisar(minhas["nota"].to_dict(), minhas["motivos"].to_dict(), dono, arestas, relatores)
    marcadas = {n for n, v in final.items() if v >= FORTE and dono.get(n) == banco}
    return {"final": final, "porque": porque, "aneis": aneis, "marcadas": marcadas, "arestas": arestas, "dono": dono}


def modo_consorcio(membros, suspeitas, txs, ate):
    """Simula o protocolo: cada membro tokeniza o que manda; o hub só vê tokens."""
    pacotes = []
    for banco in membros:
        minhas = suspeitas[suspeitas["banco"] == banco]
        ar = arestas_suspeitas(txs, ate, set(minhas.index))
        tok = dict(zip(*(lambda ids: (ids, tokens_contas(ids, banco)))(list(minhas.index) + list(ar["origem"]) + list(ar["destino"]))))
        pacotes.append({
            "instituicao": banco,
            "contas": [{"t": tok[i], "nota": int(r.nota), "motivos": r.motivos} for i, r in minhas.iterrows()],
            "pix": [{"e2e": token(r.id), "o": tok[r.origem], "d": tok[r.destino],
                     "inst_o": r.banco_origem, "inst_d": r.banco_destino,
                     "tipo": "repasse" if r.repasse else "teste", "valor": round(r.valor, -1)}
                    for r in ar.itertuples()],
        })

    # --- Hub: daqui para baixo só existem tokens --------------------------------------
    notas, motivos, dono, relatores, vistos, arestas = {}, {}, {}, defaultdict(set), set(), []
    for p in pacotes:
        for c in p["contas"]:
            notas[c["t"]], motivos[c["t"]], dono[c["t"]] = c["nota"], c["motivos"], p["instituicao"]
        for x in p["pix"]:
            dono.setdefault(x["o"], x["inst_o"])
            dono.setdefault(x["d"], x["inst_d"])
            relatores[x["o"]].add(p["instituicao"])
            relatores[x["d"]].add(p["instituicao"])
            if x["e2e"] not in vistos:  # o mesmo Pix pode ser relatado pelas duas pontas
                vistos.add(x["e2e"])
                arestas.append((x["o"], x["d"], x["tipo"], x["valor"]))
    final, porque, aneis, anel_de = analisar(notas, motivos, dono, arestas, relatores)
    marcadas_tok = {n for n, v in final.items() if v >= FORTE}
    return {"final": final, "porque": porque, "aneis": aneis, "marcadas_tok": marcadas_tok,
            "arestas": arestas, "dono": dono, "pacotes": pacotes}


def destokenizar(ids):
    """Cada instituição só consegue reverter tokens das próprias contas (ou contrapartes que já conhece)."""
    return {token_direto(i, SEGREDO, _HUB._k): i for i in ids}
