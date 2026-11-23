"""Gerador de transações Pix sintéticas com redes de contas laranja embutidas.

Tudo aqui é fictício: nomes, CPFs (sempre começam com 999), chaves e instituições.

O gerador tenta ser honesto com o detector:
- parte dos laranjas usa contas antigas (conta alugada), não só contas recém-abertas;
- existem clientes legítimos que parecem laranjas: autônomos que recebem de muita gente
  e repassam ao fornecedor no mesmo dia, e jovens com conta nova;
- as redes têm formatos diferentes (2 ou 3 camadas, saída para corretora de cripto);
- nem toda vítima contesta, e a contestação chega de horas a dias depois.

Uso: python3 gerador/gerar.py --contas 3000 --redes 8 --dias 30 --semente 42 --saida data/out
"""

import argparse
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Heitor", "Iara", "João",
         "Kauã", "Larissa", "Marcos", "Natália", "Otávio", "Paula", "Rafael", "Sofia", "Tiago", "Vitória"]
SOBRENOMES = ["Amaral", "Barros", "Cardoso", "Duarte", "Esteves", "Farias", "Guedes", "Holanda",
              "Lacerda", "Meireles", "Nogueira", "Pinheiro", "Queiroz", "Rocha", "Siqueira", "Teles"]

# Instituições fictícias. As quatro pequenas formam o consórcio; os dois bancos grandes ficam de fora.
INSTITUICOES = {
    "Banco Açaí": {"peso": 0.26, "consorcio": False},
    "Banco Pirarucu": {"peso": 0.24, "consorcio": False},
    "Coop Cupuaçu": {"peso": 0.12, "consorcio": True},
    "Coop Guaraná": {"peso": 0.12, "consorcio": True},
    "Fintech Jaraqui": {"peso": 0.13, "consorcio": True},
    "Fintech Tambaqui": {"peso": 0.13, "consorcio": True},
}
# Laranjas abrem conta mais em fintech (abertura rápida pelo celular), mas não só.
PESO_LARANJA = {"Banco Açaí": 0.17, "Banco Pirarucu": 0.15, "Coop Cupuaçu": 0.12,
                "Coop Guaraná": 0.12, "Fintech Jaraqui": 0.22, "Fintech Tambaqui": 0.22}

INICIO = datetime(2026, 10, 1)


def cpf_ficticio(rng):
    return f"999.{rng.randint(0, 999):03d}.{rng.randint(0, 999):03d}-{rng.randint(0, 99):02d}"


def sortear(rng, pesos):
    return rng.choices(list(pesos), weights=list(pesos.values()))[0]


def gerar(n_contas, n_redes, dias, semente, ruido=1.0):
    """ruido multiplica os casos legítimos que parecem laranja (centavos e contestação contra inocente)."""
    rng = random.Random(semente)
    fim = INICIO + timedelta(days=dias)
    contas, txs, redes, contestacoes = [], [], [], []
    pesos_inst = {k: v["peso"] for k, v in INSTITUICOES.items()}

    def nova_conta(papel, criada_em, pesos=pesos_inst):
        c = {"id": None, "nome": f"{rng.choice(NOMES)} {rng.choice(SOBRENOMES)}", "cpf": cpf_ficticio(rng),
             "banco": sortear(rng, pesos), "criada_em": criada_em.date().isoformat(), "papel": papel}
        contas.append(c)
        return c

    LICITAS = {"salario", "compra", "p2p", "racha", "venda", "fornecedor", "centavos"}

    def add_tx(origem, destino, valor, ts, tipo):
        # Conta lícita aberta no meio do mês não movimenta antes de existir.
        if tipo in LICITAS and ts.date().isoformat() < max(origem["criada_em"], destino["criada_em"]):
            return None
        txs.append({"id": None, "ts": ts, "origem": origem, "destino": destino,
                    "valor": round(max(valor, 0.01), 2), "tipo_real": tipo})
        return txs[-1]

    def ts_aleatorio(ini=INICIO, fim_=fim):
        return ini + timedelta(seconds=rng.randint(0, int((fim_ - ini).total_seconds()) - 1))

    def antiga():
        return INICIO - timedelta(days=rng.randint(200, 3000))

    def recente(max_dias=60):
        return INICIO + timedelta(days=rng.randint(0, dias - 1)) - timedelta(days=rng.randint(0, max_dias))

    # --- Contas legítimas -------------------------------------------------------------
    n_comercios = max(20, n_contas // 15)
    n_autonomos = max(10, n_contas // 30)
    n_jovens = max(10, n_contas // 25)
    comercios = [nova_conta("comercio", antiga()) for _ in range(n_comercios)]
    corretora = nova_conta("comercio", antiga(), {"Banco Açaí": 1})  # corretora de cripto, porta de saída
    corretora["nome"] = "Corretora Cripto Boto"
    autonomos = [nova_conta("autonomo", recente(90) if rng.random() < 0.3 else antiga())
                 for _ in range(n_autonomos)]
    jovens = [nova_conta("jovem", recente(45)) for _ in range(n_jovens)]
    pessoas = [nova_conta("pessoa", antiga()) for _ in range(n_contas - n_comercios - n_autonomos - n_jovens)]
    todas_pessoas = pessoas + jovens
    empregadores = comercios[:max(5, len(comercios) // 4)]
    fornecedores = comercios[len(empregadores):]
    amigos = {id(p): rng.sample(todas_pessoas, 8) for p in todas_pessoas}

    # --- Tráfego normal ---------------------------------------------------------------
    for p in todas_pessoas:
        for mes in range((dias + 29) // 30):  # salário
            dia = INICIO + timedelta(days=30 * mes + rng.randint(3, 6), hours=rng.randint(8, 12))
            if dia < fim:
                add_tx(rng.choice(empregadores), p, rng.uniform(1500, 6000), dia, "salario")
        for _ in range(rng.randint(dias // 2, dias * 2)):  # compras
            add_tx(p, rng.choice(comercios), rng.lognormvariate(3.5, 0.9), ts_aleatorio(), "compra")
        for _ in range(rng.randint(1, dias // 3 + 1)):  # Pix entre amigos
            add_tx(p, rng.choice(amigos[id(p)]), rng.lognormvariate(4, 1), ts_aleatorio(), "p2p")
        if rng.random() < 0.15:  # racha: vários amigos pagam, a pessoa paga a conta em minutos
            t = ts_aleatorio()
            total = 0
            for a in rng.sample(amigos[id(p)], rng.randint(3, 6)):
                v = rng.uniform(40, 150)
                total += v
                add_tx(a, p, v, t + timedelta(minutes=rng.randint(0, 30)), "racha")
            add_tx(p, rng.choice(comercios), total * rng.uniform(1.0, 1.3), t + timedelta(minutes=rng.randint(35, 90)), "racha")

    # Autônomos: recebem de muitos clientes diferentes e repassam ao fornecedor no mesmo dia
    for a in autonomos:
        forn = rng.choice(fornecedores)
        for d in range(dias):
            if rng.random() < 0.6:
                dia = INICIO + timedelta(days=d, hours=rng.randint(8, 18))
                recebido = 0
                for c in rng.sample(todas_pessoas, rng.randint(2, 9)):
                    v = rng.lognormvariate(4.2, 0.6)
                    recebido += v
                    add_tx(c, a, v, dia + timedelta(minutes=rng.randint(0, 240)), "venda")
                add_tx(a, forn, recebido * rng.uniform(0.6, 0.9), dia + timedelta(minutes=rng.randint(30, 420)), "fornecedor")

    # --- Redes de laranjas --------------------------------------------------------------
    vitimas_livres = rng.sample(todas_pessoas, min(len(todas_pessoas), n_redes * 30))

    def laranja(papel):
        # ~40% das contas de laranja são antigas: conta alugada de alguém real
        criada = antiga() if rng.random() < 0.4 else recente(40)
        return nova_conta(papel, criada, PESO_LARANJA)

    for r in range(n_redes):
        tres_camadas = rng.random() < 0.6
        camada1 = [laranja("laranja") for _ in range(rng.randint(4, 8))]
        # Parte da camada 1 é PJ de fachada (65% dos golpes vão para conta de empresa, Silverguard):
        # além do golpe, tem vendas comuns de clientes e paga fornecedor, o que dilui o repasse.
        for m in camada1:
            if rng.random() < 0.3:
                forn = rng.choice(fornecedores)
                for d in range(dias):
                    if rng.random() < 0.4:
                        dia = INICIO + timedelta(days=d, hours=rng.randint(8, 18))
                        recebido = 0
                        for c in rng.sample(todas_pessoas, rng.randint(2, 6)):
                            v = rng.lognormvariate(4.2, 0.6)
                            recebido += v
                            add_tx(c, m, v, dia + timedelta(minutes=rng.randint(0, 240)), "venda")
                        add_tx(m, forn, recebido * rng.uniform(0.6, 0.9), dia + timedelta(minutes=rng.randint(30, 420)), "fornecedor")
        camada2 = [laranja("laranja") for _ in range(rng.randint(2, 4))] if tres_camadas else []
        coletora = laranja("coletora")
        membros = camada1 + camada2 + [coletora]
        redes.append({"rede": f"R{r + 1}", "membros": membros, "camada1": camada1,
                      "camada2": camada2, "coletora": coletora})

        ini = INICIO + timedelta(days=rng.randint(0, max(0, dias - 12)))
        fim_rede = min(fim, ini + timedelta(days=rng.randint(5, 12)))

        # Pix de teste: centavos para conferir se a conta recebe, pouco antes de começar
        for m in camada1 + camada2:
            for _ in range(rng.randint(1, 2) if rng.random() < 0.44 else 0):  # 44% dos laranjas (Data Rudder)
                add_tx(coletora, m, rng.choice([0.01, 0.1, 1.0, rng.uniform(0.01, 2)]),
                       ini - timedelta(hours=rng.randint(1, 48)), "teste")

        # Disfarce: algumas compras comuns
        for m in membros:
            for _ in range(rng.randint(1, 6)):
                add_tx(m, rng.choice(comercios), rng.lognormvariate(3, 0.7), ts_aleatorio(), "compra")

        for _ in range(rng.randint(10, 28)):
            if not vitimas_livres:
                break
            vitima = vitimas_livres.pop()
            t0 = ts_aleatorio(ini, fim_rede)
            valor = rng.choice([rng.uniform(300, 2000), rng.uniform(2000, 9000)])
            l1 = rng.choice(camada1)
            tx = add_tx(vitima, l1, valor, t0, "golpe")
            if rng.random() < 0.7:  # nem toda vítima contesta
                contestacoes.append({"tx": tx, "vitima": vitima, "valor": round(valor, 2),
                                     "aberta_em": t0 + timedelta(hours=rng.randint(2, 120))})

            restante = valor * rng.uniform(0.92, 0.99)  # o laranja fica com uma "comissão"
            t = t0
            partes = rng.randint(2, 3)
            paciente = rng.random() < 0.2  # alguns laranjas esperam horas para não chamar atenção
            for _ in range(partes):
                t += timedelta(minutes=rng.randint(60, 240) if paciente else rng.randint(1, 20))
                parte = restante / partes
                if tres_camadas:
                    l2 = rng.choice(camada2)
                    add_tx(l1, l2, parte, t, "lavagem")
                    add_tx(l2, coletora, parte * rng.uniform(0.95, 0.99), t + timedelta(minutes=rng.randint(2, 40)), "lavagem")
                else:
                    add_tx(l1, coletora, parte, t, "lavagem")

        # A coletora tira o dinheiro pela corretora de cripto
        for _ in range(rng.randint(3, 8)):
            add_tx(coletora, corretora, rng.uniform(2000, 15000), ts_aleatorio(ini, fim_rede + timedelta(days=1)), "saida")
        # Ouroboros: parte do dinheiro volta para a camada 1 para parecer movimento legítimo
        for _ in range(rng.randint(2, 5)):
            add_tx(coletora, rng.choice(camada1), rng.uniform(100, 800), ts_aleatorio(ini, fim_rede), "ciclo")

    # --- Ruído legítimo que o detector precisa aguentar ------------------------------------
    # 2% das contas lícitas recebem um Pix de centavos (Data Rudder: 2% das lícitas recebem teste).
    licitas = todas_pessoas + autonomos + comercios
    for c in rng.sample(licitas, min(len(licitas), max(1, int(len(licitas) * 0.02 * ruido)))):
        add_tx(rng.choice(todas_pessoas), c, rng.choice([0.01, 0.1, 1.0]), ts_aleatorio(), "centavos")
    # Contestação contra inocente: cliente que contesta uma venda de autônomo ou loja (golpe do
    # comprador, ou engano). Taxa sem fonte pública; 5% dos autônomos e 2% das lojas, uma vez cada.
    vendas = {}
    for t in txs:
        if t["tipo_real"] in ("venda", "compra"):
            vendas.setdefault(id(t["destino"]), []).append(t)
    for c in (rng.sample(autonomos, min(len(autonomos), max(1, int(len(autonomos) * 0.05 * ruido))))
              + rng.sample(comercios, min(len(comercios), max(1, int(len(comercios) * 0.02 * ruido))))):
        if vendas.get(id(c)):
            t = rng.choice(vendas[id(c)])
            contestacoes.append({"tx": t, "vitima": t["origem"], "valor": t["valor"],
                                 "aberta_em": t["ts"] + timedelta(hours=rng.randint(2, 120))})

    # IDs embaralhados: a ordem de criação não pode entregar quem é laranja
    rng.shuffle(contas)
    for i, c in enumerate(contas):
        c["id"] = f"C{i:05d}"
    txs = [t for t in txs if INICIO <= t["ts"] < fim + timedelta(days=1)]
    txs.sort(key=lambda x: x["ts"])
    for i, t in enumerate(txs):
        t["id"] = f"T{i:07d}"
        t["origem"], t["destino"] = t["origem"]["id"], t["destino"]["id"]
        t["ts"] = t["ts"].isoformat(timespec="seconds")
    for c in contestacoes:
        c["tx_id"] = c.pop("tx")["id"]
        c["vitima"] = c["vitima"]["id"]
        c["aberta_em"] = c["aberta_em"].isoformat(timespec="seconds")
    contestacoes.sort(key=lambda c: c["aberta_em"])
    for r in redes:
        r["membros"] = [m["id"] for m in r["membros"]]
        r["camada1"] = [m["id"] for m in r["camada1"]]
        r["camada2"] = [m["id"] for m in r["camada2"]]
        r["coletora"] = r["coletora"]["id"]
    return contas, txs, redes, contestacoes


def salvar(saida, contas, txs, redes, contestacoes):
    saida.mkdir(parents=True, exist_ok=True)
    with open(saida / "contas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "nome", "cpf", "banco", "criada_em"], extrasaction="ignore")
        w.writeheader()
        w.writerows(contas)
    with open(saida / "transacoes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "ts", "origem", "destino", "valor"], extrasaction="ignore")
        w.writeheader()
        w.writerows(txs)
    with open(saida / "contestacoes.json", "w", encoding="utf-8") as f:
        json.dump(contestacoes, f, ensure_ascii=False, indent=1)
    with open(saida / "instituicoes.json", "w", encoding="utf-8") as f:
        json.dump({k: {"consorcio": v["consorcio"]} for k, v in INSTITUICOES.items()}, f, ensure_ascii=False, indent=1)
    # Gabarito: só para medir o acerto do detector, que nunca lê este arquivo
    gabarito = {"redes": redes, "papeis": {c["id"]: c["papel"] for c in contas},
                "tipo_tx": {t["id"]: t["tipo_real"] for t in txs}}
    with open(saida / "gabarito.json", "w", encoding="utf-8") as f:
        json.dump(gabarito, f, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--contas", type=int, default=3000)
    ap.add_argument("--redes", type=int, default=8)
    ap.add_argument("--dias", type=int, default=30)
    ap.add_argument("--semente", type=int, default=42)
    ap.add_argument("--saida", type=Path, default=Path("data/out"))
    a = ap.parse_args()
    contas, txs, redes, contestacoes = gerar(a.contas, a.redes, a.dias, a.semente)
    salvar(a.saida, contas, txs, redes, contestacoes)
    laranjas = sum(len(r["membros"]) for r in redes)
    print(f"{len(contas)} contas ({laranjas} em {len(redes)} redes), {len(txs)} transações, "
          f"{len(contestacoes)} contestações -> {a.saida}")


if __name__ == "__main__":
    main()
