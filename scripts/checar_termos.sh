#!/bin/zsh
# Barra a publicação se o repositório citar termos proibidos (empresas e fontes internas de outros projetos).
# A lista fica em .termos-proibidos (uma expressão por linha), fora do git, para o próprio repositório não citá-los.
# Procura nos arquivos (fora de saida/ e dados/fontes/) e em todo o histórico do git.
cd "$(dirname "$0")/.." || exit 1
[[ -s .termos-proibidos ]] || { echo "❌ Falta o arquivo .termos-proibidos"; exit 1; }
TERMOS=$(grep -v '^\s*$' .termos-proibidos | paste -sd '|' -)
ACHOU=$(grep -rIn -i -E "$TERMOS" . --exclude-dir=.git --exclude-dir=saida --exclude-dir=fontes --exclude=.termos-proibidos)
HIST=$(git log -p --all 2>/dev/null | grep -E '^\+[^+]' | grep -i -E "$TERMOS")
if [[ -n "$ACHOU$HIST" ]]; then
  echo "❌ Termos proibidos encontrados:"; [[ -n "$ACHOU" ]] && echo "$ACHOU"; [[ -n "$HIST" ]] && echo "$HIST"; exit 1
fi
echo "✅ Nenhum termo proibido nos arquivos nem no histórico."
