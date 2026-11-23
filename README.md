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

Resultados (o mesmo motor, sem ajuste por base):

| Base | Laranjas achados, sozinha → consórcio | Precisão do consórcio | Dinheiro em conta já marcada |
|---|---|---|---|
| Gerador do Hórus (5 sementes) | 52–79% → 69–83% | 100% | 32–45% → 40–49% |
| PixSim (3 sementes, 20 mil contas) | 38–44% → 48–55% | 99–100% | 31–44% → 32–44% |
| IBM AMLworld (lavagem lenta) | 0% → 0% | — | — |

Em nenhuma base um laranja é marcado antes do primeiro golpe que recebe. No PixSim os laranjas extras do consórcio ficam evidentes depois de usados, então o dinheiro protegido não sobe.

## Privacidade

O identificador da conta vira token por OPRF sobre Ed25519 (`motor/oprf.py`): o membro cega a entrada, o hub aplica a chave k sem ver a conta, o membro tira a cegueira. O hub não tem a chave m dos membros e não testa contas; um membro não calcula token sem o hub, e o hub registra quantos tokens cada membro pede (ataque de dicionário aparece no registro). Hub e membro juntos ainda conseguem testar contas.

## Rodar

```
python gerador/gerar.py --semente 42
python -m motor.exportar --saida web/public/demo.json
cd web && npm install && npm run dev
```

## Licença

MIT
