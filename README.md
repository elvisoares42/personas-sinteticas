# Personas Sintéticas

Base aberta de **personas sintéticas que retratam a população brasileira**, feita para a comunidade de UX usar em pesquisa, testes com agentes de IA e ensino.

Cada persona é uma pessoa fictícia sorteada a partir de dados públicos do IBGE: a proporção de idades, sexos, cor ou raça, estados, escolaridade, renda, deficiência e uso de internet da amostra bate com o Censo 2022 e a PNAD TIC 2025 (ver [docs/validacao-v0.md](docs/validacao-v0.md)).

> Personas sintéticas **não substituem** pesquisa com pessoas reais, em especial com pessoas com deficiência. Use como triagem e para ampliar repertório, não como prova.

## O que tem na v0

- **100 mil personas** da população toda (todas as idades), em PT-BR.
- Só maiores de 18 anos são marcados como `testavel = sim`; crianças e adolescentes entram para o retrato estatístico.
- Gerador **determinístico**: a persona nº N é sempre a mesma, gere-se mil ou 100 mil. Dá para gerar mais com o mesmo script.
- Para cada persona: os campos abaixo e uma **ficha em texto** pronta para dar a um agente de IA.

| Campo | Status | Fonte |
|---|---|---|
| UF, região, cor ou raça, sexo, idade | ✅ | Censo 2022, tabela 9606 (sorteio conjunto) |
| Ano de nascimento e geração | ✅ | calculado (silenciosa, boomer, X, Y, Z, Alfa) |
| Nome | ✅ / ⚠️ | IBGE Nomes (Censo 2010), ranking por estado, década e sexo; peso pela raiz da frequência (o ranking só traz o top 20) e, fora de 1930–2010, a década mais próxima |
| Sobrenome | ⚠️ | lista de sobrenomes comuns (não há tabela oficial) |
| Urbano ou rural | ✅ | Censo 2022, tabela 10089 |
| Escolaridade (18+) | ✅ | Censo 2022, tabela 10061 |
| Renda domiciliar per capita | ✅ / ⚠️ | Censo 2022, tabela 10296 (por UF, sexo e cor ou raça; sem ligação com idade e escolaridade) |
| Deficiência e tipos de dificuldade | ✅ / ⚠️ | Censo 2022, tabelas 10125 e 10127 (combinação de tipos sorteada de forma independente) |
| Internet em casa | ✅ | Censo 2022, tabela 9942 |
| Usou internet nos últimos 3 meses (10+) e só pelo celular | ✅ / ⚠️ | PNAD Contínua TIC 2025, tabelas 7334 e 7337 (independente da internet em casa) |

O detalhe de cada campo fica em `saida/campos.json`.

## Como gerar

Só Python 3.9+ (biblioteca padrão).

```bash
python3 scripts/baixar_fontes.py
python3 scripts/gerar.py 100000
python3 scripts/validar.py
scripts/checar_termos.sh
```

- `baixar_fontes.py`: baixa as tabelas do SIDRA/IBGE e da API IBGE Nomes para `dados/fontes/`.
- `gerar.py`: grava `saida/personas.csv`, `saida/personas.jsonl` (com a ficha) e `saida/campos.json`.
- `validar.py`: compara a amostra com o IBGE e grava `docs/validacao-v0.md`.
- `checar_termos.sh`: barra a publicação se aparecer algum termo da lista local `.termos-proibidos` (fora do git).

## Limitações da v0

- **Retrato de 2022**: idades e campos do Censo 2022 (a ficha diz "no Censo de 2022 tinha N anos" e o ano de nascimento); o uso de internet é da PNAD 2025.
- **Ligações entre campos**: o sorteio é conjunto só em UF × cor ou raça × sexo × idade. Os outros campos dependem dessas quatro variáveis, mas não uns dos outros (ex.: renda não depende da escolaridade; uso de internet não depende da renda). Isso suaviza correlações reais.
- **Universo**: renda e internet em casa vêm de moradores de domicílios particulares permanentes; aplicamos à população toda.
- **Nomes**: o ranking do IBGE traz só os 20 nomes mais comuns por estado, década e sexo; nomes raros não aparecem.
- Não há jornadas (transporte, saúde, alimentação, finanças, telecom, moradia), fatores políticos nem renda individual. Ficam para as próximas versões.

## Próximas versões

1. **Jornadas**: serviços usados e dores típicas por segmento, a partir de dados abertos (Consumidor.gov.br, Banco Central, ANS, Anatel) e do feed público de avaliações da App Store, só agregados e com tratamento igual para todas as empresas.
2. **Squad de especialistas**: avaliadores de produto, UX, UI, desenvolvimento, acessibilidade, marketing, UX writing e privacidade, com ferramentas como axe e Lighthouse.
3. **Integração com o MatrAIx** (github.com/MatrAIx-ai/MatrAIx, MIT) para testes qualitativos com vídeo, áudio e pensar em voz alta, e quantitativos só com formulário.

## Licenças (propostas)

- Código: MIT.
- Base de personas: CC BY 4.0.
- Dados de origem: IBGE (uso livre com citação da fonte).

## Decisões

Ver [DECISOES.md](DECISOES.md).
