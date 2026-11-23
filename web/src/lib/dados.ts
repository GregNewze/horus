// Tipos e contas sobre o demo.json gerado por `python -m motor.exportar`. A tela não decide nada:
// notas, marcações e laudos vêm prontos do motor.

export type Motivo = { frase: string; pontos: number };
export type No = {
  id: string; banco: string; membro: boolean; papel: string; x: number; y: number;
  token: string; motivos: Motivo[]; marcada_s: string | null; marcada_c: string | null;
};
export type Aresta = { o: string; d: string; tipo: "repasse" | "teste"; valor: number; n: number; desde: string };
export type Foto = {
  ate: string; s: Record<string, number>; c: Record<string, number>;
  recall_s: number; recall_c: number; protegido_s: number; protegido_c: number; golpe_ate_agora: number;
};
export type Salto = { camada: number; origem: string; destino: string; valor: number; quando: string; tx: string };
export type Laudo = {
  tx: string; aberta_em: string; recebido_em: string; conta: string; banco: string; valor: number;
  saltos: Salto[]; texto: string[];
};
export type Anel = {
  rede: string; membros: string[]; visiveis: number; primeira_contestacao: string | null;
  achado_s: string | null; achado_c: string | null;
};
export type Semente = {
  semente: number; recall_sozinha: number; recall_consorcio: number;
  dinheiro_sozinha: number; dinheiro_consorcio: number; clientes: number;
};
export type Demo = {
  meta: {
    inicio: string; fim: string; passo_h: number; fraca: number; forte: number;
    clientes_membros: number; laranjas_membros: number; golpe_total_membros: number;
    instituicoes: { nome: string; consorcio: boolean }[]; sementes: Semente[] | null;
    pedidos_hub?: Record<string, { tokens: number; clientes: number }>;
  };
  nos: No[]; arestas: Aresta[]; fotos: Foto[]; laudos: Laudo[]; aneis: Anel[];
};

export type Modo = "s" | "c";

export const ms = (t: string) => Date.parse(t.replace(" ", "T"));

export const BANCOS: Record<string, { cor: string; letra: string }> = {
  "Fintech Tambaqui": { cor: "var(--b-tambaqui)", letra: "T" },
  "Coop Cupuaçu": { cor: "var(--b-cupuacu)", letra: "C" },
  "Coop Guaraná": { cor: "var(--b-guarana)", letra: "G" },
  "Fintech Jaraqui": { cor: "var(--b-jaraqui)", letra: "J" },
};
export const corBanco = (b: string) => BANCOS[b]?.cor ?? "var(--b-fora)";
export const letraBanco = (b: string) => BANCOS[b]?.letra ?? "·";

export const LARANJA = new Set(["laranja", "coletora"]);

/** Motivos que a instituição calcula sozinha, com os próprios dados (motor/sinais.py). */
export const ehSinalLocal = (frase: string) =>
  /^(repassou|conta com|recebeu \d+ Pix de teste|dinheiro de|\d+ Pix recebido)/.test(frase);

export function estado(no: No, modo: Modo, foto: Foto, t: number): "neutra" | "fraca" | "marcada" {
  const quando = modo === "s" ? no.marcada_s : no.marcada_c;
  if (quando && ms(quando) <= t) return "marcada";
  return foto[modo][no.id] !== undefined ? "fraca" : "neutra";
}

export const pct = (v: number) => `${Math.round(v * 100)}%`;
export const reais = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 });
export const dataHora = (t: string | number) => {
  const d = new Date(typeof t === "number" ? t : ms(t));
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getDate())}/${p(d.getMonth() + 1)} ${p(d.getHours())}:${p(d.getMinutes())}`;
};
export const horas = (a: string, b: string) => Math.round((ms(b) - ms(a)) / 3_600_000);

export function mediana(v: number[]) {
  if (!v.length) return null;
  const s = [...v].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/**
 * Posição das contas: cada grupo ligado (um anel) vira um círculo, os grupos ficam numa grade e as
 * contas soltas numa faixa embaixo. As duas telas usam as mesmas posições, então a mesma conta
 * está no mesmo lugar à esquerda e à direita.
 */
export function layout(demo: Demo, W = 1000) {
  const viz: Record<string, string[]> = Object.fromEntries(demo.nos.map(n => [n.id, []]));
  for (const a of demo.arestas) if (viz[a.o] && viz[a.d]) { viz[a.o].push(a.d); viz[a.d].push(a.o); }
  const visto = new Set<string>();
  const grupos: string[][] = [];
  const ids = [...demo.nos.map(n => n.id)].sort((a, b) => viz[b].length - viz[a].length);
  for (const ini of ids) {
    if (visto.has(ini)) continue;
    // Busca em profundidade: vizinhos ficam lado a lado no círculo, com menos cruzamentos
    const ordem: string[] = [], pilha = [ini];
    while (pilha.length) {
      const v = pilha.pop()!;
      if (visto.has(v)) continue;
      visto.add(v); ordem.push(v);
      for (const w of [...viz[v]].sort((a, b) => viz[a].length - viz[b].length)) if (!visto.has(w)) pilha.push(w);
    }
    grupos.push(ordem);
  }
  const aneis = grupos.filter(g => g.length >= 3).sort((a, b) => b.length - a.length);
  const soltas = grupos.filter(g => g.length < 3).flat();
  const cols = 4, cel = W / cols, pos: Record<string, { x: number; y: number }> = {};
  aneis.forEach((g, i) => {
    const cx = cel * (i % cols) + cel / 2, cy = cel * Math.floor(i / cols) + cel / 2;
    const r = Math.min(cel / 2 - 34, 26 + g.length * 5.5);
    g.forEach((id, k) => {
      const ang = -Math.PI / 2 + (2 * Math.PI * k) / g.length;
      pos[id] = { x: cx + r * Math.cos(ang), y: cy + r * Math.sin(ang) };
    });
  });
  const topo = cel * Math.ceil(aneis.length / cols) + 10;
  const porLinha = 16, passo = (W - 80) / (porLinha - 1);
  soltas.forEach((id, k) => { pos[id] = { x: 40 + (k % porLinha) * passo, y: topo + 40 + Math.floor(k / porLinha) * 46 }; });
  const H = topo + 40 + Math.ceil(soltas.length / porLinha) * 46 + 10;
  return { pos, W, H, topo };
}

export type BaseValidacao = {
  nome: string; descricao: string; sementes: number;
  recall_s: [number, number]; recall_c: [number, number]; prec_c: [number, number] | null;
  din_s: [number, number] | null; din_c: [number, number] | null; nota?: string;
};
export const faixaPct = (f: [number, number] | null) =>
  !f ? "—" : Math.round(f[0] * 100) === Math.round(f[1] * 100) ? pct(f[0]) : `${Math.round(f[0] * 100)}–${pct(f[1])}`;
