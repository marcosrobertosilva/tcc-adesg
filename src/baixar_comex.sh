#!/usr/bin/env bash
#
# Baixa os microdados de Comércio Exterior (MDIC/SECEX - Comex Stat) via curl.
# O servidor balanca.mdic.gov.br usa um certificado da ICP-Brasil (AC SERPRO) sem
# enviar a cadeia intermediária, por isso a verificação TLS é desativada aqui
# (-k/--insecure). Isso é inseguro (remove a proteção contra man-in-the-middle);
# use apenas se você confia na rede/DNS de onde está baixando.
#
# Uso: ./baixar_comex.sh [ANO] [DIRETORIO_DESTINO]
#   ANO              Ano dos dados (padrão: 2023)
#   DIRETORIO_DESTINO Pasta onde salvar os CSVs (padrão: ./dados_comex)

set -euo pipefail

ANO="${1:-2023}"
DESTINO="${2:-./dados_comex}"
BASE_URL="https://balanca.mdic.gov.br/balanca/bd/comexstat-bd/ncm"
MAX_TENTATIVAS=10

mkdir -p "$DESTINO"

baixar_com_retomada() {
    local fluxo="$1"
    local url="$2"
    local destino="$3"
    local tmp="${destino}.part"
    local tentativa=1

    echo "-> Baixando ${fluxo} (${url})..."
    while [ "$tentativa" -le "$MAX_TENTATIVAS" ]; do
        # -k: ignora verificação TLS | --retry: nova tentativa em falhas de rede
        # Baixa sempre para um arquivo .part novo (sem -C -): o servidor não garante
        # byte-range consistente entre tentativas, e retomar com -C - já corrompeu
        # arquivos no passado (linhas intercaladas de tentativas diferentes).
        rm -f "$tmp"
        if curl -k -L --fail --retry 5 --retry-delay 3 --connect-timeout 30 \
                -o "$tmp" "$url"; then
            mv -f "$tmp" "$destino"
            echo "   ✓ ${fluxo} salvo em ${destino}"
            return 0
        fi
        echo "   ⚠ Tentativa ${tentativa}/${MAX_TENTATIVAS} falhou para ${fluxo}. Tentando novamente do zero..."
        tentativa=$((tentativa + 1))
    done

    rm -f "$tmp"
    echo "   ✗ Falha ao baixar ${fluxo} após ${MAX_TENTATIVAS} tentativas."
    return 1
}

baixar_com_retomada "Exportacao" "${BASE_URL}/EXP_${ANO}.csv" "${DESTINO}/EXP_${ANO}.csv"
baixar_com_retomada "Importacao" "${BASE_URL}/IMP_${ANO}.csv" "${DESTINO}/IMP_${ANO}.csv"
