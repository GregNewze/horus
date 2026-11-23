"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import Grafo from "@/components/Grafo";
import PainelConta from "@/components/PainelConta";
import LaudoMuninn from "@/components/LaudoMuninn";
import Aneis from "@/components/Aneis";
import Apresentacao from "@/components/Apresentacao";
import { BANCOS, BaseValidacao, Demo, LARANJA, dataHora, faixaPct, horas, mediana, ms, pct } from "@/lib/dados";

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
  const [validacao, setValidacao] = useState<BaseValidacao[]>([]);
  const [apresentando, setApresentando] = useState(false);
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

  // Apresentação abre na primeira visita; depois só pelo botão no topo
  useEffect(() => {
    let visto = false;
    try { visto = localStorage.getItem("horus-apresentacao") === "1"; } catch { visto = false; }
    if (!visto) setApresentando(true);
  }, []);
  const fecharApresentacao = useCallback(() => {
    setApresentando(false);
    try { localStorage.setItem("horus-apresentacao", "1"); } catch { /* sem armazenamento: abre de novo na próxima visita */ }
  }, []);

  useEffect(() => {
    fetch("validacao.json").then(r => r.ok ? r.json() : { bases: [] }).then(d => setValidacao(d.bases ?? [])).catch(() => setValidacao([]));
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
          <button type="button" className="pilula botao" onClick={() => setApresentando(true)}>Ver apresentação</button>
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
            {[
              { v: foto.recall_c, s: foto.recall_s, rot: "dos laranjas encontrados", forte: true },
              { v: foto.protegido_c, s: foto.protegido_s, rot: "do dinheiro de golpe caiu em conta já marcada" },
            ].map(x => (
              <div key={x.rot}>
                <b className={x.forte ? "vermelho" : ""}>{pct(x.v)}</b><span>{x.rot}</span>
                <div className="duas-barras" aria-hidden="true">
                  <i className="b-c" style={{ width: pct(x.v) }} /><i className="b-s" style={{ width: pct(x.s) }} />
                </div>
                <em><i className="leg-c" />juntas {pct(x.v)} · <i className="leg-s" />sozinha {pct(x.s)}</em>
              </div>
            ))}
            <div><b>{numeros.med !== null ? `${numeros.med} h` : "—"}</b><span>de vantagem na mediana para achar um anel</span><em>{numeros.antes} de {numeros.nAneis} anéis achados antes da instituição sozinha; os outros empatam</em></div>
            <div><b>{numeros.falsosC}</b><span>alarmes falsos</span><em>{numeros.falsosS} sozinha · {demo.meta.clientes_membros.toLocaleString("pt-BR")} clientes nas 4</em></div>
          </section>

          <ol className="como-ler" aria-label="Como ler a simulação">
            <li><b>Cada bolinha é uma conta.</b> A letra e a cor da borda dizem o banco.</li>
            <li><b>Amarela tracejada:</b> suspeita fraca. <b className="vermelho">Vermelha:</b> marcada, dá para segurar o dinheiro.</li>
            <li><b>Aperte play</b> e compare: à esquerda cada banco sozinho, à direita os quatro juntos.</li>
          </ol>

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

          {validacao.length > 0 && <section className="secao">
            <div className="secao-cab">
              <h2>Validação fora do nosso gerador</h2>
              <p>O mesmo motor, sem nenhum ajuste, em bases que não fizemos. Cinza: cada instituição sozinha. Vermelho: o consórcio. Cada faixa vai do menor ao maior valor entre as sementes.</p>
            </div>
            <div className="validacao">
              {validacao.map(b => (
                <article key={b.nome} className={b.nota ? "val-fora" : ""}>
                  <header><h3>{b.nome}</h3><span>{b.sementes} {b.sementes === 1 ? "rodada" : "sementes"}</span></header>
                  <p className="val-desc">{b.descricao}</p>
                  <div className="val-linha"><span>Laranjas encontrados</span>
                    <div className="val-barra" aria-label={`sozinha ${faixaPct(b.recall_s)}, consórcio ${faixaPct(b.recall_c)}`}>
                      <i className="faixa-s" style={{ left: pct(b.recall_s[0]), width: `calc(${pct(b.recall_s[1])} - ${pct(b.recall_s[0])} + 4px)` }} />
                      <i className="faixa-c" style={{ left: pct(b.recall_c[0]), width: `calc(${pct(b.recall_c[1])} - ${pct(b.recall_c[0])} + 4px)` }} />
                    </div>
                    <b>{faixaPct(b.recall_s)} → {faixaPct(b.recall_c)}</b></div>
                  <div className="val-linha"><span>Precisão do consórcio</span><div /><b>{faixaPct(b.prec_c)}</b></div>
                  <div className="val-linha"><span>Dinheiro em conta já marcada</span><div /><b>{b.din_s ? `${faixaPct(b.din_s)} → ${faixaPct(b.din_c)}` : "—"}</b></div>
                  {b.nota && <p className="val-nota">{b.nota}</p>}
                </article>
              ))}
            </div>
            <p className="nota-rodape">Em nenhuma base um laranja foi marcado antes do primeiro golpe que recebeu. O dinheiro que dá para segurar vem dos golpes seguintes na mesma conta. No PixSim, os laranjas a mais que o consórcio acha só ficam evidentes depois de usados, por isso o dinheiro não sobe.</p>
          </section>}

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

          <p className="nota-rodape">Tela: semente 42 do gerador do Hórus, fotos a cada 6 h. Dados sintéticos.</p>
        </>}

        {vista === "laudo" && demo.laudos[laudoI] &&
          <LaudoMuninn demo={demo} laudo={demo.laudos[laudoI]} indice={laudoI} trocar={setLaudoI} voltar={() => ir("grafo")} />}

        {vista === "como" && <article className="como">
          <span className="eyebrow">Como funciona</span>
          <h1>Nenhuma conta sai da instituição com nome ou CPF.</h1>
          <ol className="passos">
            <li><b>Cada instituição dá nota às próprias contas.</b><p>Repassar em menos de 1 hora 60% ou mais do que recebeu (+30) ou de 30% a 60% (+15), com pelo menos R$ 1 mil recebidos; conta com menos de 90 dias que já recebeu R$ 3 mil (+15); Pix de teste de centavos (+10); dinheiro de 5 ou mais pessoas em 7 dias, repassando (+10); Pix contestado no MED (+40). A partir de {demo.meta.fraca} pontos a conta vira suspeita fraca e vai para o consórcio.</p></li>
            <li><b>A conta vira um token que nem o hub nem os outros membros conseguem reverter.</b><p>O membro cega o identificador e o hub aplica a chave dele sem ver o que está dentro (OPRF sobre Ed25519). Vão ao hub o token, a nota, os motivos e os repasses rápidos que tocam a conta.</p></li>
            <li><b>O hub roda a mesma análise de rede com tudo junto.</b><p>Cada vizinho suspeito soma 15 pontos (até 3), duas ou mais outras instituições relatando a conta somam 10, e anel de 4 ou mais contas soma 10. A partir de {demo.meta.forte} a conta é marcada, mas só se alguma instituição já tinha dado nota a ela: a rede reforça, não acusa sozinha.</p></li>
            <li><b>Muninn segue o dinheiro de um Pix contestado.</b><p>Até 5 camadas, janela de 24 h, valor mínimo de R$ 200. O laudo é montado com os fatos calculados e serve de registro da fundada suspeita (Res. BCB 501/2025).</p></li>
          </ol>

          <h2>O token, passo a passo</h2>
          <figure className="protocolo">
            <svg viewBox="0 0 760 230" role="img" aria-label="Membro cega o identificador, hub aplica a chave k, membro tira a cegueira e obtém o token">
              <rect x="10" y="40" width="210" height="150" rx="18" className="p-caixa" />
              <rect x="540" y="40" width="210" height="150" rx="18" className="p-caixa" />
              <text x="115" y="72" className="p-tit">Membro</text>
              <text x="115" y="96" className="p-txt">tem a chave m</text>
              <text x="115" y="140" className="p-mono">x = H(HMACₘ(conta))</text>
              <text x="115" y="166" className="p-mono">token = r⁻¹ · y</text>
              <text x="645" y="72" className="p-tit">Hub</text>
              <text x="645" y="96" className="p-txt">tem a chave k</text>
              <text x="645" y="150" className="p-mono">y = k · a</text>
              <line x1="230" y1="118" x2="530" y2="118" className="p-seta" markerEnd="url(#seta)" />
              <line x1="530" y1="160" x2="230" y2="160" className="p-seta" markerEnd="url(#seta)" />
              <text x="380" y="108" className="p-mono">a = r · x   (cego)</text>
              <text x="380" y="182" className="p-mono">y</text>
              <defs><marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" className="p-ponta" /></marker></defs>
            </svg>
            <figcaption>O hub não tem m, então não consegue testar contas. O membro não tem k, então não calcula token sem pedir ao hub, e cada pedido fica registrado.</figcaption>
          </figure>

          {demo.meta.pedidos_hub && <>
            <h2>Registro do hub nesta simulação</h2>
            <p className="sub">Um membro que pede muito mais tokens do que tem clientes está testando CPFs: é ataque de dicionário e aparece aqui.</p>
            <div className="tbl">
              <table>
                <thead><tr><th>Membro</th><th>Tokens pedidos</th><th>Clientes</th><th>Situação</th></tr></thead>
                <tbody>{Object.entries(demo.meta.pedidos_hub).map(([m, v]) => (
                  <tr key={m}><td>{m}</td><td className="num">{v.tokens}</td><td className="num">{v.clientes}</td>
                    <td>{v.tokens > 2 * v.clientes ? <span className="selo selo-marcada">acima do limite</span> : "normal"}</td></tr>
                ))}</tbody>
              </table>
            </div>
          </>}

          <h2>Limites que continuam</h2>
          <ul className="limites">
            <li><b>Laranja só é marcado depois do primeiro golpe.</b> Em nenhuma base o motor marcou uma conta antes de ela receber dinheiro de golpe. O que dá para segurar são os golpes seguintes na mesma conta.</li>
            <li><b>No PixSim, o consórcio acha mais laranjas, mas não segura mais dinheiro.</b> Os laranjas extras ficam evidentes depois de usados.</li>
            <li><b>Conta de fora do consórcio nunca é marcada.</b> Sem sinal próprio ela fica como suspeita, para o consórcio avisar a instituição dona.</li>
            <li><b>Hub e membro juntos quebram o sigilo.</b> Com m e k na mesma mão dá para testar contas. A defesa é contratual e de auditoria, não criptográfica.</li>
            <li><b>Lavagem lenta fica fora.</b> Na base IBM AMLworld, onde o dinheiro sujo leva 28 h na mediana para sair, as regras de repasse em 1 hora não marcaram nenhuma conta.</li>
          </ul>
        </article>}
      </main>

      {vista === "grafo" && sel && no && <>
        <div className="veu" onClick={() => setSel(null)} aria-hidden="true" />
        <PainelConta demo={demo} no={no} foto={foto} t={t} temLaudo={laudoDaConta >= 0} reduzir={reduzir}
          fechar={() => setSel(null)} abrirLaudo={() => { if (laudoDaConta >= 0) { setLaudoI(laudoDaConta); setSel(null); ir("laudo"); } }} />
      </>}

      {apresentando && <Apresentacao demo={demo} fechar={fecharApresentacao} reduzir={reduzir} />}

      <footer className="rodape">Hórus · time Northern · Hack Brasil 2026, trilha Cibersegurança</footer>
    </div>
  );
}
