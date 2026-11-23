"""Converte um mundo do PixSim (Zeimarani et al., 2026, Apache-2.0) para o formato que o motor do Hórus lê.

O PixSim é um simulador independente, calibrado com dados do BCB, feito por outro grupo. Ele simula
uma instituição só; a divisão das contas entre 6 instituições é hipótese nossa, com os mesmos pesos
do gerador do Hórus, mas SEM o viés do gerador (lá os laranjas caem mais nas instituições pequenas;
aqui a instituição é sorteada sem olhar se a conta é laranja).

Roda no ambiente do PixSim, que é dependência externa e não fica neste repositório:
  <pixsim>/.venv/bin/python -I validacao/pixsim_adaptar.py --pixsim <pasta do pixsim_public> --semente 1
Depois, no ambiente do Hórus:
  .venv/bin/python -m motor.avaliar --pasta data/externo/pixsim_s1 --passo 6
"""

import argparse
import datetime as dt
import json
import pathlib
import sys

import numpy as np
import pandas as pd

INSTITUICOES = {"Banco Açaí": (0.26, False), "Banco Pirarucu": (0.24, False), "Coop Cupuaçu": (0.12, True),
                "Coop Guaraná": (0.12, True), "Fintech Jaraqui": (0.13, True), "Fintech Tambaqui": (0.13, True)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pixsim", required=True, type=pathlib.Path)
    ap.add_argument("--semente", type=int, default=1)
    ap.add_argument("--contas", type=int, default=20000)
    ap.add_argument("--golpes_mes", type=int, default=400, help="eventos de golpe aceitos por mês (o PixSim usa 2000 para 100 mil contas)")
    ap.add_argument("--saida", type=pathlib.Path, default=None)
    a = ap.parse_args()
    saida = a.saida or pathlib.Path(f"data/externo/pixsim_s{a.semente}")
    saida.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(a.pixsim))
    from pixsim import load_config
    from pixsim.fraud import inject_fraud
    from pixsim.population import build_population
    from pixsim.traffic import generate_legit_traffic

    cfg = load_config(a.pixsim / "configs" / "baseline.yaml", overrides={
        "seed": a.semente, "population": {"n_accounts": a.contas}, "fraud": {"target_accepted_per_month": a.golpes_mes}})
    rng = np.random.default_rng(a.semente)
    pop = build_population(cfg, rng)
    legit = generate_legit_traffic(pop, cfg, rng)
    tx, eventos, _ = inject_fraud(pop, cfg, rng, legit)
    inicio = pd.Timestamp(pop.start_date)

    acc = pop.accounts
    nomes = list(INSTITUICOES)
    pesos = np.array([v[0] for v in INSTITUICOES.values()])
    banco = np.random.default_rng(a.semente + 1000).choice(nomes, size=len(acc), p=pesos / pesos.sum())
    ids = "P" + acc["account_id"].astype(str).str.zfill(6)
    contas = pd.DataFrame({"id": ids, "nome": "Conta " + ids, "cpf": "",
                           "banco": banco, "criada_em": pd.to_datetime(acc["opening_date"]).dt.date.astype(str)})
    contas.to_csv(saida / "contas.csv", index=False)
    mapa = dict(zip(acc["account_id"], ids))

    tx = tx.sort_values("t")
    trans = pd.DataFrame({"id": "X" + tx["tx_id"].astype(str).str.zfill(8),
                          "ts": (inicio + pd.to_timedelta(tx["t"], unit="s")).dt.strftime("%Y-%m-%dT%H:%M:%S"),
                          "origem": tx["sender"].map(mapa), "destino": tx["receiver"].map(mapa),
                          "valor": tx["amount"].round(2)})
    trans.to_csv(saida / "transacoes.csv", index=False)

    # Contestação MED: golpes que a vítima relatou, abertos depois do atraso de relato e de abertura do PixSim
    ev = eventos[eventos["reported"]].copy()
    ev["aberta"] = inicio + pd.to_timedelta(ev["t0"] + ev["report_delay_s"] + ev["open_delay_s"], unit="s")
    v2m = tx[tx["role"] == "victim_to_mule"]
    contest = []
    fim = inicio + pd.Timedelta(days=int(cfg.simulation.days))
    for r in ev.itertuples():
        if r.aberta > fim:
            continue
        for x in v2m[v2m["scenario_id"] == r.scenario_id].itertuples():
            contest.append({"vitima": mapa[x.sender], "valor": round(float(x.amount), 2),
                            "aberta_em": r.aberta.strftime("%Y-%m-%dT%H:%M:%S"), "tx_id": "X" + str(x.tx_id).zfill(8)})
    json.dump(contest, open(saida / "contestacoes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # Gabarito: laranja = conta laranja do PixSim que recebeu dinheiro de golpe no mês
    golpe = tx[tx["role"].isin(["victim_to_mule", "mule_forward"])]
    recebeu = set(golpe["receiver"])
    papel = {}
    for aid, mula, saida_ in zip(acc["account_id"], acc["is_mule"], acc["is_exit"]):
        papel[mapa[aid]] = ("laranja" if aid in recebeu else "laranja_inativa") if mula else ("saida" if saida_ else "licita")
    redes = [{"rede": f"R{int(rid)}", "membros": sorted({mapa[c] for c in g["receiver"] if acc.at[c, "is_mule"]})}
             for rid, g in golpe.groupby("ring_id")]
    redes = [r for r in redes if r["membros"]]
    tipo_tx = {"X" + str(i).zfill(8): "golpe" for i in tx.loc[tx["role"] == "victim_to_mule", "tx_id"]}
    json.dump({"redes": redes, "papeis": papel, "tipo_tx": tipo_tx}, open(saida / "gabarito.json", "w", encoding="utf-8"))
    json.dump({k: {"consorcio": v[1]} for k, v in INSTITUICOES.items()},
              open(saida / "instituicoes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    n_lar = sum(p == "laranja" for p in papel.values())
    print(f"PixSim semente {a.semente}: {len(contas)} contas, {len(trans)} transações, {len(contest)} contestações, "
          f"{n_lar} laranjas ativos em {len(redes)} anéis -> {saida}  ({dt.datetime.now():%H:%M})")


if __name__ == "__main__":
    main()
