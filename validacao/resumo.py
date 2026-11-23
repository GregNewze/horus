"""Junta os resultados das validações num JSON pequeno para a tela (web/public/validacao.json).

Lê só arquivos gerados por validacao/sementes.py, motor/avaliar.py (PixSim) e validacao/amlworld.py.
Uso: python validacao/resumo.py [--sementes data/externo/sementes_v4.json] [--pixsim_sufixo v4]
"""

import argparse
import json
from pathlib import Path


def faixa(v):
    return [round(min(v), 3), round(max(v), 3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sementes", default="data/externo/sementes_v4.json")
    ap.add_argument("--pixsim_sufixo", default="v4")
    ap.add_argument("--saida", default="web/public/validacao.json")
    a = ap.parse_args()
    bases = []

    s = json.load(open(a.sementes, encoding="utf-8"))
    bases.append({
        "nome": "Gerador do Hórus", "descricao": "Nosso gerador: 3 mil contas, 8 anéis, 30 dias", "sementes": len(s),
        "recall_s": faixa([x["recall_sozinha"] for x in s]), "recall_c": faixa([x["recall_consorcio"] for x in s]),
        "prec_c": faixa([x["precisao_consorcio"] for x in s if x["precisao_consorcio"] is not None]),
        "din_s": faixa([x["dinheiro_sozinha"] for x in s]), "din_c": faixa([x["dinheiro_consorcio"] for x in s])})

    px = [json.load(open(p, encoding="utf-8")) for p in sorted(Path("data/externo").glob(f"pixsim_s*/avaliacao_{a.pixsim_sufixo}.json"))]
    if px:
        bases.append({
            "nome": "PixSim", "descricao": "Simulador independente calibrado com dados do BCB (Zeimarani et al., 2026): 20 mil contas, 30 dias",
            "sementes": len(px),
            "recall_s": faixa([d["sozinha"]["recall"] for d in px]), "recall_c": faixa([d["consorcio"]["recall"] for d in px]),
            "prec_c": faixa([d["consorcio"]["precisao"] for d in px if d["consorcio"]["precisao"] is not None]),
            "din_s": faixa([d["dinheiro"]["sozinha_pct"] for d in px]), "din_c": faixa([d["dinheiro"]["consorcio_pct"] for d in px])})

    aml = Path("data/externo/amlworld_s1.json")
    if aml.exists():
        bases.append({"nome": "IBM AMLworld", "descricao": "Lavagem corporativa lenta: 4,5 mi de transferências; só 2,7% do dinheiro sujo sai em até 1 h",
                      "sementes": 1, "recall_s": [0, 0], "recall_c": [0, 0], "prec_c": None, "din_s": None, "din_c": None,
                      "nota": "Fora do escopo: as regras procuram repasse em minutos, típico de golpe Pix."})

    json.dump({"bases": bases}, open(a.saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(bases, ensure_ascii=False)[:600])


if __name__ == "__main__":
    main()
