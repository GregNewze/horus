"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import Grafo from "@/components/Grafo";
import PainelConta from "@/components/PainelConta";
import LaudoMuninn from "@/components/LaudoMuninn";
import Aneis from "@/components/Aneis";
import { BANCOS, Demo, LARANJA, dataHora, horas, mediana, ms, pct } from "@/lib/dados";

type Vista = "grafo" | "laudo" | "como";

function useReduzir() {
  const [r, setR] = useState(false);
  useEffect(() => {
    const m = matchMedia("(prefers-reduced-motion: reduce)");
    setR(m.matches);
    const f = () => setR(m.matches);
    m.addEventListener("change", f);
    return () => m.removeEventListener("change", f);
  }, []);
  return r;
}

function Logo() {
  return (
    <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
      <path d="M3 16c4-6 8.5-9 13-9s9 3 13 9c-4 6-8.5 9-13 9S7 22 3 16z" fill="none" stroke="var(--accent)" strokeWidth="2" />
      <circle cx="16" cy="16" r="4.5" fill="var(--accent)" />
      <path d="M12 25l-2 5M20 25l3 4" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export default function Home() {
  const [demo, setDemo] = useState<Demo | null>(null);
  const [erro, setErro] = useState("");
  const [vista, setVista] = useState<Vista>("grafo");
  const [quadro, setQuadro] = useState(0);
  const [tocando, setTocando] = useState(false);
  const [vel, setVel] = useState(1);
  const [banco, setBanco] = useState("todas");
  const [sel, setSel] = useState<string | null>(null);
  const [gabarito, setGabarito] = useState(false);
  const [laudoI, setLaudoI] = useState(0);
  const reduzir = useReduzir();
  const tween = useRef<gsap.core.Tween | null>(null);

  useEffect(() => {
    fetch("demo.json").then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
      .then((d: Demo) => {
        setDemo(d);
        // Abre no momento em que juntas e sozinha mais se distanciam
        const dif = (f: Demo["fotos"][number]) => f.recall_c - f.recall_s + f.protegido_c - f.protegido_s;
        setQuadro(d.fotos.reduce((m, f, i) => dif(f) > dif(d.fotos[m]) ? i : m, 0));
      })
      .catch(() => setErro("Não consegui carregar demo.json. Rode `python -m motor.exportar --saida web/public/demo.json` e recarregue."));
  }, []);

  // Navegação pelo hash, para o vídeo e os links caírem direto numa tela
  useEffect(() => {
    const ler = () => { const h = location.hash.slice(1); setVista(h === "laudo" || h === "como" ? h : "grafo"); };
    ler();
    addEventListener("hashchange", ler);
    return () => removeEventListener("hashchange", ler);
  }, []);
  const ir = (v: Vista) => { location.hash = v === "grafo" ? "" : v; setVista(v); };

  const total = demo ? demo.fotos.length : 1;
  const parar = useCallback(() => { tween.current?.kill(); tween.current = null; setTocando(false); }, []);

  const tocar = useCallback(() => {
    if (!demo) return;
    const inicio = quadro >= total - 1 ? 0 : quadro;
    const restante = total - 1 - inicio;
    const dur = (restante / 8) / vel; // 8 fotos de 6 h por segundo em 1x: o mês inteiro em ~15 s
    setTocando(true);
    if (reduzir) {
      // Sem animação: avança foto a foto, sem interpolação
      let i = inicio;
      const id = setInterval(() => { i += 1; setQuadro(i); if (i >= total - 1) { clearInterval(id); setTocando(false); } }, 125 / vel);
      tween.current = { kill: () => clearInterval(id) } as unknown as gsap.core.Tween;
      return;
    }
    const o = { f: inicio };
    tween.current = gsap.to(o, { f: total - 1, duration: dur, ease: "none",
      onUpdate: () => setQuadro(Math.round(o.f)), onComplete: () => setTocando(false) });
  }, [demo, quadro, total, vel, reduzir]);

  useEffect(() => {
    const f = (e: KeyboardEvent) => {
      if (vista !== "grafo" || e.code !== "Space") return;
      const alvo = e.target as HTMLElement;
      if (["INPUT", "SELECT", "BUTTON", "TEXTAREA"].includes(alvo.tagName) || alvo.getAttribute("role") === "button") return;
      e.preventDefault();
      if (tocando) parar(); else tocar();
    };
    addEventListener("keydown", f);
    return () => removeEventListener("keydown", f);
  }, [vista, tocando, tocar, parar]);

  const foto = demo?.fotos[quadro];
  const t = foto ? ms(foto.ate) : 0;

  // Conta em destaque: a de maior nota no consórcio, dentro da instituição escolhida
  const destaque = useMemo(() => {
    if (!demo) return null;
    const ultima = demo.fotos[demo.fotos.length - 1];
    const cand = demo.nos.filter(n => n.membro && n.marcada_c && !n.marcada_s && (banco === "todas" || n.banco === banco));
    cand.sort((a, b) => ((ultima.c[b.id] ?? 0) - (ultima.s[b.id] ?? 0)) - ((ultima.c[a.id] ?? 0) - (ultima.s[a.id] ?? 0)));
    return cand[0]?.id ?? null;
  }, [demo, banco]);
  const contaId = sel ?? destaque;
  const no = demo?.nos.find(n => n.id === contaId);

  const numeros = useMemo(() => {
    if (!demo || !foto) return null;
    const falsos = (m: "s" | "c") => demo.nos.filter(n => {
      const q = m === "s" ? n.marcada_s : n.marcada_c;
      return n.membro && q && ms(q) <= t && !LARANJA.has(n.papel);
    }).length;
    const ganhos = demo.aneis.filter(a => a.achado_c && a.achado_s).map(a => horas(a.achado_c!, a.achado_s!));
    const antesMed = demo.aneis.filter(a => a.achado_c && a.primeira_contestacao && ms(a.achado_c) < ms(a.primeira_contestacao)).length;
    const sem = demo.meta.sementes;
    const faixa = (k: "recall_sozinha" | "recall_consorcio") => sem ? `${pct(Math.min(...sem.map(s => s[k])))} a ${pct(Math.max(...sem.map(s => s[k])))}` : null;
    return { falsosS: falsos("s"), falsosC: falsos("c"), med: mediana(ganhos), nAneis: demo.aneis.length,
      antes: ganhos.filter(g => g > 0).length, antesMed, faixaS: faixa("recall_sozinha"), faixaC: faixa("recall_consorcio"), nSem: sem?.length ?? 0 };
  }, [demo, foto, t]);

  const laudoDaConta = demo && contaId ? demo.laudos.findIndex(l => l.conta === contaId || l.saltos.some(s => s.destino === contaId)) : -1;

  if (erro) return <main className="erro"><p>{erro}</p></main>;
  if (!demo || !foto || !numeros) return <main className="carregando"><p>Carregando a simulação…</p></main>;

  const marcadasAgora = demo.nos.filter(n => n.marcada_c && ms(n.marcada_c) <= t)
    .sort((a, b) => (foto.c[b.id] ?? 0) - (foto.c[a.id] ?? 0));



  return (
    <div className="app">
      <header className="barra-topo">
        <div className="barra-dentro">
          <a className="marca" href="#" onClick={e => { e.preventDefault(); ir("grafo"); }}><Logo /><b>Hórus</b></a>
          <nav className="segmentos" aria-label="Seções">
            {([["grafo", "Sozinha × Juntas"], ["laudo", "Laudos"], ["como", "Como funciona"]] as [Vista, string][]).map(([v, r]) =>
              <button key={v} type="button" aria-current={vista === v ? "page" : undefined} onClick={() => ir(v)}>{r}</button>)}
          </nav>
          <span className="pilula">Dados sintéticos</span>
        </div>
      </header>

      <main className="conteudo">
        {vista === "grafo" && <>
          <section className="abertura">
            <span className="eyebrow">Consórcio antifraude para cooperativas e fintechs</span>
            <h1>Sozinhas, elas veem pontos soltos.<br /><span className="destaque-h">Juntas, veem o anel.</span></h1>
            <p className="lead">Quatro instituições pequenas juntam as suspeitas fracas que cada uma tem, pseudonimizadas, e encontram redes de contas laranja no Pix que nenhuma acharia sozinha.</p>
          </section>

          <section className="numeros" aria-label="Resultado no momento escolhido">
            <div><b>{pct(foto.recall_c)}</b><span>dos laranjas encontrados</span><em>{pct(foto.recall_s)} sozinha</em></div>
            <div><b>{pct(foto.protegido_c)}</b><span>do dinheiro de golpe dava para segurar</span><em>{pct(foto.protegido_s)} sozinha</em></div>
            <div><b>{numeros.med !== null ? `${numeros.med} h` : "—"}</b><span>antes, na mediana, para achar cada anel</span><em>vantagem sobre a instituição sozinha</em></div>
            <div><b>{numeros.falsosC}</b><span>alarmes falsos</span><em>{numeros.falsosS} sozinha · {demo.meta.clientes_membros.toLocaleString("pt-BR")} clientes</em></div>
          </section>

          <section className="palco" aria-label="Grafos">
            <div className="palco-cab">
              <label className="seletor">
                <span className="sr">Destacar instituição</span>
                <select value={banco} onChange={e => { setBanco(e.target.value); setSel(null); }}>
                  <option value="todas">Todas as instituições</option>
                  {Object.keys(BANCOS).map(b => <option key={b}>{b}</option>)}
                </select>
              </label>
              <div className="legenda" aria-label="Legenda">
                {Object.entries(BANCOS).map(([b, v]) => <span key={b}><i className="lg-banco" style={{ borderColor: v.cor }}>{v.letra}</i>{b.replace("Fintech ", "").replace("Coop ", "")}</span>)}
                <span><i className="lg-banco" style={{ borderColor: "var(--b-fora)" }} />fora</span>
                <span className="sep" />
                <span><i className="lg-fraca" />fraca</span>
                <span><i className="lg-marcada" />marcada</span>
              </div>
            </div>
            <div className="grafos">
              <figure>
                <figcaption><h2>Sozinha</h2><span>{demo.nos.filter(n => n.marcada_s && ms(n.marcada_s) <= t).length} marcadas · cada uma só liga as próprias contas</span></figcaption>
                <Grafo demo={demo} modo="s" foto={foto} t={t} banco={banco} sel={sel} onSel={setSel} gabarito={gabarito} reduzir={reduzir} />
              </figure>
              <figure>
                <figcaption><h2>Juntas</h2><span>{marcadasAgora.length} marcadas · as ligações entre instituições aparecem</span></figcaption>
                <Grafo demo={demo} modo="c" foto={foto} t={t} banco={banco} sel={sel} onSel={setSel} gabarito={gabarito} reduzir={reduzir} />
              </figure>
            </div>

            <div className="controle">
              <button type="button" className="btn-play" onClick={() => tocando ? parar() : tocar()} aria-label={tocando ? "Pausar" : "Tocar o mês"} aria-pressed={tocando}>
                {tocando ? <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><rect x="4" y="3" width="4" height="14" rx="1" fill="currentColor" /><rect x="12" y="3" width="4" height="14" rx="1" fill="currentColor" /></svg>
                  : <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="M6 3.5l11 6.5-11 6.5z" fill="currentColor" /></svg>}
              </button>
              <div className="trilho">
                <input type="range" id="quadro" min={0} max={total - 1} value={quadro} aria-label="Momento da simulação"
                  aria-valuetext={dataHora(foto.ate)} onChange={e => { parar(); setQuadro(Number(e.target.value)); }}
                  style={{ ["--p" as string]: `${(quadro / (total - 1)) * 100}%` }} />
              </div>
              <span className="agora">{dataHora(foto.ate)}</span>
              <div className="vel" role="group" aria-label="Velocidade">
                {[1, 2].map(v => <button key={v} type="button" aria-pressed={vel === v} onClick={() => { setVel(v); if (tocando) parar(); }}>{v}×</button>)}
              </div>
            </div>
            <div className="controle-rodape">
              <label className="check"><input type="checkbox" id="gabarito" checked={gabarito} onChange={e => setGabarito(e.target.checked)} />Mostrar quem era laranja de verdade</label>
              {destaque && !sel && <button type="button" className="btn-texto" onClick={() => setSel(destaque)}>Ver uma conta que só o consórcio pegou →</button>}
              <span className="dica">Toque numa conta para ver a nota · espaço toca e pausa</span>
            </div>
          </section>

          <section className="secao">
            <div className="secao-cab">
              <h2>Cada anel, achado antes</h2>
              <p>Ponto vermelho: o consórcio achou o anel. Ponto cinza: a instituição sozinha achou. Traço preto: a primeira contestação no MED. O consórcio chega antes da instituição sozinha em {numeros.antes} de {numeros.nAneis} anéis, mas antes do MED só em {numeros.antesMed}.</p>
            </div>
            <Aneis demo={demo} t={t} />
          </section>

          <section className="secao">
            <div className="secao-cab">
              <h2>Contas marcadas agora <span className="contagem">{marcadasAgora.length}</span></h2>
            </div>
            <div className="tbl">
              <table>
                <thead><tr><th>Conta</th><th>Instituição</th><th>Nota</th><th>Sozinha</th><th>Marcada em</th></tr></thead>
                <tbody>
                  {marcadasAgora.slice(0, 10).map(n => (
                    <tr key={n.id} className={n.id === sel ? "linha-sel" : ""}>
                      <td><button type="button" className="link" onClick={() => setSel(n.id)}>{n.id}</button></td>
                      <td>{n.banco}</td>
                      <td className="num">{foto.c[n.id] ?? "—"}</td>
                      <td className="num">{n.marcada_s && ms(n.marcada_s) <= t ? "marcada" : foto.s[n.id] !== undefined ? `${foto.s[n.id]}` : "não via"}</td>
                      <td className="num">{dataHora(n.marcada_c!)}</td>
                    </tr>
                  ))}
                  {!marcadasAgora.length && <tr><td colSpan={5} className="sub">Ninguém marcado ainda. Toque o mês para ver as redes aparecerem.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>

          {numeros.faixaS && <p className="nota-rodape">Simulação com semente 42. Em {numeros.nSem} sementes, a instituição sozinha acha de {numeros.faixaS} dos laranjas e o consórcio, de {numeros.faixaC}. Dados sintéticos, gerados pelo próprio projeto; não medem o mundo real.</p>}
        </>}

        {vista === "laudo" && demo.laudos[laudoI] &&
          <LaudoMuninn demo={demo} laudo={demo.laudos[laudoI]} indice={laudoI} trocar={setLaudoI} voltar={() => ir("grafo")} />}

        {vista === "como" && <article className="como">
          <span className="eyebrow">Como funciona</span>
          <h1>Quatro passos, nenhum CPF compartilhado.</h1>
          <ol className="passos">
            <li><b>Cada instituição dá nota às próprias contas.</b><p>Repasse em menos de 1 hora, conta nova recebendo muito, Pix de teste de centavos, contestação no MED. Acima de {demo.meta.fraca} pontos a conta vira suspeita fraca; acima de {demo.meta.forte}, marcada.</p></li>
            <li><b>As suspeitas fracas vão para o hub, pseudonimizadas.</b><p>Cada conta vira um token HMAC. Vão junto a nota, os motivos e os repasses rápidos que tocam a conta. Nome, CPF e saldo ficam na instituição.</p></li>
            <li><b>O hub roda a mesma análise de rede com tudo junto.</b><p>Uma conta que troca repasses com outras suspeitas, em outras instituições, sobe de nota. Anéis partidos entre quatro instituições se fecham.</p></li>
            <li><b>Muninn segue o dinheiro de um Pix contestado.</b><p>Até 5 camadas, janela de 24 h, valor mínimo de R$ 200. O laudo sai em português, montado só com fatos calculados, e serve de registro da fundada suspeita.</p></li>
          </ol>
          <h2>O que ainda não resolvemos</h2>
          <ul className="limites">
            <li><b>Chave compartilhada.</b> Com uma chave HMAC comum, um membro poderia testar CPFs e descobrir suspeitos de outro. A correção é um OPRF, em que o hub calcula o token sem ver o CPF.</li>
            <li><b>Validação externa.</b> No PixSim, um simulador de golpe Pix independente, calibrado com dados do BCB (Zeimarani et al., 2026), o consórcio achou de 50% a 56% dos laranjas, contra 40% a 48% de cada instituição sozinha, em 3 sementes. Mas a precisão caiu para 83% a 90%: as contas de saída, como lojas e corretoras que recebem de muitos laranjas, viraram alarme falso. E o dinheiro protegido quase não mudou. Na base IBM AMLworld, que simula lavagem corporativa lenta, as regras de repasse em 1 hora não acharam nada: é outro crime.</li>
            <li><b>Precisão perfeita só no nosso gerador.</b> No nosso gerador há de 0 a 1 alarme falso por simulação; no PixSim, de 9 a 16. A próxima regra é não somar pontos de rede a contas PJ que recebem de muitos pagadores lícitos.</li>
            <li><b>Antes do MED, nem sempre.</b> O consórcio acha os anéis antes da instituição sozinha, mas antes da primeira contestação só em {numeros.antesMed} de {numeros.nAneis}.</li>
          </ul>
        </article>}
      </main>

      {vista === "grafo" && sel && no && <>
        <div className="veu" onClick={() => setSel(null)} aria-hidden="true" />
        <PainelConta demo={demo} no={no} foto={foto} t={t} temLaudo={laudoDaConta >= 0} reduzir={reduzir}
          fechar={() => setSel(null)} abrirLaudo={() => { if (laudoDaConta >= 0) { setLaudoI(laudoDaConta); setSel(null); ir("laudo"); } }} />
      </>}

      <footer className="rodape">Hórus · time Northern · Hack Brasil 2026, trilha Cibersegurança</footer>
    </div>
  );
}
