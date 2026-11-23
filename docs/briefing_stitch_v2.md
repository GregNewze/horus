# Briefing do Stitch, versão 2 (22/11): refinar as telas a partir do front atual

Colar no projeto "Hórus Antifraude Dashboard" (modo web, desktop 1440 px). Junto, enviar os prints do front atual como referência.

---

Refine a interface do **Hórus**, um consórcio antifraude para cooperativas de crédito e fintechs pequenas no Brasil. Público: analistas de prevenção à fraude e júri técnico de hackathon. Todo o texto em português do Brasil, frases curtas e concretas.

**Estilo (manter):** linha de produto da Apple. Fundo claro #fbfbfd, superfícies brancas com sombra bem suave, cantos de 28 px nos cartões grandes e 14 px nos pequenos, tipografia grande e muito espaço livre. Uma só cor forte: vermelho #e0301e para "marcada". Âmbar #ff9f0a com borda tracejada para "suspeita fraca". Cinza #6e6e73 para texto de apoio (nunca mais claro que isso). Números em fonte mono tabular. Sem gradiente, sem emoji, sem tema escuro.

**Cores das instituições (só na borda do nó, nunca no texto):** Tambaqui #0e7c86, Cupuaçu #af52de, Guaraná #007aff, Jaraqui #8a6d48, bancos de fora #b0b0b6. Não usar verde, que lê como "seguro".

**Tela 1: Sozinha × Juntas (principal)**
- Topo fixo: marca "Hórus" com ícone de olho, controle segmentado "Sozinha × Juntas | Laudos | Como funciona" e botão preto "Ver apresentação".
- Abertura centralizada: rótulo "Consórcio antifraude para cooperativas e fintechs", título "Sozinhas, elas veem pontos soltos." com a segunda linha em vermelho "Juntas, veem o anel.", e um parágrafo curto.
- Quatro números numa faixa: 72% dos laranjas encontrados (juntas 72%, sozinha 60%, com duas barrinhas); 39% do dinheiro de golpe caiu em conta já marcada (juntas 39%, sozinha 28%); 36 h de vantagem na mediana para achar um anel; 0 alarmes falsos entre 1.567 clientes.
- Cartão grande com dois grafos lado a lado ("Sozinha" e "Juntas"). Cada anel de contas desenhado num círculo. Nó pequeno e vazio = conta sem suspeita; nó maior com letra da instituição = suspeita; nó vermelho com letra branca e halo = marcada. Em "Juntas" aparecem linhas entre instituições que em "Sozinha" não existem. Contas sem ligação ficam numa faixa discreta embaixo, só com a contagem.
- Abaixo: botão de play redondo, linha do tempo de 30 dias, data e hora atuais ("16/10 06:00"), velocidade 1× e 2×, caixa "Mostrar quem era laranja de verdade".
- Seção "Cada anel, achado antes": uma linha por anel (R1 a R8) num eixo de datas; ponto vermelho = consórcio achou, ponto cinza = sozinha achou, traço preto = primeira contestação MED, ganho à direita ("+54 h", "empate").

**Tela 2: gaveta da conta (abre ao tocar num nó)**
- Conta, instituição e nota com barra dividida por motivo: "repassou 97% do que recebeu em menos de 1 hora +30", "aberta há 31 dias e já recebeu R$ 47.689 +15", "ligada a 3 outras contas suspeitas por repasse rápido ou Pix de teste +45", "2 outras instituições relataram Pix suspeitos com esta conta +10", "faz parte de um anel com 5 contas +10".
- Separar "sinais da própria instituição" de "o que o consórcio acrescentou".
- Bloco "O que o hub viu": token hexadecimal, nota e motivos. Texto: "Token OPRF no lugar da conta. Nome, CPF e saldo ficam na instituição. Pseudonimizado, não anônimo."

**Tela 3: Laudo do Pix contestado**
- Rótulo "Laudo Muninn · Pix T0079602", título "Laudo do Pix contestado" e seletor de contestação à direita.
- Quatro fatos: valor contestado R$ 8.598,63 (vermelho), recebido em 18/10 12:50 na conta C02295 da Fintech Tambaqui, contestação MED aberta em 18/10 23:50 (11 h depois), 6 saltos em 3 camadas.
- "Trilha do dinheiro": colunas Origem → Camada 1 → Camada 2 → Camada 3, um cartão por conta com borda esquerda na cor da instituição, selo "marcada" e, em mono, cada valor recebido com horário.
- Texto do laudo em parágrafos curtos, um por conta, e ao lado o cartão "Registro da fundada suspeita" (Res. BCB 501/2025), com a regra de rastreio, os dados usados, a frase "O texto foi montado a partir de fatos calculados. Nenhuma IA decidiu quem é suspeito." e os botões "Copiar laudo" e "Voltar ao grafo".

**Celular (390 px):** marca e botão na primeira linha, controle segmentado ocupando a largura toda na segunda. Números em 2 × 2 sem cortar texto. Grafos empilhados.

**Não usar:** "anônimo", "Motor BACEN", "IA detecta", nomes reais de bancos, datas que não sejam outubro de 2026 da simulação.

Peça 2 variações da Tela 1 focadas em deixar o grafo mais legível (tamanho da letra no nó, menos ruído nas contas sem ligação), mantendo o resto.
