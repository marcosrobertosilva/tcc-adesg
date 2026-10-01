import io
import requests
import pandas as pd
import numpy as np

# ==============================================================================
# 1. FUNÇÕES DE DOWNLOAD AUTOMÁTICO DE DADOS OFICIAIS (APIs e OPEN DATA)
# ==============================================================================

def baixar_pam_ibge(ano: int = 2023) -> pd.DataFrame:
    """
    Baixa dados da Produção Agrícola Municipal (PAM - Tabela 5457) do IBGE
    via API REST SIDRA para o Estado de São Paulo (UF 35).
    """
    print(f"[1/4] Baixando PAM/IBGE ({ano}) para São Paulo...")
    # Tabela 5457 | Variável 214 (Quantidade produzida em Toneladas) | UF 35 (SP) | Todos os produtos (classificação 782)
    # Obs: a Tabela 6588 é a LSPA (estimativa mensal) e exige períodos no formato AAAAMM, não AAAA;
    # por isso a Tabela 5457 (PAM definitiva, periodicidade anual) é usada aqui.
    url = f"https://servicodados.ibge.gov.br/api/v3/agregados/5457/periodos/{ano}/variaveis/214?localidades=N3[35]&classificacao=782[all]"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        resultados = []
        for item in data[0]["resultados"]:
            for id_prod, nome_prod in item["classificacoes"][0]["categoria"].items():
                if id_prod == "0":  # categoria "Total" agregada, não é um produto individual
                    continue
                valor_str = list(item["series"][0]["serie"].values())[0]
                valor = float(valor_str) if valor_str not in ["-", "...", "X"] else 0.0
                resultados.append({"produto_origem": nome_prod, "producao_bruta_t": valor})
                
        df_pam = pd.DataFrame(resultados)
        print(f"   ✓ PAM carregada com sucesso ({len(df_pam)} produtos).")
        return df_pam
    except Exception as e:
        print(f"   ⚠ Falha no acesso à API PAM. Aplicando estrutura de apoio. Erro: {e}")
        # Fallback de segurança com dados base para viabilizar a execução
        return pd.DataFrame([
            {"produto_origem": "Arroz (em casca)", "producao_bruta_t": 80000},
            {"produto_origem": "Feijão (em grão)", "producao_bruta_t": 150000},
            {"produto_origem": "Soja (em grão)", "producao_bruta_t": 4200000},
            {"produto_origem": "Laranja", "producao_bruta_t": 13000000}
        ])


def baixar_abate_ibge(ano: int = 2023) -> pd.DataFrame:
    """
    Baixa dados da Pesquisa Trimestral do Abate de Animais (Tabelas 1092 e 1094) do
    IBGE para o Estado de São Paulo (UF 35), consolidando o peso total das carcaças.
    Cada espécie é publicada em uma tabela própria (1092 = bovinos, 1094 = frangos);
    a Tabela 6829 unifica as espécies, mas só está disponível em nível nacional (N1).
    """
    print(f"[2/4] Baixando Pesquisa de Abate/IBGE ({ano}) para São Paulo...")
    # Trimestres do ano selecionado (YYYY01 a YYYY04) | Variável 285 (Peso total das carcaças - kg)
    periodos = f"{ano}01,{ano}02,{ano}03,{ano}04"
    # Classificação 12716[115236] = "Total do trimestre" | 12529[118225] = "Tipo de inspeção: Total"
    tabelas = [
        {
            "produto_origem": "Carne Bovina (carcaça)",
            "url": (
                f"https://servicodados.ibge.gov.br/api/v3/agregados/1092/periodos/{periodos}"
                f"/variaveis/285?localidades=N3[35]&classificacao=18[992]|12529[118225]|12716[115236]"
            ),
        },
        {
            "produto_origem": "Carne de Frango (carcaça)",
            "url": (
                f"https://servicodados.ibge.gov.br/api/v3/agregados/1094/periodos/{periodos}"
                f"/variaveis/285?localidades=N3[35]&classificacao=12529[118225]|12716[115236]"
            ),
        },
    ]

    try:
        resultados = []
        for tabela in tabelas:
            response = requests.get(tabela["url"], timeout=30)
            response.raise_for_status()
            data = response.json()

            serie = data[0]["resultados"][0]["series"][0]["serie"]
            # Soma dos 4 trimestres e conversão de kg para Toneladas
            soma_kg = sum(float(v) for v in serie.values() if v not in ["-", "...", "X", None])
            resultados.append({
                "produto_origem": tabela["produto_origem"],
                "producao_bruta_t": soma_kg / 1000.0
            })

        df_abate = pd.DataFrame(resultados)
        print(f"   ✓ Pesquisa de Abate carregada ({len(df_abate)} categorias de proteína).")
        return df_abate
    except Exception as e:
        print(f"   ⚠ Falha na API de Abate. Aplicando estrutura de apoio. Erro: {e}")
        return pd.DataFrame([
            {"produto_origem": "Carne Bovina (carcaça)", "producao_bruta_t": 580000},
            {"produto_origem": "Carne de Frango (carcaça)", "producao_bruta_t": 1350000}
        ])


def baixar_comex_stat(ano: int = 2023) -> pd.DataFrame:
    """
    Baixa e filtra diretamente os microdados abertos de Comércio Exterior (MDIC/SECEX)
    para o Estado de São Paulo (SG_UF_NCM == 'SP').
    """
    print(f"[3/4] Baixando microdados de Comércio Exterior (Comex Stat - {ano})...")
    comex_dfs = []
    
    # URLs oficiais dos arquivos CSV abertos do MDIC
    urls = {
        "Exportacao": f"https://balanca.mdic.gov.br/balanca/bd/comexstat-bd/ncm/EXP_{ano}.csv",
        "Importacao": f"https://balanca.mdic.gov.br/balanca/bd/comexstat-bd/ncm/IMP_{ano}.csv"
    }
    
    for fluxo, url in urls.items():
        try:
            print(f"   -> Baixando arquivo CSV de {fluxo}...")
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # Leitura otimizada carregando apenas colunas necessárias
            df = pd.read_csv(
                io.BytesIO(response.content),
                sep=";",
                usecols=["CO_NCM", "SG_UF_NCM", "KG_LIQUIDO"],
                dtype={"CO_NCM": str, "SG_UF_NCM": str, "KG_LIQUIDO": float}
            )
            
            # Filtragem exclusiva para o Estado de São Paulo
            df_sp = df[df["SG_UF_NCM"] == "SP"].copy()
            df_sp["CO_NCM"] = df_sp["CO_NCM"].str.zfill(8)
            df_sp["ncm_posicao"] = df_sp["CO_NCM"].str[:4]  # Posição NCM (4 dígitos)
            df_sp["flow"] = fluxo
            
            comex_dfs.append(df_sp)
            print(f"      ✓ {fluxo} para SP filtrada ({len(df_sp):,} registros).")
            
        except Exception as e:
            print(f"      ⚠ Download direto de {fluxo} falhou. Aplicando mock calibrado. Erro: {e}")
            # Mock de contingência em caso de alteração no servidor do MDIC
            mock_data = pd.DataFrame([
                {"ncm_posicao": "1006", "SG_UF_NCM": "SP", "KG_LIQUIDO": 120000000 if fluxo=="Importacao" else 5000000, "flow": fluxo},
                {"ncm_posicao": "0713", "SG_UF_NCM": "SP", "KG_LIQUIDO": 30000000 if fluxo=="Importacao" else 2000000, "flow": fluxo},
                {"ncm_posicao": "1507", "SG_UF_NCM": "SP", "KG_LIQUIDO": 15000000 if fluxo=="Importacao" else 250000000, "flow": fluxo},
                {"ncm_posicao": "0201", "SG_UF_NCM": "SP", "KG_LIQUIDO": 25000000 if fluxo=="Importacao" else 210000000, "flow": fluxo},
                {"ncm_posicao": "0207", "SG_UF_NCM": "SP", "KG_LIQUIDO": 3000000 if fluxo=="Importacao" else 320000000, "flow": fluxo}
            ])
            comex_dfs.append(mock_data)

    df_comex_consolidado = pd.concat(comex_dfs, ignore_index=True)
    return df_comex_consolidado


def obter_populacao_sp(ano: int = 2023) -> int:
    """
    Obtém a população residente estimada do Estado de São Paulo via API SIDRA/IBGE
    (Tabela 6579, variável 9324). A antiga API "v1/projecoes/populacao" foi
    descontinuada; além disso, a Tabela 6579 não possui dados publicados para
    alguns anos intercensitários (ex.: 2022-2023), então tentamos os anos
    vizinhos mais próximos antes de recorrer ao valor de apoio.
    """
    print("[4/4] Obtendo projeção populacional de SP via API IBGE...")
    for p in (ano, ano + 1, ano - 1, ano + 2, ano - 2):
        url = f"https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/{p}/variaveis/9324?localidades=N3[35]"
        try:
            res = requests.get(url, timeout=15)
            res.raise_for_status()
            serie = res.json()[0]["resultados"][0]["series"][0]["serie"]
            if serie:
                pop = int(list(serie.values())[0])
                print(f"   ✓ População obtida (ano-base {p}): {pop:,} habitantes.")
                return pop
        except Exception:
            continue

    pop_fallback = 44411238
    print(f"   ⚠ Falha na API Demográfica para {ano} e anos vizinhos. Utilizando fallback: {pop_fallback:,}.")
    return pop_fallback


# ==============================================================================
# 2. CONFIGURAÇÃO METODOLÓGICA E REGRAS DE CONVERSÃO
# ==============================================================================

depara_config = [
    {
        "grupo": "Arroz",
        "codigo_producao": "Arroz (em casca)",
        "posicao_ncm": "1006",
        "codigo_pof": "Cereais - Arroz",
        "fator_processamento": 0.70,
        "pct_nao_alimentar": 0.02,
        "pct_perdas": 0.05,
        "consumo_per_capita_kg_ano": 15.2
    },
    {
        "grupo": "Feijão",
        "codigo_producao": "Feijão (em grão)",
        "posicao_ncm": "0713",
        "codigo_pof": "Leguminosas - Feijão",
        "fator_processamento": 1.00,
        "pct_nao_alimentar": 0.03,
        "pct_perdas": 0.08,
        "consumo_per_capita_kg_ano": 5.8
    },
    {
        "grupo": "Soja / Óleo",
        "codigo_producao": "Soja (em grão)",
        "posicao_ncm": "1507",
        "codigo_pof": "Óleos e Gorduras - Soja",
        "fator_processamento": 0.18,
        "pct_nao_alimentar": 0.45,
        "pct_perdas": 0.03,
        "consumo_per_capita_kg_ano": 4.1
    },
    {
        "grupo": "Laranja / Hortifrúti",
        "codigo_producao": "Laranja",
        "posicao_ncm": "0805",
        "codigo_pof": "Frutas - Laranja",
        "fator_processamento": 1.00,
        "pct_nao_alimentar": 0.70,
        "pct_perdas": 0.20,
        "consumo_per_capita_kg_ano": 8.5
    },
    {
        "grupo": "Carne Bovina",
        "codigo_producao": "Carne Bovina (carcaça)",
        "posicao_ncm": "0201",
        "codigo_pof": "Carnes - Carne Bovina",
        "fator_processamento": 0.78,
        "pct_nao_alimentar": 0.03,
        "pct_perdas": 0.05,
        "consumo_per_capita_kg_ano": 17.8
    },
    {
        "grupo": "Carne de Frango",
        "codigo_producao": "Carne de Frango (carcaça)",
        "posicao_ncm": "0207",
        "codigo_pof": "Carnes - Aves",
        "fator_processamento": 0.85,
        "pct_nao_alimentar": 0.02,
        "pct_perdas": 0.04,
        "consumo_per_capita_kg_ano": 19.5
    }
]

df_depara = pd.DataFrame(depara_config)

# ==============================================================================
# 3. PIPELINE INTEGRADO DE PROCESSAMENTO DO BALANÇO
# ==============================================================================

def executar_balanco_automatico(ano: int = 2023):
    """
    Executa o download automático de todas as pontas do modelo e consolida
    o Balanço de Oferta e Demanda do Estado de São Paulo.
    """
    # 1. Download dos Dados Primários
    df_pam = baixar_pam_ibge(ano)
    df_abate = baixar_abate_ibge(ano)
    df_comex = baixar_comex_stat(ano)
    pop_sp = obter_populacao_sp(ano)

    # Unificação da Produção Agrícola e Pecuária
    df_producao_total = pd.concat([df_pam, df_abate], ignore_index=True)

    # 2. Processamento da Oferta Líquida Produzida
    prod_merged = pd.merge(
        df_producao_total,
        df_depara,
        left_on="produto_origem",
        right_on="codigo_producao",
        how="inner"
    )
    
    prod_merged["oferta_liquida_prod_t"] = (
        prod_merged["producao_bruta_t"]
        * prod_merged["fator_processamento"]
        * (1 - prod_merged["pct_nao_alimentar"])
        * (1 - prod_merged["pct_perdas"])
    )
    
    prod_agregada = prod_merged.groupby("grupo")["oferta_liquida_prod_t"].sum().reset_index()

    # 3. Processamento do Comércio Exterior (Conversão kg -> Toneladas)
    comex_merged = pd.merge(
        df_comex,
        df_depara,
        left_on="ncm_posicao",
        right_on="posicao_ncm",
        how="inner"
    )
    comex_merged["toneladas"] = comex_merged["KG_LIQUIDO"] / 1000.0
    
    comex_pivot = comex_merged.pivot_table(
        index="grupo",
        columns="flow",
        values="toneladas",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # Garantir colunas mesmo em ausência de registros
    for col in ["Importacao", "Exportacao"]:
        if col not in comex_pivot.columns:
            comex_pivot[col] = 0.0

    # 4. Cálculo da Demanda Populacional
    df_depara["demanda_total_t"] = (df_depara["consumo_per_capita_kg_ano"] * pop_sp) / 1000.0
    demanda_agregada = df_depara[["grupo", "demanda_total_t"]].copy()

    # 5. Consolidação Final do Balanço de Massa
    balanco = pd.merge(prod_agregada, comex_pivot, on="grupo", how="outer").fillna(0)
    balanco = pd.merge(balanco, demanda_agregada, on="grupo", how="outer").fillna(0)

    # Disponibilidade Internacional
    balanco["disponibilidade_internacional_t"] = (
        balanco["oferta_liquida_prod_t"] + balanco["Importacao"] - balanco["Exportacao"]
    )

    # Saldo Comercial Interestadual Residual
    balanco["saldo_comercio_interestadual_t"] = (
        balanco["disponibilidade_internacional_t"] - balanco["demanda_total_t"]
    )

    # Ordenação e Formatação dos Números
    cols_num = balanco.select_dtypes(include=[np.number]).columns
    balanco[cols_num] = balanco[cols_num].round(2)

    return balanco

# ==============================================================================
# 4. EXECUÇÃO
# ==============================================================================

if __name__ == "__main__":
    df_resultado = executar_balanco_automatico(ano=2023)
    
    print("\n" + "=" * 80)
    print(" BALANÇO AUTOMÁTICO DE OFERTA E DEMANDA DE ALIMENTOS (SÃO PAULO)")
    print("=" * 80)
    print(df_resultado.to_string(index=False))