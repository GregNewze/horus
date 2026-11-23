"use client";

import { useState } from "react";
import { Demo, Laudo, corBanco, dataHora, horas, reais } from "@/lib/dados";

type Props = { demo: Demo; laudo: Laudo; indice: number; trocar: (i: number) => void; voltar: () => void };

export default function LaudoMuninn({ demo, laudo, indice, trocar, voltar }: Props) {
  const [copiado, setCopiado] = useState<"" | "ok" | "erro">("");
  const porId = Object.fromEntries(demo.nos.map(n => [n.id, n]));
  const bancoDe = (id: string) => porId[id]?.banco ?? "";
  const marcada = (id: string) => !!porId[id]?.marcada_c;

  // Colunas por camada: quem recebeu o dinheiro em cada uma.
  const camadas: { n: number; contas: string[] }[] = [{ n: 1, contas: [laudo.conta] }];
  for (const s of laudo.saltos) {
    const c = s.camada + 1;
    let col = camadas.find(x => x.n === c);
    if (!col) { col = { n: c, contas: [] }; camadas.push(col); }
    if (!col.contas.includes(s.destino)) col.contas.push(s.destino);
  }
  camadas.sort((a, b) => a.n - b.n);

  const paragrafos = laudo.texto;
  // A trilha já mostra cada salto; o texto na tela fica com o resumo e o porquê de cada conta
  const naTela = paragrafos.filter(p => !p.startsWith("Camada"));
  const copiar = async () => {
    const txt = [`Laudo do Pix contestado ${laudo.tx}`, ...paragrafos,
      "Regra de rastreio: até 5 camadas, janela de 24 h, valor mínimo R$ 200.",
      "O texto foi montado a partir de fatos calculados; nenhuma IA decidiu quem é suspeito."].join("\n");
    try { await navigator.clipboard.writeText(txt); setCopiado("ok"); }
    catch { setCopiado("erro"); }
    setTimeout(() => setCopiado(""), 2000);
  };

  return (
    <div className="laudo">
      <div className="laudo-cab">
        <div>
          <span className="eyebrow">Laudo Muninn · Pix {laudo.tx}</span>
          <h1>Laudo do Pix contestado</h1>
        </div>
        <label className="seletor">
          <span>Contestação</span>
          <select value={indice} onChange={e => trocar(Number(e.target.value))}>
            {demo.laudos.map((l, i) => <option key={l.tx} value={i}>{reais(l.valor)} · {l.conta}</option>)}
          </select>
        </label>
      </div>

      <div className="fatos">
        <div><span className="rotulo">Valor contestado</span><b className="grande">{reais(laudo.valor)}</b></div>
        <div><span className="rotulo">Recebido</span><b className="mono">{dataHora(laudo.recebido_em)}</b><span className="sub">conta {laudo.conta} · {laudo.banco}</span></div>
        <div><span className="rotulo">Contestação MED aberta</span><b className="mono">{dataHora(laudo.aberta_em)}</b><span className="sub">{horas(laudo.recebido_em, laudo.aberta_em)} h depois do Pix</span></div>
        <div><span className="rotulo">Saltos rastreados</span><b className="mono">{laudo.saltos.length}</b><span className="sub">em {camadas.length} camadas</span></div>
      </div>

      <section className="trilha-box" aria-label="Trilha do dinheiro">
        <h2>Trilha do dinheiro</h2>
        <div className="trilha">
          <div className="coluna">
            <span className="rotulo">Origem</span>
            <div className="cartao-conta vitima"><b>Vítima</b><span className="sub">Pix de {reais(laudo.valor)}</span></div>
          </div>
          {camadas.map(col => (
            <div className="coluna" key={col.n}>
              <span className="rotulo">Camada {col.n}</span>
              {col.contas.map(id => {
                const entradas = col.n === 1 ? [] : laudo.saltos.filter(s => s.destino === id);
                return (
                  <div className="cartao-conta" key={id} style={{ borderColor: corBanco(bancoDe(id)) }}>
                    <div className="linha"><b className="mono">{id}</b>{marcada(id) && <span className="selo selo-marcada">marcada</span>}</div>
                    <span className="sub">{bancoDe(id) || "conta de fora"}</span>
                    {entradas.map(s => <span key={s.tx} className="mono entrada">← {reais(s.valor)} às {dataHora(s.quando).slice(6)} de {s.origem}</span>)}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </section>

      <div className="laudo-corpo">
        <section className="texto-laudo">
          <h2>Texto do laudo</h2>
          {naTela.map((p, i) => <p key={i}>{p}</p>)}
          <p className="sub">Os saltos de cada camada estão na trilha acima e entram completos no texto copiado.</p>
        </section>
        <aside className="registro">
          <h2>Registro da fundada suspeita</h2>
          <p className="sub">A Res. BCB 501/2025 obriga a instituição a guardar o que embasou a suspeita. Este laudo serve como esse registro.</p>
          <dl>
            <dt>Regra de rastreio</dt><dd>até 5 camadas, janela de 24 h, valor mínimo R$ 200</dd>
            <dt>Dados usados</dt><dd>transações da instituição e repasses pseudonimizados do consórcio</dd>
          </dl>
          <p className="nota-ia">O texto foi montado a partir de fatos calculados. Nenhuma IA decidiu quem é suspeito.</p>
          <div className="acoes">
            <button type="button" className="btn-secundario" onClick={copiar}>{copiado === "ok" ? "Laudo copiado" : copiado === "erro" ? "Não deu para copiar" : "Copiar laudo"}</button>
            <button type="button" className="btn-principal" onClick={voltar}>Voltar ao grafo</button>
          </div>
        </aside>
      </div>
    </div>
  );
}
