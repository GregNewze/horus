"use client";

import { Demo, dataHora, horas, ms } from "@/lib/dados";

// Uma linha por anel: quando o consórcio achou, quando a instituição sozinha achou e a 1ª contestação MED.
export default function Aneis({ demo, t }: { demo: Demo; t: number }) {
  const t0 = ms(demo.fotos[0].ate), t1 = ms(demo.fotos[demo.fotos.length - 1].ate);
  const x = (s: string) => `${((ms(s) - t0) / (t1 - t0)) * 100}%`;
  const dias = [1, 8, 15, 22, 29].map(d => ({ d, p: ((Date.parse(`2026-10-${String(d).padStart(2, "0")}T00:00:00`) - t0) / (t1 - t0)) * 100 }));

  return (
    <div className="aneis" role="table" aria-label="Quando cada anel foi achado">
      <div className="aneis-eixo" aria-hidden="true">
        {dias.map(d => <span key={d.d} style={{ left: `${d.p}%` }}>{String(d.d).padStart(2, "0")}/10</span>)}
        <i className="agora-linha" style={{ left: `${((t - t0) / (t1 - t0)) * 100}%` }} />
      </div>
      {demo.aneis.map(a => {
        const ganho = a.achado_c && a.achado_s ? horas(a.achado_c, a.achado_s) : null;
        const vC = a.achado_c && ms(a.achado_c) <= t, vS = a.achado_s && ms(a.achado_s) <= t;
        return (
          <div className="anel-linha" role="row" key={a.rede}>
            <span className="anel-nome" role="rowheader"><b>{a.rede}</b><span>{a.membros.length} contas</span></span>
            <div className="anel-trilho" role="cell"
              aria-label={`Consórcio achou em ${a.achado_c ? dataHora(a.achado_c) : "nunca"}; sozinha em ${a.achado_s ? dataHora(a.achado_s) : "nunca"}; primeira contestação ${a.primeira_contestacao ? dataHora(a.primeira_contestacao) : "nenhuma"}`}>
              {a.achado_c && a.achado_s && <i className={`vantagem ${vS ? "on" : ""}`} style={{ left: x(a.achado_c), width: `calc(${x(a.achado_s)} - ${x(a.achado_c)})` }} />}
              {a.primeira_contestacao && <i className="med" style={{ left: x(a.primeira_contestacao) }} title={`1ª contestação MED ${dataHora(a.primeira_contestacao)}`} />}
              {a.achado_s && <i className={`pt pt-s ${vS ? "on" : ""}`} style={{ left: x(a.achado_s) }} title={`Sozinha: ${dataHora(a.achado_s)}`} />}
              {a.achado_c && <i className={`pt pt-c ${vC ? "on" : ""}`} style={{ left: x(a.achado_c) }} title={`Consórcio: ${dataHora(a.achado_c)}`} />}
            </div>
            <span className="anel-ganho" role="cell">{ganho !== null ? `${ganho > 0 ? "+" : ""}${ganho} h` : "—"}</span>
          </div>
        );
      })}
    </div>
  );
}
