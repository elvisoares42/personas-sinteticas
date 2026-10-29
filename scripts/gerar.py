"""Gera personas sintéticas que retratam a população brasileira (Censo 2022 + PNAD TIC 2025).

Cada persona N é sorteada com um gerador próprio, semeado por (SEED, N): a persona 123 é sempre a mesma,
gere-se 1 mil ou 100 mil. Só dados públicos (ver DECISOES.md); campos marcados em CAMPOS.
Uso: python3 scripts/gerar.py [quantidade]   (padrão: 100000)
"""
import bisect
import csv
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "dados" / "fontes"
SAIDA = RAIZ / "saida"
SEED = "personas-abertas-ux-v0"
ANO_CENSO = 2022  # data de referência do Censo: 31/07/2022

# Cada campo: (status, origem). ✅ dado público; ⚠️ suposição de trabalho.
CAMPOS = {
    "persona_id": ("—", "número sequencial"),
    "nome": ("✅", "IBGE Nomes: ranking do estado, década de nascimento e sexo (Censo 2010); peso pela raiz da frequência e, fora de 1930–2010, a década mais próxima ⚠️"),
    "sobrenome": ("⚠️", "lista de sobrenomes comuns no Brasil (não há tabela pública do IBGE de sobrenomes)"),
    "uf": ("✅", "Censo 2022, tabela 9606 (sorteio conjunto UF × cor ou raça × sexo × idade)"),
    "regiao": ("✅", "região do IBGE da UF"),
    "cor_raca": ("✅", "Censo 2022, tabela 9606 (autodeclaração nas 5 categorias do IBGE)"),
    "negra": ("✅", "preta ou parda, critério do IBGE e do Estatuto da Igualdade Racial"),
    "quilombola": ("✅", "Censo 2022, tabela 10089: pessoas quilombolas por UF, sexo e grupo de idade (independente da cor ou raça ⚠️)"),
    "sexo": ("✅", "Censo 2022, tabela 9606"),
    "idade": ("✅", "Censo 2022, tabela 9606 (idade em 31/07/2022, anos completos)"),
    "ano_nascimento": ("✅", "calculado pela idade e pela data de referência do Censo"),
    "geracao": ("✅", "pelo ano de nascimento: silenciosa até 1945, boomer 1946–64, X 1965–80, Y 1981–96, Z 1997–2012, Alfa 2013+"),
    "situacao_domicilio": ("✅", "Censo 2022, tabela 10089: urbana ou rural por UF, sexo e grupo de idade"),
    "instrucao": ("✅", "Censo 2022, tabela 10061: 18+ por UF, grupo de idade, sexo e cor ou raça"),
    "renda_per_capita": ("✅", "Censo 2022, tabela 10296: classe de rendimento domiciliar per capita por UF, sexo e cor ou raça (sem ligação com idade e escolaridade na v0 ⚠️)"),
    "deficiencia": ("✅", "Censo 2022, tabela 10125: pessoas de 2 anos ou mais com deficiência por UF, sexo e grupo de idade"),
    "tipos_dificuldade": ("⚠️", "Censo 2022, tabela 10127 (frequência de cada tipo por UF); a combinação de tipos é sorteada de forma independente"),
    "internet_em_casa": ("✅", "Censo 2022, tabela 9942: conexão domiciliar por UF, cor ou raça e grupo de idade"),
    "usa_internet": ("✅", "PNAD Contínua TIC 2025, tabela 7334: uso nos últimos 3 meses por UF e grupo de idade (10+); independente da conexão em casa ⚠️"),
    "internet_so_celular": ("✅", "PNAD Contínua TIC 2025, tabela 7337: entre quem usa, só pelo celular (média Brasil)"),
    "orientacao_sexual": ("✅", "IBGE, PNS 2019 (estatística experimental, 18+): distribuição por sexo; chance de ser homossexual ou bissexual por idade, ajustada por UF, sexo e urbano/rural ⚠️ (ajustes multiplicativos)"),
    "identidade_genero": ("⚠️", "não há dado oficial; Spizzirri et al., Scientific Reports, 2021 (amostra nacional de 6 mil adultos): 0,69% pessoas trans e 1,19% não binárias, sem diferença entre regiões; 18+"),
    "testavel": ("—", "idade 18+; menores entram só para o retrato estatístico"),
}

# preposição com artigo para cada UF ("na Bahia", "no Pará", "em São Paulo")
NO_UF = {"Acre": "no", "Amapá": "no", "Amazonas": "no", "Ceará": "no", "Espírito Santo": "no", "Maranhão": "no",
         "Mato Grosso": "no", "Mato Grosso do Sul": "no", "Pará": "no", "Paraná": "no", "Piauí": "no",
         "Rio de Janeiro": "no", "Rio Grande do Norte": "no", "Rio Grande do Sul": "no", "Tocantins": "no",
         "Distrito Federal": "no", "Bahia": "na", "Paraíba": "na", "Alagoas": "em", "Goiás": "em", "Minas Gerais": "em",
         "Pernambuco": "em", "Rondônia": "em", "Roraima": "em", "Santa Catarina": "em", "São Paulo": "em", "Sergipe": "em"}
REGIAO = {"Norte": ["Rondônia", "Acre", "Amazonas", "Roraima", "Pará", "Amapá", "Tocantins"],
          "Nordeste": ["Maranhão", "Piauí", "Ceará", "Rio Grande do Norte", "Paraíba", "Pernambuco", "Alagoas", "Sergipe", "Bahia"],
          "Sudeste": ["Minas Gerais", "Espírito Santo", "Rio de Janeiro", "São Paulo"],
          "Sul": ["Paraná", "Santa Catarina", "Rio Grande do Sul"],
          "Centro-Oeste": ["Mato Grosso do Sul", "Mato Grosso", "Goiás", "Distrito Federal"]}
UF_REGIAO = {uf: r for r, ufs in REGIAO.items() for uf in ufs}
# ⚠️ Sobrenomes frequentes no Brasil (não há fonte oficial com frequência); sorteio uniforme.
SOBRENOMES = ["Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves", "Pereira", "Lima", "Gomes", "Costa",
              "Ribeiro", "Martins", "Carvalho", "Almeida", "Lopes", "Soares", "Fernandes", "Vieira", "Barbosa", "Rocha", "Dias",
              "Nascimento", "Andrade", "Moreira", "Nunes", "Marques", "Machado", "Mendes", "Freitas", "Cardoso", "Ramos",
              "Gonçalves", "Santana", "Teixeira", "Araújo", "Batista", "Correia", "Pinto", "Monteiro", "Moura", "Cavalcanti"]
GERACOES = [(2013, "geração Alfa"), (1997, "geração Z"), (1981, "geração Y (millennials)"), (1965, "geração X"),
            (1946, "geração baby boomer"), (0, "geração silenciosa")]
ACENTOS = {"JOSE": "José", "JOAO": "João", "ANTONIO": "Antônio", "SEBASTIAO": "Sebastião", "CONCEICAO": "Conceição",
           "LUCIA": "Lúcia", "MARCIA": "Márcia", "PATRICIA": "Patrícia", "FABIO": "Fábio", "MARCIO": "Márcio",
           "SERGIO": "Sérgio", "CLAUDIO": "Cláudio", "CLAUDIA": "Cláudia", "FLAVIA": "Flávia", "VITORIA": "Vitória",
           "JULIA": "Júlia", "LUCAS": "Lucas", "VINICIUS": "Vinícius", "CAUA": "Cauã", "VITOR": "Vitor", "ANDRE": "André",
           "MONICA": "Mônica", "VANIA": "Vânia", "SONIA": "Sônia", "SILVIA": "Sílvia", "TANIA": "Tânia", "MARIO": "Mário",
           "ROGERIO": "Rogério", "MAURICIO": "Maurício", "CICERO": "Cícero", "BENEDITO": "Benedito", "IRACEMA": "Iracema",
           "LUIS": "Luís", "JESSICA": "Jéssica", "BARBARA": "Bárbara", "LETICIA": "Letícia", "LAIS": "Laís", "LIVIA": "Lívia",
           "HELOISA": "Heloísa", "EMILIA": "Emília", "CECILIA": "Cecília", "OTAVIO": "Otávio", "INACIO": "Inácio",
           "GABRIELA": "Gabriela", "RAIMUNDA": "Raimunda", "SIMONE": "Simone", "ANDREIA": "Andreia", "LAURA": "Laura"}


def faixa(nome: str):
    if nome in ("Menos de 1 ano",):
        return 0, 0
    if m := re.fullmatch(r"(\d+) anos?", nome):
        return int(m[1]), int(m[1])
    if m := re.fullmatch(r"(\d+) (?:a|ou) (\d+) anos", nome):
        return int(m[1]), int(m[2])
    if m := re.fullmatch(r"(\d+) anos ou mais", nome):
        return int(m[1]), 200
    raise ValueError(nome)


def carregar(nome: str):
    return json.loads((FONTES / f"{nome}.json").read_text(encoding="utf-8"))["linhas"]


class Distribuicao:
    """Pesos por categoria com sorteio por CDF (bisect)."""

    def __init__(self, pesos: dict):
        self.itens = [k for k, v in pesos.items() if v > 0]
        acum, self.cdf = 0.0, []
        for k in self.itens:
            acum += pesos[k]
            self.cdf.append(acum)
        self.total = acum

    def sortear(self, rng):
        return self.itens[bisect.bisect_right(self.cdf, rng.random() * self.total)]


class Condicional:
    """P(categoria | chave), com recuo para chaves menos específicas quando a célula é vazia (UF pequena, grupo raro)."""

    def __init__(self):
        self.tab = defaultdict(lambda: defaultdict(float))
        self.cache = {}

    def somar(self, chave: tuple, cat, valor):
        if valor:
            for i in range(len(chave) + 1):  # registra também as chaves com o início trocado por '*' (recuo)
                self.tab[("*",) * i + chave[i:]][cat] += valor

    def dist(self, chave: tuple) -> dict:
        for i in range(len(chave) + 1):
            d = self.tab.get(("*",) * i + chave[i:])
            if d and sum(d.values()) > 0:
                return d
        raise KeyError(chave)

    def sortear(self, chave: tuple, rng):
        if chave not in self.cache:
            self.cache[chave] = Distribuicao(self.dist(chave))
        return self.cache[chave].sortear(rng)


def grupo_de(grupos: list, idade: int):
    for nome, (a, b) in grupos:
        if a <= idade <= b:
            return nome
    return None


class Modelo:
    def __init__(self):
        pop = carregar("pop_uf_raca_sexo_idade")
        self.base = Distribuicao({(l["Unidade da Federação"], l["Cor ou raça"], l["Sexo"], faixa(l["Idade"])[0]): l["valor"] or 0
                                  for l in pop})

        def montar(nome, chave, cat, filtro=lambda l: True):
            c, grupos = Condicional(), {}
            for l in carregar(nome):
                if filtro(l):
                    if "Grupo de idade" in l:
                        grupos[l["Grupo de idade"]] = faixa(l["Grupo de idade"])
                    c.somar(chave(l), l[cat], l["valor"])
            return c, sorted(grupos.items(), key=lambda g: g[1][0])

        uf = "Unidade da Federação"
        self.situacao, self.g_sit = montar("situacao_domicilio", lambda l: (l[uf], l["Sexo"], l["Grupo de idade"]), "Situação do domicílio")
        self.instr, self.g_instr = montar("instrucao_18mais", lambda l: (l[uf], l["Grupo de idade"], l["Sexo"], l["Cor ou raça"]), "Nível de instrução")
        self.renda, _ = montar("renda_per_capita", lambda l: (l[uf], l["Sexo"], l["Cor ou raça"]), "Classes de rendimento nominal mensal domiciliar per capita")
        self.net_casa, self.g_net = montar("internet_domicilio", lambda l: (l[uf], l["Cor ou raça"], l["Grupo de idade"]), "Existência de conexão domiciliar à Internet")

        # Deficiência: proporção de PcD por UF, sexo e grupo de idade (2+)
        self.pcd, grupos = {}, {}
        tot = defaultdict(lambda: [0.0, 0.0])
        for l in carregar("deficiencia_sexo_idade"):
            grupos[l["Grupo de idade"]] = faixa(l["Grupo de idade"])
            i = 1 if "com deficiência" in l["Variável"] else 0
            tot[(l[uf], l["Sexo"], l["Grupo de idade"])][i] += l["valor"] or 0
        self.pcd = {k: (v[1] / v[0] if v[0] else 0.0) for k, v in tot.items()}
        self.g_pcd = sorted(grupos.items(), key=lambda g: g[1][0])
        tipos = defaultdict(dict)
        for l in carregar("deficiencia_tipos"):
            tipos[l[uf]][l["Tipos de dificuldades funcionais"]] = l["valor"] or 0
        self.tipos = {u: {t.replace("Dificuldade permanente para ", "").split(",")[0]: v / d["Total"] for t, v in d.items() if t != "Total"}
                      for u, d in tipos.items()}

        # Uso de internet (PNAD TIC 2025, %) por UF e grupo de idade, 10+
        self.uso, grupos = {}, {}
        for l in carregar("uso_internet_idade"):
            grupos[l["Grupo de idade"]] = faixa(l["Grupo de idade"])
            self.uso[(l[uf], l["Grupo de idade"])] = (l["valor"] or 0) / 100
        self.g_uso = sorted(grupos.items(), key=lambda g: g[1][0])
        equip = {l["Equipamento utilizado para acessar a Internet"]: l["valor"] for l in carregar("equipamento_internet")}
        self.so_celular = (equip["Utilizaram somente telefone móvel celular"] or 0) / 100

        # Quilombolas: proporção por UF, sexo e grupo de idade (total de população da mesma tabela)
        pop_g = defaultdict(float)
        for l in carregar("situacao_domicilio"):
            pop_g[(l[uf], l["Sexo"], l["Grupo de idade"])] += l["valor"] or 0
        quil = defaultdict(float)
        for l in carregar("quilombolas"):
            quil[(l[uf], l["Sexo"], l["Grupo de idade"])] += l["valor"] or 0
        self.quilombola = {k: quil[k] / v for k, v in pop_g.items() if v}

        # Orientação sexual (PNS 2019, 18+)
        o = json.loads((FONTES / "orientacao_sexual.json").read_text(encoding="utf-8"))
        tot = o["lgb_total"]
        self.lgb_idade = [((18, 29), o["lgb_idade"]["18 a 29"]), ((30, 39), o["lgb_idade"]["30 a 39"]),
                          ((40, 59), o["lgb_idade"]["40 a 59"]), ((60, 200), o["lgb_idade"]["60 ou mais"])]
        self.lgb_fator = {"sexo": {k: v / tot for k, v in o["lgb_sexo"].items()},
                          "uf": {k: v / tot for k, v in o["lgb_uf"].items()},
                          "sit": {k: v / tot for k, v in o["lgb_situacao"].items()}}
        self.orient_lgb, self.orient_outras = {}, {}
        for sx, d in o["distribuicao_por_sexo"].items():
            self.orient_lgb[sx] = Distribuicao({k: d[k] for k in ("Homossexual", "Bissexual")})
            self.orient_outras[sx] = Distribuicao({k: v for k, v in d.items() if k not in ("Homossexual", "Bissexual")})
        # calibra os ajustes multiplicativos para o total voltar ao % nacional da PNS
        esp = soma = 0.0
        for (u, _, sx, idade), w in zip(self.base.itens, [self.base.cdf[0]] + [b - a for a, b in zip(self.base.cdf, self.base.cdf[1:])]):
            if idade >= 18:
                urb = self.situacao.dist((u, sx, grupo_de(self.g_sit, idade)))
                f_sit = sum(v * self.lgb_fator["sit"][k] for k, v in urb.items()) / sum(urb.values())
                esp += w * self._lgb_bruto(u, sx, idade) * f_sit
                soma += w
        self.lgb_calibra = (tot / 100) / (esp / soma)

        self.nomes = {}
        for chave, lista in carregar("nomes_uf_decada_sexo").items():
            if lista:
                # ⚠️ raiz quadrada da frequência: o ranking só traz o top 20, e o peso bruto inflaria os primeiros (ex.: Maria)
                self.nomes[tuple(chave.split("|"))] = Distribuicao({n: f ** 0.5 for n, f in lista})

    def _lgb_bruto(self, uf, sexo, idade):
        base = next(v for (a, b), v in self.lgb_idade if a <= idade <= b) / 100
        return base * self.lgb_fator["sexo"][sexo] * self.lgb_fator["uf"].get(uf, 1.0)

    def orientacao(self, rng, uf, sexo, idade, situacao):
        p = self._lgb_bruto(uf, sexo, idade) * self.lgb_fator["sit"][situacao] * self.lgb_calibra
        return (self.orient_lgb if rng.random() < p else self.orient_outras)[sexo].sortear(rng)

    def nome(self, rng, uf, ano, sexo):
        decada = str(min(2010, max(1930, ano // 10 * 10)))
        s = "F" if sexo == "Mulheres" else "M"
        d = self.nomes.get((uf, decada, s))
        bruto = d.sortear(rng) if d else "MARIA" if s == "F" else "JOSÉ"
        return ACENTOS.get(bruto, bruto.capitalize())


def rng_da_persona(n: int) -> random.Random:
    return random.Random(int.from_bytes(hashlib.sha256(f"{SEED}|{n}".encode()).digest()[:8], "big"))


def gerar_persona(m: Modelo, n: int) -> dict:
    rng = rng_da_persona(n)
    uf, raca, sexo, idade = m.base.sortear(rng)
    # nascido entre 01/08 e 31/12 ainda não tinha feito aniversário em 31/07/2022: 5 em 12 meses
    ano = ANO_CENSO - idade - (1 if rng.random() < 5 / 12 else 0)
    p = {"persona_id": f"{n:06d}", "nome": m.nome(rng, uf, ano, sexo), "sobrenome": rng.choice(SOBRENOMES),
         "uf": uf, "regiao": UF_REGIAO[uf], "cor_raca": raca, "sexo": "Mulher" if sexo == "Mulheres" else "Homem",
         "idade": idade, "ano_nascimento": ano, "geracao": next(g for inicio, g in GERACOES if ano >= inicio)}
    p["situacao_domicilio"] = m.situacao.sortear((uf, sexo, grupo_de(m.g_sit, idade)), rng)
    p["instrucao"] = (m.instr.sortear((uf, grupo_de(m.g_instr, idade), sexo, raca), rng)
                      if idade >= 18 else "menor de 18 anos")
    p["renda_per_capita"] = m.renda.sortear((uf, sexo, raca), rng)
    g = grupo_de(m.g_pcd, idade)
    pcd = idade >= 2 and rng.random() < m.pcd.get((uf, sexo, g), 0)
    p["deficiencia"] = "sim" if pcd else ("não" if idade >= 2 else "não se aplica (menos de 2 anos)")
    tipos = []
    if pcd:
        while not tipos:  # cada pessoa com deficiência tem ao menos um tipo
            tipos = [t for t, pr in m.tipos[uf].items() if rng.random() < pr]
    p["tipos_dificuldade"] = "; ".join(tipos)
    p["internet_em_casa"] = m.net_casa.sortear((uf, raca, grupo_de(m.g_net, idade)), rng).lower()
    if idade >= 10:
        usa = rng.random() < m.uso.get((uf, grupo_de(m.g_uso, idade)), 0)
        p["usa_internet"] = "sim" if usa else "não"
        p["internet_so_celular"] = ("sim" if rng.random() < m.so_celular else "não") if usa else ""
    else:
        p["usa_internet"], p["internet_so_celular"] = "não se aplica (menos de 10 anos)", ""
    p["negra"] = "sim" if raca in ("Preta", "Parda") else "não"
    p["quilombola"] = "sim" if rng.random() < m.quilombola.get((uf, sexo, grupo_de(m.g_sit, idade)), 0) else "não"
    if idade >= 18:
        p["orientacao_sexual"] = m.orientacao(rng, uf, sexo, idade, p["situacao_domicilio"])
        r = rng.random()
        p["identidade_genero"] = ("pessoa não binária" if r < 0.0119 else
                                  ("mulher trans" if sexo == "Mulheres" else "homem trans") if r < 0.0119 + 0.0069 else "cisgênero")
    else:
        p["orientacao_sexual"] = p["identidade_genero"] = "não se aplica (menor de 18)"
    p["testavel"] = "sim" if idade >= 18 else "não"
    p["ficha"] = ficha(p)
    return p


ORIENT = {"Heterossexual": "Sua orientação sexual: heterossexual. ", "Homossexual": "Sua orientação sexual: homossexual. ",
          "Bissexual": "Sua orientação sexual: bissexual. ", "Outra orientação sexual": "Você se identifica com outra orientação sexual. ",
          "Não sabe": "Você não sabe ou não define sua orientação sexual. ",
          "Recusou-se a responder": "Você prefere não falar sobre sua orientação sexual. "}
RENDA = {"Sem rendimento": "sem rendimento", "Até 1/4 de salário mínimo": "de até 1/4 de salário mínimo"}
DIFIC = {"enxergar": "enxergar", "ouvir": "ouvir", "andar ou subir degraus": "andar ou subir degraus",
         "pegar pequenos objetos": "pegar pequenos objetos ou abrir tampas",
         "se comunicar": "se comunicar, cuidar de si, trabalhar ou estudar por uma limitação nas funções mentais"}


def ficha(p: dict) -> str:
    """Texto em PT-BR que descreve a persona. Só padrões agregados; nada de empresa ou marca."""
    m = p["sexo"] == "Mulher"
    nb = p["identidade_genero"] == "pessoa não binária"
    o = "" if nb else ("a " if m else "o ")
    onde = "na zona rural" if p["situacao_domicilio"] == "Rural" else "em área urbana"
    idade = "menos de 1 ano" if p["idade"] == 0 else f"{p['idade']} ano{'s' if p['idade'] != 1 else ''}"
    t = (f"Você é {o}{p['nome']} {p['sobrenome']}, nasceu em {p['ano_nascimento']} e é da {p['geracao']}; "
         f"no Censo de 2022 tinha {idade}. Mora {onde} {NO_UF[p['uf']]} {p['uf']} ({p['regiao']}). "
         f"Cor ou raça: {p['cor_raca'].lower()}" + (" (pessoa negra)" if p["negra"] == "sim" else "") + ". ")
    if p["quilombola"] == "sim":
        t += "Você é quilombola. "
    if p["identidade_genero"] in ("mulher trans", "homem trans"):
        t += f"Você é {'uma' if p['identidade_genero'] == 'mulher trans' else 'um'} {p['identidade_genero']}. "
    elif nb:
        t += "Você é uma pessoa não binária. "
    t += ORIENT.get(p["orientacao_sexual"], "")
    if p["idade"] >= 18:
        t += f"Escolaridade: {p['instrucao'].lower()}. "
    renda = RENDA.get(p["renda_per_capita"], p["renda_per_capita"].lower().replace("mais de ", "de mais de "))
    t += f"A renda da sua casa por pessoa é {renda}. " if renda != "sem rendimento" else "A sua casa não tem rendimento. "
    if p["deficiencia"] == "sim":
        t += "Você tem dificuldade permanente para " + " e para ".join(DIFIC.get(x, x) for x in p["tipos_dificuldade"].split("; ")) + ". "
    t += "Sua casa tem internet. " if p["internet_em_casa"] == "sim" else "Sua casa não tem conexão de internet. "
    if p["usa_internet"] == "sim":
        t += ("Mesmo assim, você" if p["internet_em_casa"] != "sim" else "Você") + " usa a internet" + \
             (" só pelo celular. " if p["internet_so_celular"] == "sim" else ". ")
    elif p["usa_internet"] == "não":
        t += "Você não usou a internet nos últimos três meses. "
    if p["testavel"] == "não":
        t += "Persona menor de idade: só para retrato estatístico, não usar em testes."
    return t.strip()


def main():
    qtd = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    m = Modelo()
    SAIDA.mkdir(exist_ok=True)
    campos = list(CAMPOS) + ["ficha"]
    with open(SAIDA / "personas.csv", "w", newline="", encoding="utf-8") as fc, \
            open(SAIDA / "personas.jsonl", "w", encoding="utf-8") as fj:
        w = csv.DictWriter(fc, fieldnames=campos)
        w.writeheader()
        for n in range(1, qtd + 1):
            p = gerar_persona(m, n)
            w.writerow(p)
            fj.write(json.dumps(p, ensure_ascii=False) + "\n")
    (SAIDA / "campos.json").write_text(json.dumps({k: {"status": s, "origem": o} for k, (s, o) in CAMPOS.items()},
                                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{qtd} personas em {SAIDA}")


if __name__ == "__main__":
    main()
