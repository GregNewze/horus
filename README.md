# Hórus

**Siga o dinheiro até a rede inteira.**

Hórus encontra redes de contas laranja no Pix. Ele trata as transações como uma rede, marca os grupos de contas que só servem de passagem para dinheiro de golpe e explica em português por que cada conta foi marcada. É feito para fintechs e cooperativas que precisam cumprir o MED 2.0 e não têm acesso às ferramentas caras dos grandes bancos.

Projeto do time Northern no Hack Brasil 2026, trilha Cibersegurança.

## Partes

| Parte | O que faz |
|---|---|
| **Hórus** | Tela com o grafo da rede inteira, onde os anéis de laranjas aparecem |
| **Muninn** | Parte de um Pix contestado, segue o dinheiro conta por conta e escreve o laudo |
| **Ouroboros** | Detecta o dinheiro que dá a volta e retorna para perto da origem |

## Dados

Todas as transações são sintéticas, geradas pelo próprio repositório. Nomes, CPFs e chaves Pix são fictícios. Nenhum dado real de pessoa ou instituição é usado.

## Validação externa

Além do gerador próprio, o motor foi testado em mundos do **PixSim**, simulador independente de golpes no Pix calibrado com dados do BCB:

> Zeimarani, B., Khatib, A., Mousavinasr, S. e Figueiredo, C. M. S. (2026). *PixSim: a calibrated open-source simulator of instant-payment fraud, recovery and interdiction under analyst capacity constraints.* Apache-2.0. https://github.com/BashirZeimarani/pixsim_public

O PixSim é usado como dependência externa, sem cópia de código para este repositório (`validacao/pixsim_adaptar.py` só converte a saída). Ele simula uma instituição; a divisão das contas entre seis instituições é hipótese nossa.

Resultado em 3 sementes (20 mil contas, 30 dias): o consórcio achou de 50% a 56% dos laranjas, contra 40% a 48% das instituições sozinhas. A precisão caiu de 98–100% para 83–90%, porque contas de saída (lojas e corretoras que recebem de muitos laranjas) viraram alarme falso. O dinheiro protegido ficou praticamente igual. Também testamos na base IBM AMLworld (lavagem corporativa lenta), onde as regras de repasse em 1 hora não acham nada.

## Rodar

```
python gerador/gerar.py --semente 42
python -m motor.exportar --saida web/public/demo.json
cd web && npm install && npm run dev
```

## Licença

MIT
