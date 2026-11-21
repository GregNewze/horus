"""Gerador de transações Pix sintéticas com redes de contas laranja embutidas.

Tudo aqui é fictício: nomes, CPFs (sempre começam com 999), chaves e bancos.
Uso: python3 gerador/gerar.py --contas 3000 --redes 6 --dias 30 --semente 42 --saida data/out
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
BANCOS = ["Banco Açaí", "Banco Tucumã", "Coop Cupuaçu", "Fintech Jaraqui", "Banco Pirarucu", "Coop Guaraná"]

INICIO = datetime(2026, 10, 1)


def cpf_ficticio(rng):
    return f"999.{rng.randint(0, 999):03d}.{rng.randint(0, 999):03d}-{rng.randint(0, 99):02d}"


def nova_conta(rng, idx, papel, criada_em):
    return {
        "id": f"C{idx:05d}",
        "nome": f"{rng.choice(NOMES)} {rng.choice(SOBRENOMES)}",
        "cpf": cpf_ficticio(rng),
        "banco": rng.choice(BANCOS),
        "criada_em": criada_em.date().isoformat(),
        "papel": papel,  # rótulo verdadeiro; o detector NÃO pode ler este campo
    }


def gerar(n_contas, n_redes, dias, semente):
    rng = random.Random(semente)
    fim = INICIO + timedelta(days=dias)
    contas, txs, redes, contestacoes = [], [], [], []

    def add_tx(origem, destino, valor, ts, tipo):
        txs.append({"id": f"T{len(txs):07d}", "ts": ts.isoformat(timespec="seconds"),
                    "origem": origem, "destino": destino, "valor": round(valor, 2), "tipo_real": tipo})

    def ts_aleatorio():
        return INICIO + timedelta(seconds=rng.randint(0, dias * 86400 - 1))

    # Contas comuns: pessoas e comércios, abertas há anos
    n_comercios = max(20, n_contas // 15)
    for i in range(n_contas):
        papel = "comercio" if i < n_comercios else "pessoa"
        criada = INICIO - timedelta(days=rng.randint(200, 3000))
        contas.append(nova_conta(rng, i, papel, criada))
    comercios = [c["id"] for c in contas if c["papel"] == "comercio"]
    pessoas = [c["id"] for c in contas if c["papel"] == "pessoa"]
    empregadores = comercios[:max(5, len(comercios) // 4)]

    # Círculo social de cada pessoa (rede de mundo pequeno)
    amigos = {p: rng.sample(pessoas, 8) for p in pessoas}

    # Tráfego normal
    for p in pessoas:
        for mes in range((dias + 29) // 30):  # salário
            dia = INICIO + timedelta(days=30 * mes + 4, hours=rng.randint(8, 12))
            if dia < fim:
                add_tx(rng.choice(empregadores), p, rng.uniform(1500, 6000), dia, "salario")
        for _ in range(rng.randint(dias // 2, dias * 2)):  # compras
            add_tx(p, rng.choice(comercios), rng.lognormvariate(3.5, 0.9), ts_aleatorio(), "compra")
        for _ in range(rng.randint(1, dias // 3 + 1)):  # Pix entre amigos
            add_tx(p, rng.choice(amigos[p]), rng.lognormvariate(4, 1), ts_aleatorio(), "p2p")

    # Redes de laranjas
    idx = len(contas)
    vitimas_livres = rng.sample(pessoas, min(len(pessoas), n_redes * 25))
    for r in range(n_redes):
        def nova(papel, dias_atras):
            nonlocal idx
            c = nova_conta(rng, idx, papel, INICIO + timedelta(days=rng.randint(0, dias - 1)) - timedelta(days=dias_atras))
            idx += 1
            contas.append(c)
            return c["id"]

        camada1 = [nova("laranja", rng.randint(0, 40)) for _ in range(rng.randint(4, 8))]
        camada2 = [nova("laranja", rng.randint(0, 60)) for _ in range(rng.randint(2, 4))]
        coletora = nova("coletora", rng.randint(30, 120))
        membros = camada1 + camada2 + [coletora]
        redes.append({"rede": f"R{r + 1}", "membros": membros, "camada1": camada1,
                      "camada2": camada2, "coletora": coletora})

        # Laranjas fazem um pouco de movimento comum para disfarçar
        for m in camada1 + camada2:
            for _ in range(rng.randint(1, 4)):
                add_tx(m, rng.choice(comercios), rng.lognormvariate(3, 0.7), ts_aleatorio(), "compra")

        n_vitimas = rng.randint(10, 25)
        for _ in range(n_vitimas):
            if not vitimas_livres:
                break
            vitima = vitimas_livres.pop()
            t0 = ts_aleatorio()
            valor = rng.choice([rng.uniform(300, 2000), rng.uniform(2000, 9000)])
            l1 = rng.choice(camada1)
            add_tx(vitima, l1, valor, t0, "golpe")
            contestacoes.append({"tx_id": txs[-1]["id"], "vitima": vitima, "valor": round(valor, 2),
                                 "aberta_em": (t0 + timedelta(hours=rng.randint(2, 48))).isoformat(timespec="seconds")})

            # Espalha em minutos para a camada 2, que junta na coletora
            restante = valor * rng.uniform(0.92, 0.99)  # o laranja fica com uma "comissão"
            t = t0
            partes = rng.randint(2, 3)
            for _ in range(partes):
                t += timedelta(minutes=rng.randint(1, 20))
                l2 = rng.choice(camada2)
                parte = restante / partes
                add_tx(l1, l2, parte, t, "lavagem")
                t2 = t + timedelta(minutes=rng.randint(2, 40))
                add_tx(l2, coletora, parte * rng.uniform(0.95, 0.99), t2, "lavagem")

        # Ouroboros: parte do dinheiro volta para a camada 1 para parecer movimento legítimo
        for _ in range(rng.randint(2, 5)):
            t = ts_aleatorio()
            add_tx(coletora, rng.choice(camada1), rng.uniform(100, 800), t, "ciclo")

    txs.sort(key=lambda x: x["ts"])
    return contas, txs, redes, contestacoes


def salvar(saida, contas, txs, redes, contestacoes):
    saida.mkdir(parents=True, exist_ok=True)
    publico = ["id", "nome", "cpf", "banco", "criada_em"]
    with open(saida / "contas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=publico, extrasaction="ignore")
        w.writeheader()
        w.writerows(contas)
    with open(saida / "transacoes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "ts", "origem", "destino", "valor"], extrasaction="ignore")
        w.writeheader()
        w.writerows(txs)
    with open(saida / "contestacoes.json", "w", encoding="utf-8") as f:
        json.dump(contestacoes, f, ensure_ascii=False, indent=1)
    # Gabarito: só para medir o acerto do detector
    gabarito = {"redes": redes, "papeis": {c["id"]: c["papel"] for c in contas},
                "tipo_tx": {t["id"]: t["tipo_real"] for t in txs}}
    with open(saida / "gabarito.json", "w", encoding="utf-8") as f:
        json.dump(gabarito, f, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contas", type=int, default=3000)
    ap.add_argument("--redes", type=int, default=6)
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
