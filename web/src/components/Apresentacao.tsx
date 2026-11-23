"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import { Demo, corBanco, dataHora, ms, pct, reais } from "@/lib/dados";

type Props = { demo: Demo; fechar: () => void; reduzir: boolean };

// Exemplo 1: a trilha de um Pix contestado de verdade (laudo com mais valor).
function trilha(demo: Demo) {
  const l = demo.laudos[0];
  const banco = (id: string) => demo.nos.find(n => n.id === id)?.banco ?? "conta de fora";
  const passos = [{ id: l.conta, banco: l.banco, quando: l.recebido_em, valor: l.valor }];
  let atual = l.conta;
  for (let c = 1; c <= 5; c++) {
    const s = l.saltos.find(x => x.camada === c && x.origem === atual);
    if (!s) break;
    passos.push({ id: s.destino, banco: banco(s.destino), quando: s.quando, valor: s.valor });
    atual = s.destino;
  }
  return { laudo: l, passos };
}

// Exemplo 2: a conta que o consórcio marcou com mais antecedência que o banco dela sozinho.
function exemplo(demo: Demo) {
  const fim = ms(demo.fotos[demo.fotos.length - 1].ate) + 1;
  const vizinhosAte = (id: string, t: number) => {
    const v = new Set<string>();
    for (const a of demo.arestas) if (ms(a.desde) <= t) { if (a.o === id) v.add(a.d); if (a.d === id) v.add(a.o); }
    return [...v];
  };
  // Prefere um anel visível (4+ vizinhos, 3+ bancos) e, entre esses, a maior antecedência sobre o banco sozinho
  const cand = demo.nos.filter(n => n.membro && n.marcada_c).map(n => {
    const c = ms(n.marcada_c!), s = n.marcada_s ? ms(n.marcada_s) : fim;
    const v = vizinhosAte(n.id, c);
    const bancos = new Set([n.banco, ...v.map(id => demo.nos.find(x => x.id === id)?.banco)]);
    return { n, ganho: s - c, rico: v.length >= 4 && bancos.size >= 3 };
  }).sort((a, b) => Number(b.rico) - Number(a.rico) || b.ganho - a.ganho);
  const alvo = cand[0].n;
  const foto = demo.fotos.find(f => f.ate.replace("T", " ") >= alvo.marcada_c!) ?? demo.fotos[demo.fotos.length - 1];
  const t = ms(foto.ate);
  const viz: string[] = [];
  for (const a of demo.arestas) {
    if (ms(a.desde) > t) continue;
    const o = a.o === alvo.id ? a.d : a.d === alvo.id ? a.o : null;
    if (o && !viz.includes(o)) viz.push(o);
  }
  const vizinhos = viz.map(id => demo.nos.find(n => n.id === id)!).filter(Boolean).slice(0, 5);
  return { alvo, foto, vizinhos, horas: Math.round(cand[0].ganho / 3_600_000) };
}

const PASSOS = 6;

export default function Apresentacao({ demo, fechar, reduzir }: Props) {
  const [i, setI] = useState(0);
  const cena = useRef<HTMLDivElement>(null);
  const tr = useMemo(() => trilha(demo), [demo]);
  const ex = useMemo(() => exemplo(demo), [demo]);
  const ultima = demo.fotos[demo.fotos.length - 1];
  const bancosAnel = new Set([ex.alvo.banco, ...ex.vizinhos.map(v => v.banco)]);

  useEffect(() => {
    const f = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "Enter") setI(x => Math.min(PASSOS - 1, x + 1));
      if (e.key === "ArrowLeft") setI(x => Math.max(0, x - 1));
      if (e.key === "Escape") fechar();
    };
    addEventListener("keydown", f);
    return () => removeEventListener("keydown", f);
  }, [fechar]);

  // Cada passo entra em sequência: texto, depois a ilustração. Sem blur; com movimento reduzido, aparece pronto.
  useEffect(() => {
    if (reduzir || !cena.current) return;
    const q = gsap.utils.selector(cena.current);
    const tl = gsap.timeline();
    tl.fromTo(q(".ap-texto > *"), { y: 16, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, stagger: 0.07, ease: "power3.out" });
    tl.fromTo(q(".entra"), { y: 10, opacity: 0 }, { y: 0, opacity: 1, duration: 0.45, stagger: 0.09, ease: "power2.out" }, "-=0.25");
    tl.fromTo(q(".traco"), { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.6, stagger: 0.15, ease: "power2.inOut" }, "-=0.3");
    if (i === 0) tl.fromTo(q(".moeda"), { attr: { cx: 70 } }, { attr: { cx: 70 + (tr.passos.length + 1) * 150 }, duration: 2.6, ease: "power1.inOut", repeat: -1, repeatDelay: 0.8 }, "-=0.2");
    return () => { tl.kill(); };
  }, [i, reduzir, tr.passos.length]);

  const W = 70 + (tr.passos.length + 2) * 150 - 40;
  const local = (id: string) => ex.foto.s[id];
  const juntas = (id: string) => ex.foto.c[id];

  return (
    <div className="ap" role="dialog" aria-modal="true" aria-label="Apresentação do Hórus">
      <div className="ap-topo">
        <span className="ap-marca">Hórus</span>
        <div className="ap-pontos" aria-label={`Passo ${i + 1} de ${PASSOS}`}>
          {Array.from({ length: PASSOS }, (_, k) => <button key={k} type="button" aria-label={`Ir ao passo ${k + 1}`} aria-current={k === i} onClick={() => setI(k)} />)}
        </div>
        <button type="button" className="ap-pular" onClick={fechar}>Pular</button>
      </div>

      <div className="ap-cena" ref={cena} key={i}>
        {i === 0 && <>
          <div className="ap-texto">
            <span className="ap-num">1 · O golpe</span>
            <h2>O dinheiro do golpe passa por várias contas em minutos.</h2>
            <p>Exemplo da simulação: uma pessoa cai num golpe e faz um Pix de <b>{reais(tr.laudo.valor)}</b>. Em menos de uma hora o dinheiro já passou por {tr.passos.length} contas laranja, alugadas só para isso, até sumir.</p>
          </div>
          <div className="ap-arte" style={{ overflowX: "auto" }}>
            <svg viewBox={`0 0 ${W} 200`} className="ap-svg" role="img" aria-label="Trilha do dinheiro do golpe">
              <circle className="moeda" cx={70} cy={90} r={9} />
              <g className="entra"><circle cx={70} cy={90} r={30} className="ap-vitima" /><text x={70} y={95} className="ap-rot">Vítima</text>
                <text x={70} y={150} className="ap-sub">{dataHora(tr.laudo.recebido_em).slice(6)}</text></g>
              {tr.passos.map((p, k) => {
                const x = 70 + (k + 1) * 150;
                return (
                  <g key={p.id}>
                    <line x1={x - 120} y1={90} x2={x - 32} y2={90} className="ap-linha traco" pathLength={1} />
                    <g className="entra">
                      <circle cx={x} cy={90} r={30} className="ap-conta" />
                      <text x={x} y={95} className="ap-rot mono">{p.id}</text>
                      <text x={x} y={150} className="ap-sub">{dataHora(p.quando).slice(6)}</text>
                      <text x={x} y={172} className="ap-sub">{reais(p.valor)}</text>
                    </g>
                  </g>
                );
              })}
              <line x1={70 + tr.passos.length * 150 + 30} y1={90} x2={70 + (tr.passos.length + 1) * 150 - 32} y2={90} className="ap-linha traco" pathLength={1} />
              <g className="entra"><circle cx={70 + (tr.passos.length + 1) * 150} cy={90} r={30} className="ap-vitima" strokeDasharray="5 4" />
                <text x={70 + (tr.passos.length + 1) * 150} y={95} className="ap-rot">saque</text>
                <text x={70 + (tr.passos.length + 1) * 150} y={150} className="ap-sub">o dinheiro some</text></g>
            </svg>
          </div>
        </>}

        {i === 1 && <>
          <div className="ap-texto">
            <span className="ap-num">2 · O problema</span>
            <h2>Cada conta está num banco diferente.</h2>
            <p>Cada banco só enxerga as próprias contas. Para a Fintech Tambaqui, a conta {tr.passos[0].id} só recebeu um Pix e repassou. Isso também é o que um autônomo faz todo dia. Ninguém vê a rede inteira.</p>
          </div>
          <div className="ap-arte" style={{ overflowX: "auto" }}>
            <svg viewBox={`0 0 ${W} 200`} className="ap-svg" role="img" aria-label="As mesmas contas, cada uma num banco">
              {tr.passos.map((p, k) => {
                const x = 70 + (k + 1) * 150;
                return (
                  <g key={p.id} className="entra">
                    <rect x={x - 62} y={30} width={124} height={130} rx={18} className="ap-banco" style={{ stroke: corBanco(p.banco) }} />
                    <text x={x} y={52} className="ap-sub" style={{ fill: corBanco(p.banco), fontWeight: 600 }}>{p.banco.replace("Fintech ", "").replace("Coop ", "").replace("Banco ", "")}</text>
                    <circle cx={x} cy={98} r={28} className="ap-conta" style={{ stroke: corBanco(p.banco) }} />
                    <text x={x} y={103} className="ap-rot mono">{p.id}</text>
                    <text x={x} y={145} className="ap-sub">só vê isto</text>
                  </g>
                );
              })}
              <g className="entra"><circle cx={70} cy={98} r={28} className="ap-vitima" /><text x={70} y={103} className="ap-rot">Vítima</text></g>
            </svg>
          </div>
        </>}

        {(i === 2 || i === 3) && <>
          <div className="ap-texto">
            <span className="ap-num">{i === 2 ? "3 · Sozinho" : "4 · Juntos"}</span>
            {i === 2 ? <>
              <h2>Sozinho, o banco vê só uma suspeita fraca.</h2>
              <p>A conta <b className="mono">{ex.alvo.id}</b> ({ex.alvo.banco}) tem <b>{local(ex.alvo.id) ?? 0} pontos</b> em {dataHora(ex.foto.ate)}. Para marcar e segurar o dinheiro são precisos {demo.meta.forte}. Com o que vê sozinho, o banco não age.</p>
            </> : <>
              <h2>Juntos, os bancos veem o anel.</h2>
              <p>Cada banco manda ao consórcio só as suspeitas fracas. As ligações entre bancos aparecem, e {ex.alvo.id} passa para <b className="vermelho">{juntas(ex.alvo.id)} pontos: marcada</b>. O banco dela sozinho {ex.alvo.marcada_s ? `só chegaria lá ${ex.horas} horas depois` : "não chegaria lá no mês"}.</p>
            </>}
          </div>
          <div className="ap-arte">
            <svg viewBox="0 0 600 360" className="ap-svg ap-anel" role="img" aria-label={i === 2 ? "A conta vista pelo banco sozinho" : "A conta vista pelo consórcio"}>
              {ex.vizinhos.map((v, k) => {
                const ang = -Math.PI / 2 + (2 * Math.PI * k) / ex.vizinhos.length;
                const x = 300 + 135 * Math.cos(ang), y = 180 + 135 * Math.sin(ang);
                const visivel = i === 3 || v.banco === ex.alvo.banco;
                const nota = i === 3 ? juntas(v.id) : local(v.id);
                return (
                  <g key={v.id}>
                    {visivel && <line x1={300} y1={180} x2={x} y2={y} className={`ap-linha traco ${i === 3 ? "ap-linha-red" : ""}`} pathLength={1} />}
                    <g className="entra" opacity={visivel ? 1 : 0.18}>
                      <circle cx={x} cy={y} r={26} className={`ap-conta ${i === 3 && nota !== undefined && nota >= demo.meta.forte ? "ap-marcada" : nota !== undefined ? "ap-fraca" : ""}`} style={{ stroke: corBanco(v.banco) }} />
                      <text x={x} y={y + 4} className="ap-rot mono">{visivel ? v.id : "?"}</text>
                      <text x={x} y={y < 170 ? y - 36 : y + 44} className="ap-sub" style={{ fill: corBanco(v.banco) }}>{v.banco.replace("Fintech ", "").replace("Coop ", "").replace("Banco ", "")}</text>
                    </g>
                  </g>
                );
              })}
              <g className="entra">
                <circle cx={300} cy={180} r={44} className={`ap-conta ${i === 3 ? "ap-marcada" : "ap-fraca"}`} style={{ stroke: corBanco(ex.alvo.banco) }} />
                <text x={300} y={176} className="ap-rot mono">{ex.alvo.id}</text>
                <text x={300} y={198} className="ap-nota">{i === 3 ? juntas(ex.alvo.id) : local(ex.alvo.id) ?? 0} pts</text>
              </g>
            </svg>
            <div className="ap-medidor entra">
              <div className="ap-barra"><i style={{ width: `${Math.min(100, ((i === 3 ? juntas(ex.alvo.id) : local(ex.alvo.id) ?? 0) / 140) * 100)}%` }} className={i === 3 ? "red" : "amb"} />
                <b style={{ left: `${(demo.meta.forte / 140) * 100}%` }}>marcar: {demo.meta.forte}</b></div>
              <span>{i === 3 ? `${bancosAnel.size} bancos juntaram o que cada um via` : "o banco só vê as contas da cor dele"}</span>
            </div>
          </div>
        </>}

        {i === 4 && <>
          <div className="ap-texto">
            <span className="ap-num">5 · Sigilo</span>
            <h2>Ninguém manda nome, CPF ou saldo.</h2>
            <p>Antes de sair do banco, cada conta vira um código que ninguém consegue reverter, nem o próprio consórcio. O consórcio cruza códigos, não pessoas. Quando acha um anel, cada banco descobre só quais das suas contas estão nele.</p>
          </div>
          <div className="ap-arte ap-token">
            <div className="entra ap-cartao"><span>No banco</span><b className="mono">{ex.alvo.id}</b><em>nome, CPF, saldo, histórico</em></div>
            <svg viewBox="0 0 120 40" className="ap-seta entra" aria-hidden="true"><line x1="0" y1="20" x2="105" y2="20" className="ap-linha traco" pathLength={1} /><path d="M100 12l12 8-12 8z" className="ap-ponta" /></svg>
            <div className="entra ap-cartao escuro"><span>No consórcio</span><b className="mono">{ex.alvo.token}</b><em>nota {juntas(ex.alvo.id)} e os motivos</em></div>
          </div>
        </>}

        {i === 5 && <>
          <div className="ap-texto">
            <span className="ap-num">6 · Resultado</span>
            <h2>Em um mês de simulação, com quatro bancos pequenos:</h2>
          </div>
          <div className="ap-arte ap-resumo">
            <div className="entra"><b className="vermelho">{pct(ultima.recall_c)}</b><span>dos laranjas encontrados juntos</span><em>{pct(ultima.recall_s)} cada um sozinho</em></div>
            <div className="entra"><b>{pct(ultima.protegido_c)}</b><span>do dinheiro de golpe caiu numa conta já marcada</span><em>{pct(ultima.protegido_s)} sozinho</em></div>
            <div className="entra"><b>0</b><span>contas inocentes marcadas</span><em>em {demo.meta.clientes_membros.toLocaleString("pt-BR")} clientes</em></div>
          </div>
          <p className="ap-rodape entra">Na próxima tela você vê o mês inteiro: aperte play e veja os anéis fecharem. Toque numa conta para ver por que ela foi marcada. Os dados são sintéticos.</p>
        </>}
      </div>

      <div className="ap-nav">
        <button type="button" className="ap-voltar" onClick={() => setI(x => Math.max(0, x - 1))} disabled={i === 0}>Voltar</button>
        {i < PASSOS - 1
          ? <button type="button" className="ap-avancar" onClick={() => setI(x => x + 1)}>Continuar</button>
          : <button type="button" className="ap-avancar" onClick={fechar}>Ver a simulação</button>}
      </div>
    </div>
  );
}
