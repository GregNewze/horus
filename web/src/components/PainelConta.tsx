"use client";

import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { Demo, Foto, No, corBanco, ehSinalLocal, estado } from "@/lib/dados";

type Props = {
  demo: Demo; no: No; foto: Foto; t: number; temLaudo: boolean;
  abrirLaudo: () => void; fechar: () => void; reduzir: boolean;
};

export default function PainelConta({ demo, no, foto, t, temLaudo, abrirLaudo, fechar, reduzir }: Props) {
  const [copiado, setCopiado] = useState(false);
  const ref = useRef<HTMLElement>(null);
  const forte = demo.meta.forte;
  const eS = estado(no, "s", foto, t), eC = estado(no, "c", foto, t);
  const locais = no.motivos.filter(m => ehSinalLocal(m.frase) && m.pontos > 0);
  const rede = no.motivos.filter(m => !ehSinalLocal(m.frase) && m.pontos > 0);
  const soma = (l: typeof locais) => l.reduce((a, m) => a + m.pontos, 0);
  const total = soma(locais) + soma(rede);
  const escala = Math.max(total, forte + 20);

  // A gaveta entra pela direita; com movimento reduzido, aparece direto.
  useEffect(() => {
    if (!ref.current || reduzir) return;
    gsap.fromTo(ref.current, { xPercent: 100 }, { xPercent: 0, duration: 0.45, ease: "power3.out" });
  }, [reduzir]);
  useEffect(() => { ref.current?.focus(); }, [no.id]);
  useEffect(() => {
    const f = (e: KeyboardEvent) => { if (e.key === "Escape") fechar(); };
    addEventListener("keydown", f);
    return () => removeEventListener("keydown", f);
  }, [fechar]);

  const copiar = async () => {
    try { await navigator.clipboard.writeText(no.token); setCopiado(true); setTimeout(() => setCopiado(false), 1600); }
    catch { setCopiado(false); }
  };
  const nome = (e: string) => e === "marcada" ? "Marcada" : e === "fraca" ? "Suspeita fraca" : "Sem suspeita";

  return (
    <aside ref={ref} className="gaveta" aria-label={`Conta ${no.id}`} tabIndex={-1}>
      <div className="gaveta-cab">
        <div>
          <span className="eyebrow" style={{ color: corBanco(no.banco) }}>{no.banco}{no.membro ? "" : " · fora do consórcio"}</span>
          <h2 className="conta-id">{no.id}</h2>
        </div>
        <button type="button" className="fechar" onClick={fechar} aria-label="Fechar painel da conta">×</button>
      </div>

      <div className="comparar">
        <div className={`cmp cmp-${eS}`}><span>Sozinha</span><b>{foto.s[no.id] ?? 0}</b><em>{nome(eS)}</em></div>
        <div className={`cmp cmp-${eC}`}><span>Consórcio</span><b>{foto.c[no.id] ?? 0}</b><em>{nome(eC)}</em></div>
      </div>

      <section className="g-bloco">
        <h3>Como a nota chegou a {total}</h3>
        <div className="barra" role="img" aria-label={`${soma(locais)} pontos de sinais próprios e ${soma(rede)} da análise de rede; corte em ${forte}`}>
          <span className="seg-local" style={{ width: `${(soma(locais) / escala) * 100}%` }} />
          <span className="seg-rede" style={{ width: `${(soma(rede) / escala) * 100}%` }} />
          <i className="corte" style={{ left: `${(forte / escala) * 100}%` }}><span>corte {forte}</span></i>
        </div>
        {locais.length > 0 && <>
          <h4><i className="dot dot-local" />O que a própria instituição vê<span>+{soma(locais)}</span></h4>
          <ul className="sinais">{locais.map(m => <li key={m.frase}><span>{m.frase}</span><b>+{m.pontos}</b></li>)}</ul>
        </>}
        {rede.length > 0 && <>
          <h4><i className="dot dot-rede" />O que só a rede mostra<span>+{soma(rede)}</span></h4>
          <ul className="sinais">{rede.map(m => <li key={m.frase}><span>{m.frase}</span><b>+{m.pontos}</b></li>)}</ul>
        </>}
        {!no.motivos.length && <p className="sub">Esta conta nunca passou da nota de suspeita fraca no consórcio.</p>}
      </section>

      <section className="g-bloco">
        <h3>O que o hub recebeu</h3>
        <div className="token"><code>{no.token}</code><button type="button" className="btn-texto" onClick={copiar}>{copiado ? "Copiado" : "Copiar"}</button></div>
        <p className="sub">Um token OPRF no lugar da conta, mais a nota e os motivos. Nome, CPF e saldo ficam na instituição. Pseudonimizado, não anônimo.</p>
      </section>

      <button type="button" className="btn-principal largo" onClick={abrirLaudo} disabled={!temLaudo}>
        {temLaudo ? "Abrir laudo Muninn" : "Sem laudo para esta conta"}
      </button>
    </aside>
  );
}
