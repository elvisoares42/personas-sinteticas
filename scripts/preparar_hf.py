"""Monta saida/hf/ para publicar a base no Hugging Face: Parquet, JSONL, campos e cartão do dataset.

Precisa do pyarrow (ambiente do projeto: .venv). Uso: .venv/bin/python scripts/preparar_hf.py
"""
import json
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pcsv
import pyarrow.parquet as pq

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "saida"
HF = SAIDA / "hf"

CARTAO = """---
license: cc-by-4.0
language:
- pt
pretty_name: Personas Sintéticas UX
size_categories:
- 100K<n<1M
task_categories:
- text-generation
tags:
- synthetic
- personas
- brazil
- census
- ux-research
configs:
- config_name: default
  data_files: data/personas.parquet
---

# Personas Sintéticas UX: base de 100 mil personas

{total} personas sintéticas que retratam a população brasileira, para a comunidade de UX usar em pesquisa,
testes com agentes de IA e ensino. Cada persona é sorteada a partir de dados públicos do IBGE (Censo 2022 e
PNAD Contínua TIC 2025): a proporção de idade, sexo, cor ou raça, estado, escolaridade, renda, deficiência e
uso de internet bate com as tabelas de origem (maior diferença: {pior}).

> Personas sintéticas **não substituem** pesquisa com pessoas reais, em especial com pessoas com deficiência.
> Use como triagem e para ampliar repertório, não como prova.

## Arquivos

- `data/personas.parquet` e `data/personas.jsonl`: uma linha por persona, com a coluna `ficha` (texto em PT-BR pronto para dar a um agente de IA).
- `campos.json`: origem de cada campo e se é ✅ dado público ou ⚠️ suposição.
- `validacao-v0.md`: comparação de cada variável com o IBGE.

## Campos

{campos}

`testavel = sim` só para 18+; crianças e adolescentes entram para o retrato estatístico.

## Exemplo de ficha

> {exemplo}

## Limitações

- Retrato de 2022: idades do Censo (a ficha informa o ano de nascimento); uso de internet da PNAD 2025.
- Só UF × cor ou raça × sexo × idade são sorteados juntos; os outros campos dependem dessas quatro, mas não uns dos outros (ex.: renda não depende da escolaridade).
- Nomes: o ranking do IBGE traz só os 20 mais comuns por estado, década e sexo. Sobrenomes são uma lista de sobrenomes comuns (não há tabela oficial).
- Sexo vem do Censo (homem ou mulher). Identidade de gênero (⚠️ estudo acadêmico) e orientação sexual (PNS 2019, experimental) são campos separados, só para 18+. Pessoas intersexo não estão representadas.
- Cor ou raça nas 5 categorias do IBGE; quilombola sorteado à parte.
- Sem jornadas de serviços, fatores políticos ou renda individual nesta versão.

## Como foi gerado

Código aberto (MIT) com gerador determinístico: a persona nº N é sempre a mesma. Fontes: IBGE, Censo 2022
(tabelas 9606, 10089, 10061, 10296, 10125, 10127 e 9942), PNAD Contínua TIC 2025 (tabelas 7334 e 7337) e IBGE Nomes.

## Créditos

Feito para uso com o [MatrAIx](https://github.com/MatrAIx-ai/MatrAIx) (MIT), plataforma de agentes-persona de Li, X. et al.,
"MatrAIx: Simulating the World with 8.3 Billion Persona Agents", arXiv:2608.04205, 2026. Dados de origem: IBGE.

## Licença

CC BY 4.0. Dados de origem: IBGE (uso livre com citação da fonte).
"""


def main():
    if HF.exists():
        shutil.rmtree(HF)
    (HF / "data").mkdir(parents=True)
    texto = pa.string()
    colunas = json.loads((SAIDA / "campos.json").read_text(encoding="utf-8"))
    tipos = {c: texto for c in list(colunas) + ["ficha"]}
    tipos.update({"idade": pa.int16(), "ano_nascimento": pa.int16()})
    tabela = pcsv.read_csv(SAIDA / "personas.csv", convert_options=pcsv.ConvertOptions(
        column_types=tipos, strings_can_be_null=False))
    pq.write_table(tabela, HF / "data" / "personas.parquet", compression="zstd")
    shutil.copy(SAIDA / "personas.jsonl", HF / "data" / "personas.jsonl")
    shutil.copy(SAIDA / "campos.json", HF / "campos.json")
    validacao = (RAIZ / "docs" / "validacao-v0.md").read_text(encoding="utf-8")
    shutil.copy(RAIZ / "docs" / "validacao-v0.md", HF / "validacao-v0.md")
    pior = next(l for l in validacao.splitlines() if l.startswith("**Maior diferença")).split(":")[1].split("**")[0].strip()
    linhas_campos = "\n".join(f"| `{k}` | {v['status']} | {v['origem']} |" for k, v in colunas.items())
    campos = "| Campo | Status | Origem |\n|---|---|---|\n" + linhas_campos + "\n| `ficha` | — | texto gerado a partir dos campos |"
    exemplo = tabela.column("ficha")[1].as_py()
    (HF / "README.md").write_text(CARTAO.format(total=f"{tabela.num_rows:,}".replace(",", "."), pior=pior,
                                                campos=campos, exemplo=exemplo), encoding="utf-8")
    tamanho = sum(f.stat().st_size for f in HF.rglob("*") if f.is_file())
    print(f"{HF}: {tabela.num_rows} linhas, {tamanho / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
