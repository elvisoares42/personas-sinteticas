"""Gera saida/explorar.html: totais das personas geradas e uma amostra navegável com filtros e ficha.

Os totais são calculados sobre todas as personas; a tabela traz uma amostra (padrão 5 mil) para a página ficar leve.
Uso: python3 scripts/explorar.py [tamanho_da_amostra]
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

SAIDA = Path(__file__).resolve().parent.parent / "saida"
FAIXAS = [(0, 9), (10, 17), (18, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 74), (75, 200)]
ORDEM = {
    "geracao": ["geração Alfa", "geração Z", "geração Y (millennials)", "geração X", "geração baby boomer", "geração silenciosa"],
    "regiao": ["Sudeste", "Nordeste", "Sul", "Norte", "Centro-Oeste"],
    "instrucao": ["Sem instrução e fundamental incompleto", "Fundamental completo e médio incompleto",
                  "Médio completo e superior incompleto", "Superior completo"],
    "renda_per_capita": ["Sem rendimento", "Até 1/4 de salário mínimo", "Mais de 1/4 a 1/2 salário mínimo",
                         "Mais de 1/2 a 1 salário mínimo", "Mais de 1 a 2 salários mínimos", "Mais de 2 a 3 salários mínimos",
                         "Mais de 3 a 5 salários mínimos", "Mais de 5 a 10 salários mínimos", "Mais de 10 a 15 salários mínimos",
                         "Mais de 15 a 20 salários mínimos", "Mais de 20 salários mínimos"],
}
COLUNAS = ["persona_id", "nome", "sobrenome", "idade", "sexo", "cor_raca", "uf", "regiao", "geracao", "situacao_domicilio",
           "instrucao", "renda_per_capita", "deficiencia", "tipos_dificuldade", "internet_em_casa", "usa_internet",
           "internet_so_celular", "testavel", "ficha"]


def faixa(i: int) -> str:
    for a, b in FAIXAS:
        if a <= i <= b:
            return f"{a}+" if b == 200 else f"{a}–{b}"


def main():
    tamanho = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    pessoas = [json.loads(l) for l in open(SAIDA / "personas.jsonl", encoding="utf-8")]
    cont = {k: Counter() for k in ["faixa", "sexo", "cor_raca", "regiao", "geracao", "situacao_domicilio", "instrucao",
                                   "renda_per_capita", "deficiencia", "tipos", "internet_em_casa", "usa_internet", "uf"]}
    for p in pessoas:
        cont["faixa"][faixa(p["idade"])] += 1
        for k in cont:
            if k in p:
                if k == "instrucao" and p["idade"] < 18:
                    continue
                if k == "deficiencia" and p["idade"] < 2:
                    continue
                if k == "usa_internet" and p["idade"] < 10:
                    continue
                cont[k][p[k]] += 1
        for t in filter(None, p["tipos_dificuldade"].split("; ")):
            cont["tipos"][t] += 1
    ordem = dict(ORDEM, faixa=[faixa(a) for a, _ in FAIXAS])
    totais = {k: sorted(c.items(), key=(lambda kv: ordem[k].index(kv[0]) if kv[0] in ordem[k] else 99) if k in ordem
                        else (lambda kv: -kv[1])) for k, c in cont.items()}
    amostra = random.Random("explorar").sample(pessoas, min(tamanho, len(pessoas)))
    amostra.sort(key=lambda p: p["persona_id"])
    dados = {"total": len(pessoas), "testaveis": sum(p["testavel"] == "sim" for p in pessoas), "totais": totais,
             "linhas": [[p[c] for c in COLUNAS] for p in amostra], "colunas": COLUNAS}
    html = MODELO.replace("__DADOS__", json.dumps(dados, ensure_ascii=False).replace("</", "<\\/"))
    (SAIDA / "explorar.html").write_text(html, encoding="utf-8")
    print(f"{SAIDA / 'explorar.html'}: {len(pessoas)} personas, amostra de {len(amostra)}")


MODELO = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Explorar personas</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--txt:#1b1f24;--sub:#5b6470;--linha:#e3e6ea;--barra:#3b6fd8;--fundo-barra:#e8eefb;--destaque:#eef3fd}
@media (prefers-color-scheme:dark){:root{--bg:#121417;--card:#1b1e23;--txt:#e8eaed;--sub:#a0a8b3;--linha:#2c3038;--barra:#7aa2f7;--fundo-barra:#243049;--destaque:#202a3d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1200px;margin:0 auto;padding:24px 16px 48px}h1{font-size:24px;margin:0 0 4px}h2{font-size:16px;margin:0 0 10px}
.sub{color:var(--sub);margin:0 0 20px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px}
.kpi,.card{background:var(--card);border:1px solid var(--linha);border-radius:12px;padding:14px 16px}.kpi b{display:block;font-size:24px}
.kpi span{color:var(--sub);font-size:13px}.grade{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin-bottom:24px}
.barra{display:grid;grid-template-columns:minmax(0,1.3fr) 2fr 52px;gap:8px;align-items:center;font-size:13px;margin:4px 0}
.barra .rot{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.trilho{background:var(--fundo-barra);border-radius:4px;height:12px}
.enche{background:var(--barra);height:12px;border-radius:4px}.pct{text-align:right;color:var(--sub);font-variant-numeric:tabular-nums}
.filtros{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}select,input{font:inherit;padding:8px 10px;border:1px solid var(--linha);border-radius:8px;background:var(--card);color:var(--txt);min-height:40px}
input{flex:1 1 200px}.tabela{overflow-x:auto;background:var(--card);border:1px solid var(--linha);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--linha);white-space:nowrap}
th{position:sticky;top:0;background:var(--card);color:var(--sub);font-weight:600}tbody tr{cursor:pointer}tbody tr:hover,tr.sel{background:var(--destaque)}
#ficha{margin:12px 0;display:none}#ficha p{margin:6px 0 0}.mais{display:flex;gap:8px;align-items:center;justify-content:space-between;margin-top:10px;color:var(--sub);font-size:13px}
button{font:inherit;padding:8px 14px;border-radius:8px;border:1px solid var(--linha);background:var(--card);color:var(--txt);cursor:pointer;min-height:40px}
</style></head><body><main>
<h1>Personas Sintéticas UX</h1>
<p class="sub">Totais calculados sobre todas as personas geradas. A tabela mostra uma amostra aleatória; clique numa linha para ver a ficha.</p>
<div class="kpis" id="kpis"></div>
<div class="grade" id="graficos"></div>
<h2>Amostra de personas</h2>
<div class="filtros" id="filtros"><input id="busca" type="search" placeholder="Buscar por nome, estado, texto da ficha…" aria-label="Buscar"></div>
<div class="card" id="ficha" aria-live="polite"></div>
<div class="tabela"><table><thead id="cab"></thead><tbody id="corpo"></tbody></table></div>
<div class="mais"><span id="cont"></span><button id="btmais">Mostrar mais</button></div>
</main>
<script>
const D=__DADOS__;const fmt=n=>n.toLocaleString('pt-BR');const p1=n=>n.toLocaleString('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:1})+'%';const C=Object.fromEntries(D.colunas.map((c,i)=>[c,i]));
const tot=D.totais, soma=k=>tot[k].reduce((a,[,v])=>a+v,0), pctDe=(k,cat)=>{const x=tot[k].find(([c])=>c===cat);return x?100*x[1]/soma(k):0};
const kpis=[[fmt(D.total),'personas'],[fmt(D.testaveis),'testáveis (18+)'],[p1(pctDe('situacao_domicilio','Urbana')),'em área urbana'],
 [p1(pctDe('deficiencia','sim')),'com deficiência (2+ anos)'],[p1(pctDe('usa_internet','sim')),'usaram internet (10+)']];
document.getElementById('kpis').innerHTML=kpis.map(([v,r])=>`<div class="kpi"><b>${v}</b><span>${r}</span></div>`).join('');
const titulos={faixa:'Faixa de idade',geracao:'Geração',sexo:'Sexo',cor_raca:'Cor ou raça',regiao:'Região',uf:'Estado',situacao_domicilio:'Urbano ou rural',
 instrucao:'Escolaridade (18+)',renda_per_capita:'Renda da casa por pessoa',deficiencia:'Deficiência (2+ anos)',tipos:'Tipos de dificuldade (entre quem tem)',
 internet_em_casa:'Internet em casa',usa_internet:'Usou internet nos últimos 3 meses (10+)'};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
document.getElementById('graficos').innerHTML=Object.keys(titulos).map(k=>{const t=soma(k),max=Math.max(...tot[k].map(([,v])=>v));
 return `<div class="card"><h2>${titulos[k]}</h2>${tot[k].map(([c,v])=>`<div class="barra" title="${esc(c)}: ${fmt(v)}"><span class="rot">${esc(c)}</span><div class="trilho"><div class="enche" style="width:${(100*v/max).toFixed(1)}%"></div></div><span class="pct">${p1(100*v/t)}</span></div>`).join('')}</div>`}).join('');
const filtros=[['uf','Estado'],['geracao','Geração'],['cor_raca','Cor ou raça'],['renda_per_capita','Renda'],['deficiencia','Deficiência'],['testavel','Testável']];
const fdiv=document.getElementById('filtros');
filtros.forEach(([c,r])=>{const vals=[...new Set(D.linhas.map(l=>l[C[c]]))].sort((a,b)=>String(a).localeCompare(String(b),'pt-BR'));
 const s=document.createElement('select');s.dataset.col=c;s.setAttribute('aria-label',r);s.innerHTML=`<option value="">${r}: todos</option>`+vals.map(v=>`<option>${esc(v)}</option>`).join('');fdiv.appendChild(s)});
const vis=['persona_id','nome','sobrenome','idade','sexo','cor_raca','uf','geracao','situacao_domicilio','instrucao','renda_per_capita','deficiencia','usa_internet','testavel'];
const nomesCol={persona_id:'Nº',nome:'Nome',sobrenome:'Sobrenome',idade:'Idade',sexo:'Sexo',cor_raca:'Cor ou raça',uf:'Estado',geracao:'Geração',situacao_domicilio:'Situação',
 instrucao:'Escolaridade',renda_per_capita:'Renda per capita',deficiencia:'Deficiência',usa_internet:'Usa internet',testavel:'Testável'};
document.getElementById('cab').innerHTML='<tr>'+vis.map(c=>`<th>${nomesCol[c]}</th>`).join('')+'</tr>';
let lista=D.linhas,limite=100;
function aplicar(){const q=document.getElementById('busca').value.toLowerCase();const ativos=[...fdiv.querySelectorAll('select')].filter(s=>s.value);
 lista=D.linhas.filter(l=>ativos.every(s=>String(l[C[s.dataset.col]])===s.value)&&(!q||l.join(' ').toLowerCase().includes(q)));limite=100;desenhar()}
function desenhar(){document.getElementById('corpo').innerHTML=lista.slice(0,limite).map((l,i)=>`<tr data-i="${i}">${vis.map(c=>`<td>${esc(l[C[c]])}</td>`).join('')}</tr>`).join('');
 document.getElementById('cont').textContent=`${fmt(Math.min(limite,lista.length))} de ${fmt(lista.length)} na amostra de ${fmt(D.linhas.length)}`;
 document.getElementById('btmais').style.display=limite<lista.length?'':'none'}
document.getElementById('corpo').addEventListener('click',e=>{const tr=e.target.closest('tr');if(!tr)return;const l=lista[+tr.dataset.i];
 document.querySelectorAll('tr.sel').forEach(x=>x.classList.remove('sel'));tr.classList.add('sel');const f=document.getElementById('ficha');f.style.display='block';
 f.innerHTML=`<h2>Persona ${esc(l[C.persona_id])}: ${esc(l[C.nome])} ${esc(l[C.sobrenome])}</h2><p>${esc(l[C.ficha])}</p>`;f.scrollIntoView({block:'nearest',behavior:'smooth'})});
document.getElementById('busca').addEventListener('input',aplicar);fdiv.addEventListener('change',aplicar);
document.getElementById('btmais').addEventListener('click',()=>{limite+=200;desenhar()});desenhar();
</script></body></html>"""

if __name__ == "__main__":
    main()
