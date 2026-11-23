# Briefing de design para o Stitch (Hórus)

Cole o bloco abaixo no Stitch (modo web, desktop 1440 px). Depois peça as variações de cada tela.

---

Crie a interface web de um produto antifraude chamado **Hórus**, para analistas de prevenção à fraude de cooperativas de crédito e fintechs pequenas no Brasil. Todo o texto em português do Brasil. Tom sério de ferramenta de compliance, sem cara de cripto nem de jogo. Fundo escuro azul-petróleo quase preto, superfícies um pouco mais claras, uma cor de destaque verde-água. Estados de risco: âmbar para "suspeita fraca" e vermelho para "marcada". Tipografia: Space Grotesk nos títulos, Inter no texto, IBM Plex Mono para números, horários e tokens. Bordas finas, cantos de 8 px, sem gradiente roxo, sem emoji.

**Tela 1: "Sozinha × Juntas" (a principal)**
- Topo: logo "Hórus", seletor de instituição (Coop Cupuaçu, Coop Guaraná, Fintech Jaraqui, Fintech Tambaqui) e um selo "dados sintéticos".
- Centro: dois painéis de grafo lado a lado, do mesmo tamanho. À esquerda, "Cada instituição sozinha"; à direita, "Consórcio". Cada nó é uma conta: a cor da borda mostra a instituição (4 tons discretos e cinza para bancos de fora), o preenchimento mostra o estado (neutro, âmbar = fraca, vermelho = marcada). As arestas são repasses rápidos. No painel do consórcio aparece um anel de 10 contas em vermelho que no painel da esquerda está só em âmbar e espalhado.
- Embaixo dos grafos: linha do tempo de 30 dias com botão de play, marcador do dia e hora atuais (ex.: "22/10 15:00") e pontinhos onde houve contestação MED.
- Faixa de números, com os dois modos lado a lado: "Laranjas encontrados 68% → 89%", "Dinheiro de golpe que dava para segurar 35% → 52%", "Alarmes falsos 0".

**Tela 2: painel lateral de uma conta** (abre ao clicar num nó)
- Identificador da conta, instituição, nota (ex.: 100 de 60 necessários) com barra dividida pelos sinais: "repassou 98% em menos de 1 hora +30", "conta com 52 dias já recebeu R$ 40.385 +15", "Pix de teste de centavos +10", "trocou repasses com 7 contas suspeitas +45", "2 outras instituições relataram +10", "anel com 10 contas +10".
- Bloco "O que o hub do consórcio viu": só um token hexadecimal de 16 caracteres (ex.: 3f9a1c07be52d4e8), a nota e os códigos dos motivos. Texto pequeno: "Nome, CPF e saldo não saem da instituição."

**Tela 3: Laudo Muninn**
- Título "Laudo do Pix contestado", valor (R$ 8.538,09), data, conta que recebeu.
- Trilha do dinheiro em camadas, da esquerda para a direita: vítima → camada 1 → camada 2 → corretora de cripto, com valor e horário em cada seta.
- Texto do laudo em parágrafos curtos, com os motivos de cada conta, e o rótulo "Registro da fundada suspeita (Res. BCB 501/2025)".
- Botão "Copiar laudo".

---

## O que a tela recebe (contrato do JSON `demo.json`)
- `meta`: início, fim, passo em horas, cortes de nota (fraca 25, forte 60), instituições.
- `nos[]`: id, banco, membro, papel (gabarito, só para o placar final), x, y (posição já calculada), token, motivos, quando foi marcada em cada modo.
- `arestas[]`: o, d, tipo (repasse ou teste), valor, n, desde.
- `fotos[]` (a cada 6 h): `s` e `c` = {conta: nota} acima de fraca nos modos sozinha e consórcio; recall e dinheiro protegido acumulados.
- `laudos[]`: tx, conta, valor, saltos (camada, origem, destino, valor, quando), texto.

---

## Prompts exatos usados em 22/11 (refazer na conta GregNewze)
Mandar cada um como UMA linha só (Enter envia a mensagem). Modo Web.

1. Estilo: o primeiro parágrafo do briefing acima ("Interface web desktop (1440px) de um produto antifraude chamado Hórus ... sem emoji.").

2. Tela principal:
Crie uma NOVA tela, a principal do produto, chamada "Sozinha × Juntas", no mesmo estilo. Nunca use a palavra "anônimo": use "pseudonimizado". Não cite integração com o BACEN. Datas em 2026. Sem lista de clientes e sem CPF: o produto mostra contas como identificadores curtos (ex.: C02023). Topo: logo Hórus, seletor de instituição (Coop Cupuaçu, Coop Guaraná, Fintech Jaraqui, Fintech Tambaqui) e selo "dados sintéticos". Centro: dois painéis de grafo lado a lado, mesmo tamanho: à esquerda "Cada instituição sozinha", à direita "Consórcio". Cada nó é uma conta: a borda mostra a instituição (4 tons discretos, cinza para bancos de fora), o preenchimento mostra o estado (neutro, âmbar = fraca, vermelho = marcada). Arestas finas são repasses rápidos. No painel Consórcio aparece um anel de 10 contas em vermelho ligado entre si; no painel da esquerda as mesmas contas aparecem soltas e só em âmbar. Abaixo dos grafos: linha do tempo de 30 dias (01/10 a 31/10) com botão play, marcador "22/10 15:00" e pequenos pontos vermelhos onde houve contestação MED. Faixa de 3 números comparando os modos: "Laranjas encontrados 68% → 89%", "Dinheiro de golpe que dava para segurar 35% → 52%", "Alarmes falsos 0 → 0". Coluna direita: painel da conta C02023 com nota 100 (corte 60) e barra empilhada pelos sinais: "repassou 98% em menos de 1 hora +30", "conta com 52 dias já recebeu R$ 40.385 +15", "Pix de teste de centavos +10", "trocou repasses com 7 contas suspeitas +45", "2 outras instituições relataram +10", "anel com 10 contas +10"; e um bloco "O que o hub do consórcio viu" mostrando só o token 3f9a1c07be52d4e8, a nota e os códigos dos motivos, com a frase "Nome, CPF e saldo não saem da instituição." Botão "Abrir laudo Muninn".

3. Laudo: Crie a tela "Laudo Muninn", no mesmo estilo e com a mesma barra lateral. Nunca use a palavra "anônimo": use "pseudonimizado". Não cite integração com o BACEN. Datas em 2026. Instituições fictícias: Coop Cupuaçu, Coop Guaraná, Fintech Jaraqui, Fintech Tambaqui, Banco Açaí (fora do consórcio). Topo: "Laudo do Pix contestado", valor R$ 8.538,09, recebido em 22/10/2026 15:23 pela conta C01171 (Fintech Tambaqui), contestação MED aberta em 22/10 21:40. Centro: trilha do dinheiro em colunas da esquerda para a direita: Vítima → Camada 1: C01171 → Camada 2: C02023 (dois Pix de R$ 4.031,31 às 15:38 e 15:39) → Camada 3: C01475 Coop Guaraná (R$ 3.916,83 às 15:41) → Camada 4: Corretora Cripto Boto, Banco Açaí (R$ 3.916,83 às 20:22). Cada seta mostra valor e horário; só as contas marcadas pelo Hórus têm selo "marcada" em vermelho (a corretora não). Abaixo, à esquerda, o texto do laudo em parágrafos curtos, um por conta, só com os motivos dados, sem inventar números. À direita: caixa "Registro da fundada suspeita (Res. BCB 501/2025)" com data e hora da geração, regra de rastreio usada ("até 5 camadas, janela de 24 h, valor mínimo R$ 200") e a nota "O texto foi montado a partir de fatos calculados; nenhuma IA decidiu quem é suspeito". Botões "Copiar laudo" e "Voltar ao grafo".
