"use client";

import { useEffect, useMemo, useRef } from "react";
import gsap from "gsap";
import { Demo, Foto, Modo, No, corBanco, estado, layout, letraBanco, ms, LARANJA } from "@/lib/dados";


type Props = {
  demo: Demo; modo: Modo; foto: Foto; t: number; banco: string;
  sel: string | null; onSel: (id: string) => void; gabarito: boolean; reduzir: boolean;
};

export default function Grafo({ demo, modo, foto, t, banco, sel, onSel, gabarito, reduzir }: Props) {
  const { pos, W, H, topo } = useMemo(() => layout(demo), [demo]);
  const porId = useMemo(() => Object.fromEntries(demo.nos.map(n => [n.id, n])), [demo]);

  // Sozinha: cada instituição só liga contas que são dela. As ligações entre instituições só existem no consórcio.
  const arestas = useMemo(() => demo.arestas.filter(a => {
    if (ms(a.desde) > t || !pos[a.o] || !pos[a.d]) return false;
    if (modo === "c") return true;
    const o = porId[a.o], d = porId[a.d];
    return o.banco === d.banco && o.membro;
  }), [demo, t, modo, pos, porId]);

  const svg = useRef<SVGSVGElement>(null);
  const vistas = useRef(new Set<string>());
  const marcadas = useRef(new Set<string>());

  // Movimento: ligação nova se desenha; conta que passa a marcada pulsa uma vez. Sem blur.
  useEffect(() => {
    const raiz = svg.current;
    if (!raiz) return;
    const novas: Element[] = [];
    for (const a of arestas) {
      const k = `${a.o}-${a.d}`;
      if (!vistas.current.has(k)) {
        vistas.current.add(k);
        const el = raiz.querySelector(`[data-a="${k}"]`);
        if (el) novas.push(el);
      }
    }
    const pulsos: Element[] = [];
    for (const n of demo.nos) {
      if (estado(n, modo, foto, t) === "marcada" && !marcadas.current.has(n.id)) {
        marcadas.current.add(n.id);
        const el = raiz.querySelector(`[data-n="${n.id}"] .anel-marcada`);
        if (el) pulsos.push(el);
      }
    }
    if (reduzir) return;
    if (novas.length) gsap.fromTo(novas, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.7, ease: "power2.out", stagger: 0.02 });
    for (const el of pulsos) {
      // Anima o raio, não a escala: em SVG a escala desloca o círculo para fora do nó
      const r = Number(el.getAttribute("r"));
      gsap.fromTo(el, { attr: { r: r + 16 }, opacity: 0 }, { attr: { r }, opacity: 1, duration: 0.55, ease: "power3.out" });
    }
  }, [arestas, demo, foto, t, modo, reduzir]);

  // Voltar no tempo: esquece o que ainda não aconteceu para poder animar de novo.
  useEffect(() => {
    for (const k of [...vistas.current]) if (!arestas.some(a => `${a.o}-${a.d}` === k)) vistas.current.delete(k);
    for (const id of [...marcadas.current]) if (estado(porId[id], modo, foto, t) !== "marcada") marcadas.current.delete(id);
  }, [arestas, porId, modo, foto, t]);

  const rotulo = (n: No) => {
    const e = estado(n, modo, foto, t);
    const nota = foto[modo][n.id];
    return `${n.id}, ${n.banco}${n.membro ? "" : " (fora do consórcio)"}, ${e === "neutra" ? "sem suspeita" : e === "fraca" ? `suspeita fraca, ${nota} pontos` : `marcada${nota ? `, ${nota} pontos` : ""}`}`;
  };

  return (
    <svg ref={svg} viewBox={`0 0 ${W} ${H}`} className="grafo" role="group" aria-label={modo === "s" ? "Grafo de cada instituição sozinha" : "Grafo do consórcio"}>
      <defs>
        <pattern id={`p-${modo}`} width="40" height="40" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="1" fill="var(--grid)" />
        </pattern>
      </defs>
      <rect width={W} height={H} fill={`url(#p-${modo})`} />
      <line x1={30} x2={W - 30} y1={topo - 8} y2={topo - 8} className="divisa" />
      <text x={30} y={topo + 12} className="rotulo-soltas">contas sem ligação</text>
      <g>
        {arestas.map(a => {
          const o = pos[a.o], d = pos[a.d];
          const marc = estado(porId[a.o], modo, foto, t) === "marcada" && estado(porId[a.d], modo, foto, t) === "marcada";
          const entre = porId[a.o].banco !== porId[a.d].banco;
          return (
            <line key={`${a.o}-${a.d}`} data-a={`${a.o}-${a.d}`} x1={o.x} y1={o.y} x2={d.x} y2={d.y} pathLength={1}
              strokeDasharray={a.tipo === "teste" ? "0.02 0.02" : "1"}
              className={`aresta ${marc ? "aresta-marcada" : ""} ${entre ? "aresta-entre" : ""}`} />
          );
        })}
      </g>
      <g>
        {demo.nos.map(n => {
          const p = pos[n.id];
          const e = estado(n, modo, foto, t);
          const apagada = banco !== "todas" && n.banco !== banco;
          const r = e === "neutra" ? 8 : 16;
          return (
            <g key={n.id} data-n={n.id} transform={`translate(${p.x},${p.y})`}
              className={`no no-${e} ${apagada ? "no-apagada" : ""} ${sel === n.id ? "no-sel" : ""}`}
              tabIndex={e === "neutra" && !gabarito ? -1 : 0} role="button" aria-label={rotulo(n)} aria-pressed={sel === n.id}
              onClick={() => onSel(n.id)}
              onKeyDown={ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); onSel(n.id); } }}>
              <title>{rotulo(n)}</title>
              {gabarito && LARANJA.has(n.papel) && <circle r={r + 9} className="gabarito" />}
              {sel === n.id && <circle r={r + 6} className="sel-halo" />}
              <circle r={r} className="corpo" style={{ stroke: corBanco(n.banco) }} />
              {e === "marcada" && <circle r={r + 5} className="anel-marcada" />}
              {e !== "neutra" && <text className="letra" dy="0.35em">{letraBanco(n.banco)}</text>}
            </g>
          );
        })}
      </g>
    </svg>
  );
}
