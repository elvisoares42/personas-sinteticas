"""Extrai das tabelas oficiais da PNS 2019 (orientação sexual autoidentificada, 18+) os percentuais usados pelo gerador.

Baixa o zip do FTP do IBGE se faltar e grava dados/fontes/orientacao_sexual.json.
Precisa do xlrd (ambiente do projeto: .venv). Uso: .venv/bin/python scripts/extrair_pns.py
"""
import json
import urllib.request
import zipfile
from pathlib import Path

import xlrd

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "dados" / "fontes" / "pns2019"
ZIP = "https://ftp.ibge.gov.br/PNS/2019/Orientacao_Sexual_Autoidentificada_da_Populacao_Adulta/PNS_2019_Orientacao_Sexual_Autoidentificada_xls.zip"


def planilha(nome: str):
    return xlrd.open_workbook(str(PASTA / nome)).sheet_by_index(0)


def linhas(s, col: int) -> dict:
    """Rótulo da coluna A → valor numérico da coluna `col` (ignora linhas de título e notas)."""
    out = {}
    for r in range(s.nrows):
        rot, v = str(s.cell_value(r, 0)).strip(), s.cell_value(r, col)
        if rot and isinstance(v, float):
            out[rot] = v
    return out


def main():
    PASTA.mkdir(parents=True, exist_ok=True)
    if not (PASTA / "Tabela 1.1.1.xls").exists():
        z = PASTA / "pns.zip"
        urllib.request.urlretrieve(ZIP, z)
        zipfile.ZipFile(z).extractall(PASTA)
    # 1.1.1: distribuição (%) por orientação: colunas 1 (total), 4 (homens), 7 (mulheres)
    t = planilha("Tabela 1.1.1.xls")
    por_sexo = {"Homens": linhas(t, 4), "Mulheres": linhas(t, 7)}
    for d in por_sexo.values():
        d.pop("Total", None)
    # 1.2.1 e 1.3.1: % de homossexuais ou bissexuais (coluna 7) por idade, sexo, UF e situação do domicílio
    lgb_carac = linhas(planilha("Tabela 1.2.1.xls"), 7)
    lgb_geo = linhas(planilha("Tabela 1.3.1.xls"), 7)
    dados = {
        "fonte": "IBGE, PNS 2019, Orientação sexual autoidentificada da população adulta (estatística experimental), tabelas 1.1.1, 1.2.1 e 1.3.1",
        "distribuicao_por_sexo": por_sexo,
        "lgb_total": lgb_carac["Total (2)"],
        "lgb_sexo": {"Homens": lgb_carac["Homem"], "Mulheres": lgb_carac["Mulher"]},
        "lgb_idade": {k: lgb_carac[k] for k in ("18 a 29", "30 a 39", "40 a 59", "60 ou mais")},
        "lgb_situacao": {"Urbana": lgb_geo["Urbana"], "Rural": lgb_geo["Rural"]},
        "lgb_uf": {k: v for k, v in lgb_geo.items() if k not in ("Brasil", "Urbana", "Rural", "Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste")},
    }
    (RAIZ / "dados" / "fontes" / "orientacao_sexual.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"orientacao_sexual.json: {len(dados['lgb_uf'])} UFs, LGB total {dados['lgb_total']}%")


if __name__ == "__main__":
    main()
