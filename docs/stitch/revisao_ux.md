# Revisão de UX das telas do Stitch (22/11/2026)

Checklist da skill ui-ux-pro-max (prioridades 1 a 10). O banco de busca da skill não está instalado nesta máquina, então a revisão usa a tabela de prioridades padrão da própria skill, não resultados de busca.

## 1. Acessibilidade (crítico)
- Rótulos dos nós no grafo estão com ~7 px: mínimo 12 px; mostrar só a nota no nó e o id no hover/foco e numa lista acessível ao lado (tabela "contas do anel").
- Texto cinza em mono pequeno sobre fundo quase preto: conferir contraste 4,5:1; subir o cinza dos rótulos.
- Fintech Tambaqui e Coop Cupuaçu têm dois verdes parecidos: além da cor, usar letra dentro do nó (T, C, G, J) ou forma da borda.
- Grafo precisa de alternativa em texto (tabela) e foco por teclado nos nós (Tab/setas), com `aria-label` "C02023, Fintech Tambaqui, nota 120, marcada".
- Estado já usa forma além de cor (tracejado = fraca, anel duplo = marcada): manter.

## 2. Interação
- Botões de play e velocidade com alvo de 44 px; play com estado (tocando/pausado) e atalho de espaço.
- Clicar no nó abre o painel da conta; o nó selecionado fica destacado nos dois grafos ao mesmo tempo.

## 4 e 6. Estilo, tipografia e copy
- Logo quebrado (aparece o texto alternativo "Hórus"): fazer logo em SVG.
- "120 / 100" é contraditório: mostrar "120 pontos · corte 60", sem denominador.
- Jargão para tirar: "Topologia Federada", "Visão Federada em Grafo", "Eficácia de captura", "Mitigação financeira", "Antecipação consórcio", "Auditoria forense", "Sessão pseudonimizada", "Sinal local isolado", "Topologia fechada confirmada". Usar: "Sozinha × Juntas", "Consórcio", "Laranjas encontrados", "Dinheiro que dava para segurar", "Alarmes falsos", "Anel achado antes".
- Pix de teste "(R$ 0,05)" foi inventado: vir do JSON.
- Cartões de número com título quebrando em 4 linhas: título de 1 linha, número grande, nota de 1 linha.

## 7. Movimento (GSAP, sem blur, respeitar prefers-reduced-motion)
- O momento principal: ao dar play, as notas sobem foto a foto; no consórcio as ligações entre instituições aparecem e o anel fecha (DrawSVG ou stroke-dashoffset), os nós passam de tracejado para cheio. À esquerda, nada se liga.
- Números da faixa contam até o valor da foto atual (tabular-nums).
- Com reduced-motion: troca de estado sem transição, linha do tempo continua funcionando.

## 10. Dados
- Legenda única entre os grafos (já existe): manter.
- Nota da simulação ("dados sintéticos, semente 42; em 5 sementes 81% a 94%") sempre visível na faixa.
