"""Compara as personas geradas com as tabelas do IBGE e grava docs/validacao-v0.md.

Para cada variável, % na amostra × % na fonte e a diferença em pontos percentuais (pp).
Com 100 mil personas, o erro de amostragem fica abaixo de ~0,3 pp; acima de 1 pp é sinal de problema.
Uso: python3 scripts/validar.py
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gerar import FONTES, RAIZ, SAIDA, UF_REGIAO, faixa  # noqa: E402

LIMITE_PP = 1.0
FAIXAS = [(0, 4), (5, 9), (10, 14), (15, 19), (20, 24), (25, 29), (30, 39), (40, 49), (50, 59), (60, 69), (70, 79), (80, 200)]


def carregar(nome):
    return json.loads((FONTES / f"{nome}.json").read_text(encoding="utf-8"))["linhas"]


def pct(c: Counter) -> dict:
    t = sum(c.values())
    return {k: 100 * v / t for k, v in c.items()} if t else {}


def nome_faixa(i: int) -> str:
    for a, b in FAIXAS:
        if a <= i <= b:
            return f"{a}+" if b == 200 else f"{a}–{b}"


def main():
    pessoas = list(csv.DictReader(open(SAIDA / "personas.csv", encoding="utf-8")))
    for p in pessoas:
        p["idade"] = int(p["idade"])
    pop = carregar("pop_uf_raca_sexo_idade")
    fonte, amostra = {}, {}

    def par(nome, f: Counter, a: Counter):
        fonte[nome], amostra[nome] = pct(f), pct(a)

    sexo_m = {"Homens": "Homem", "Mulheres": "Mulher"}
    for var, chave_f, chave_a in [("Sexo", lambda l: sexo_m[l["Sexo"]], lambda p: p["sexo"]),
                                  ("Cor ou raça", lambda l: l["Cor ou raça"], lambda p: p["cor_raca"]),
                                  ("UF", lambda l: l["Unidade da Federação"], lambda p: p["uf"]),
                                  ("Região", lambda l: UF_REGIAO[l["Unidade da Federação"]], lambda p: p["regiao"]),
                                  ("Grupo de idade", lambda l: nome_faixa(faixa(l["Idade"])[0]), lambda p: nome_faixa(p["idade"]))]:
        f = Counter()
        for l in pop:
            f[chave_f(l)] += l["valor"] or 0
        par(var, f, Counter(chave_a(p) for p in pessoas))

    f = Counter()
    for l in carregar("situacao_domicilio"):
        f[l["Situação do domicílio"]] += l["valor"] or 0
    par("Situação do domicílio", f, Counter(p["situacao_domicilio"] for p in pessoas))

    f = Counter()
    for l in carregar("instrucao_18mais"):
        f[l["Nível de instrução"]] += l["valor"] or 0
    par("Instrução (18+)", f, Counter(p["instrucao"] for p in pessoas if p["idade"] >= 18))

    f = Counter()
    for l in carregar("renda_per_capita"):
        f[l["Classes de rendimento nominal mensal domiciliar per capita"]] += l["valor"] or 0
    par("Renda domiciliar per capita", f, Counter(p["renda_per_capita"] for p in pessoas))

    f = Counter()
    for l in carregar("deficiencia_sexo_idade"):
        f["com deficiência" if "com deficiência" in l["Variável"] else "total"] += l["valor"] or 0
    par("Pessoa com deficiência (2+)", Counter({"sim": f["com deficiência"], "não": f["total"] - f["com deficiência"]}),
        Counter(p["deficiencia"] for p in pessoas if p["idade"] >= 2))

    f = Counter()
    for l in carregar("internet_domicilio"):
        f[l["Existência de conexão domiciliar à Internet"].lower()] += l["valor"] or 0
    par("Internet em casa", f, Counter(p["internet_em_casa"] for p in pessoas))

    # Uso de internet (10+): % da PNAD por UF e grupo, ponderado pela população do Censo de cada célula
    uso = {(l["Unidade da Federação"], l["Grupo de idade"]): (l["valor"] or 0) / 100 for l in carregar("uso_internet_idade")}
    grupos = sorted({g for _, g in uso}, key=lambda g: faixa(g)[0])
    peso = defaultdict(float)
    for l in pop:
        i = faixa(l["Idade"])[0]
        g = next((g for g in grupos if faixa(g)[0] <= i <= faixa(g)[1]), None)
        if g:
            peso[(l["Unidade da Federação"], g)] += l["valor"] or 0
    sim = sum(peso[k] * uso.get(k, 0) for k in peso)
    par("Usa internet (10+)", Counter({"sim": sim, "não": sum(peso.values()) - sim}),
        Counter(p["usa_internet"] for p in pessoas if p["idade"] >= 10))

    linhas = ["# Validação da v0: amostra × IBGE", "",
              f"{len(pessoas):,} personas comparadas com as tabelas de origem. Diferença em pontos percentuais (pp); "
              f"acima de {LIMITE_PP:g} pp aparece como ⚠️.".replace(",", "."), "",
              "Observações:",
              "- Renda e internet em casa: o universo do IBGE são moradores de domicílios particulares permanentes; as personas incluem toda a população.",
              "- Uso de internet: % da PNAD TIC 2025 aplicado à população do Censo 2022.", ""]
    pior = 0.0
    for var in fonte:
        linhas += [f"## {var}", "", "| Categoria | IBGE | Personas | Diferença |", "|---|---:|---:|---:|"]
        for cat in sorted(fonte[var], key=lambda k: -fonte[var][k]):
            a, b = fonte[var][cat], amostra[var].get(cat, 0.0)
            d = b - a
            pior = max(pior, abs(d))
            linhas.append(f"| {cat} | {a:.2f}% | {b:.2f}% | {d:+.2f} pp{' ⚠️' if abs(d) > LIMITE_PP else ''} |")
        linhas.append("")
    linhas.insert(3, f"**Maior diferença: {pior:.2f} pp** {'(dentro do limite)' if pior <= LIMITE_PP else '(acima do limite)'}.")
    linhas.insert(4, "")
    destino = RAIZ / "docs" / "validacao-v0.md"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"maior diferença {pior:.2f} pp → {destino}")


if __name__ == "__main__":
    main()
