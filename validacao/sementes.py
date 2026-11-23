"""Roda gerador + avaliação em várias sementes e resume sozinha x consórcio.

Uso: .venv/bin/python -m validacao.sementes [--sementes 1 2 3 4 42] [--passo 2] [--saida data/externo/sementes.json]
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gerador"))
from gerar import gerar, salvar  # noqa: E402

from motor.avaliar import rodar  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sementes", type=int, nargs="+", default=[1, 2, 3, 4, 42])
    ap.add_argument("--passo", type=int, default=2)
    ap.add_argument("--contas", type=int, default=3000)
    ap.add_argument("--redes", type=int, default=8)
    ap.add_argument("--dias", type=int, default=30)
    ap.add_argument("--ruido", type=float, default=1.0)
    ap.add_argument("--saida", default="data/externo/sementes.json")
    a = ap.parse_args()
    linhas = []
    for s in a.sementes:
        with tempfile.TemporaryDirectory() as d:
            salvar(Path(d), *gerar(a.contas, a.redes, a.dias, s, a.ruido))
            r = rodar(d, a.passo)
        lin = {"semente": s, "ruido": a.ruido,
               "recall_sozinha": r["sozinha"]["recall"], "recall_consorcio": r["consorcio"]["recall"],
               "precisao_sozinha": r["sozinha"]["precisao"], "precisao_consorcio": r["consorcio"]["precisao"],
               "falsos_sozinha": r["sozinha"]["falsos_por_tipo"], "falsos_consorcio": r["consorcio"]["falsos_por_tipo"],
               "dinheiro_sozinha": r["dinheiro"]["sozinha_pct"], "dinheiro_consorcio": r["dinheiro"]["consorcio_pct"],
               "inocentes_compartilhados": sum(r["compartilhadas"]["inocentes_por_tipo"].values()),
               "clientes": r["compartilhadas"]["clientes_dos_membros"],
               "externos_achados": r["consorcio_externas"]["laranjas"], "externos_marcados": r["consorcio_externas"]["marcadas"]}
        linhas.append(lin)
        print(json.dumps(lin, ensure_ascii=False), flush=True)
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.saida).write_text(json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
