"""Baixa as tabelas públicas do IBGE usadas pelo gerador e grava em dados/fontes/.

Fontes: SIDRA (Censo 2022 e PNAD Contínua TIC) e API IBGE Nomes. Só biblioteca padrão.
Uso: python3 scripts/baixar_fontes.py
"""
import gzip
import json
import re
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "dados" / "fontes"
SIDRA = "https://apisidra.ibge.gov.br/values"
META = "https://servicodados.ibge.gov.br/api/v3/agregados/{t}/metadados"
ESTADOS = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
NOMES = "https://servicodados.ibge.gov.br/api/v2/censos/nomes/ranking?decada={d}&sexo={s}"


def baixar(url: str, tentativas: int = 4):
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                corpo = r.read()
            if corpo[:2] == b"\x1f\x8b":  # a API às vezes responde compactada
                corpo = gzip.decompress(corpo)
            return json.loads(corpo.decode("utf-8"))
        except Exception as e:  # a API do IBGE às vezes falha; tenta de novo
            if i == tentativas - 1:
                raise RuntimeError(f"falhou: {url}") from e
            time.sleep(3 * (i + 1))


def categorias(tabela: int, cls: int) -> list[dict]:
    meta = baixar(META.format(t=tabela))
    return next(c for c in meta["classificacoes"] if c["id"] == cls)["categorias"]


def idades_simples(tabela: int) -> list[int]:
    """Idades em anos completos: 'Menos de 1 ano', '1 ano', 'N anos' e '100 anos ou mais'."""
    ids = []
    for c in categorias(tabela, 287):
        if re.fullmatch(r"Menos de 1 ano|1 ano|\d+ anos|100 anos ou mais", c["nome"]):
            ids.append(c["id"])
    return ids


def faixa(nome: str):
    """Converte o nome de um grupo de idade em (início, fim); None se não for um grupo simples."""
    if m := re.fullmatch(r"(\d+) a (\d+) anos", nome):
        return int(m[1]), int(m[2])
    if m := re.fullmatch(r"(\d+) ou (\d+) anos", nome):
        return int(m[1]), int(m[2])
    if m := re.fullmatch(r"(\d+) anos ou mais", nome):
        return int(m[1]), 200
    return None


def grupos_finos(tabela: int, inicio: int = 0) -> list[int]:
    """Escolhe os grupos de idade mais finos que cobrem as idades sem sobreposição, a partir de `inicio`."""
    por_inicio = {}
    for c in categorias(tabela, 58):
        f = faixa(c["nome"])
        if f and f[0] >= inicio and (f[0] not in por_inicio or f[1] < por_inicio[f[0]][1][1]):
            por_inicio[f[0]] = (c["id"], f)
    escolhidos, a = [], inicio
    while a in por_inicio:
        cid, (ini, fim) = por_inicio[a]
        escolhidos.append(cid)
        if fim == 200:
            break
        a = fim + 1
    if not escolhidos or faixa_fim(tabela, escolhidos[-1]) != 200:
        raise RuntimeError(f"tabela {tabela}: grupos de idade não cobrem tudo a partir de {inicio}")
    return escolhidos


def faixa_fim(tabela: int, cid: int) -> int:
    nome = next(c["nome"] for c in categorias(tabela, 58) if c["id"] == cid)
    return faixa(nome)[1]


def sidra(tabela: int, variaveis, classes: dict, nivel: str = "n3/all", periodo: str = "2022") -> list[dict]:
    """Consulta o SIDRA e devolve linhas {dimensão: nome, ..., valor: float|None}."""
    partes = [f"t/{tabela}", nivel, f"v/{','.join(map(str, variaveis))}", f"p/{periodo}"]
    for cls, cats in classes.items():
        partes.append(f"c{cls}/{cats if isinstance(cats, str) else ','.join(map(str, cats))}")
    dados = baixar(f"{SIDRA}/{'/'.join(partes)}")
    cab, linhas = dados[0], dados[1:]
    saida = []
    for l in linhas:
        reg = {cab[k]: l[k] for k in l if k.startswith("D") and k.endswith("N")}
        v = l["V"]
        reg["valor"] = float(v) if re.fullmatch(r"-?\d+(\.\d+)?", v) else None
        saida.append(reg)
    return saida


def gravar(nome: str, fonte: str, linhas) -> None:
    FONTES.mkdir(parents=True, exist_ok=True)
    (FONTES / f"{nome}.json").write_text(json.dumps({"fonte": fonte, "linhas": linhas}, ensure_ascii=False), encoding="utf-8")
    print(f"{nome:28s} {len(linhas) if isinstance(linhas, list) else len(linhas.keys()):>7} linhas")


def main(so_nomes: bool = False):
    if so_nomes:
        return nomes()
    gravar("pop_uf_raca_sexo_idade", "IBGE, Censo 2022, tabela 9606",
           sidra(9606, [93], {86: "allxt", 2: "allxt", 287: idades_simples(9606)}))
    gravar("situacao_domicilio", "IBGE, Censo 2022, tabela 10089 (localização: total)",
           sidra(10089, [93], {2: "allxt", 58: grupos_finos(10089), 2661: [32776], 1: "allxt"}))
    gravar("instrucao_18mais", "IBGE, Censo 2022, tabela 10061",
           sidra(10061, [2667], {1568: "allxt", 58: grupos_finos(10061, 18), 2: "allxt", 86: "allxt"}))
    gravar("renda_per_capita", "IBGE, Censo 2022, tabela 10296",
           sidra(10296, [13604], {2: "allxt", 86: "allxt", 386: "allxt"}))
    gravar("deficiencia_sexo_idade", "IBGE, Censo 2022, tabela 10125",
           sidra(10125, [11852, 12785], {2: "allxt", 58: grupos_finos(10125, 2)}))
    gravar("deficiencia_tipos", "IBGE, Censo 2022, tabela 10127",
           sidra(10127, [12785], {1509: "allxt"}))
    gravar("internet_domicilio", "IBGE, Censo 2022, tabela 9942",
           sidra(9942, [382], {2072: "allxt", 86: "allxt", 58: grupos_finos(9942)}))
    gravar("uso_internet_idade", "IBGE, PNAD Contínua TIC 2025, tabela 7334",
           sidra(7334, [10659], {58: "allxt"}, periodo="2025"))
    gravar("equipamento_internet", "IBGE, PNAD Contínua TIC 2025, tabela 7337 (Brasil)",
           sidra(7337, [10650], {680: "all"}, nivel="n1/all", periodo="2025"))
    nomes()


def nomes():
    # A API de nomes devolve só os 20 mais comuns; por estado são 27 rankings diferentes por década e sexo.
    estados = {e["nome"]: e["id"] for e in baixar(ESTADOS)}
    tabela = {}
    for uf, cod in estados.items():
        for d in range(1930, 2020, 10):
            for s in ("F", "M"):
                r = baixar(NOMES.format(d=d, s=s) + f"&localidade={cod}")
                tabela[f"{uf}|{d}|{s}"] = [(x["nome"], x["frequencia"]) for x in r[0]["res"]] if r else []
    gravar("nomes_uf_decada_sexo", "IBGE Nomes (Censo 2010), ranking por estado, década de nascimento e sexo", tabela)


if __name__ == "__main__":
    import sys
    main(so_nomes="--nomes" in sys.argv)
