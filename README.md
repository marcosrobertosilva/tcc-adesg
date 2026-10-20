# tcc-adesg
TCC ADESG 69o CEPE - Grupo 3 Charlie - Segurança Alimentar e Agricultura Sustentável no Estado de São Paulo

## Código-fonte e parâmetros do balanço alimentar

Esta documentação descreve os dados, parâmetros e procedimentos usados pelo
programa Python para estimar o balanço de oferta e demanda dos seis grupos
alimentares analisados. O [código-fonte](src/balanco-alimentar.py) é mantido
neste repositório.

### Execução e requisitos

O programa requer Python 3 e as bibliotecas `requests`, `pandas` e `numpy`.
A partir da raiz do repositório, pode ser executado com:

```bash
python3 src/balanco-alimentar.py
```

As versões dessas bibliotecas não estão fixadas no código. Para reproduzir
exatamente uma execução, devem ser preservados o script, os arquivos de entrada
e as versões das dependências utilizadas.

### Fontes e parâmetros operacionais

A execução padrão usa 2023 como ano da produção e do comércio exterior e o
código IBGE 35 para São Paulo. A produção agrícola é consultada na PAM (Tabela
5457, variável 214, classificação 782[all] e localidade N3[35]). A produção de
carne bovina e de frango é obtida nas Tabelas 1092 e 1094 da Pesquisa Trimestral
do Abate, variável 285, somando-se os quatro trimestres. Para bovinos, são
selecionadas as classificações 18[992], 12529[118225] e 12716[115236]; para
frangos, 12529[118225] e 12716[115236]. Os pesos do abate, originalmente em
quilogramas, são convertidos para toneladas dividindo-se por 1.000. O comércio
exterior é lido dos arquivos `EXP_2023.csv` e `IMP_2023.csv`, localizados por
padrão em `src/dados_comex/`; se os arquivos não existirem, o script tenta
baixá-los do Comex Stat.

Para o Comex Stat são lidas as colunas `CO_NCM`, `SG_UF_NCM` e `KG_LIQUIDO`.
Os registros são filtrados por `SP`; o código NCM é preenchido com zeros à
esquerda e reduzido à posição de quatro dígitos. O peso líquido, em
quilogramas, é convertido para toneladas dividindo-se por 1.000. Linhas
malformadas são ignoradas pelo leitor de CSV; valores não numéricos de peso são
descartados. A população é consultada na Tabela 6579 do IBGE, variável 9324.
Para o ano de execução 2023, o programa tenta, nesta ordem, 2023, 2024, 2022,
2025 e 2021; nesta execução foi encontrado o valor de 45.973.194 habitantes
para 2024.

Os parâmetros de conversão, perdas, usos não alimentares e aquisição per capita
estão definidos diretamente no dicionário `depara_config` do código. As
categorias da POF na tabela servem como rótulos de correspondência: o script
não consulta microdados da POF durante a execução, e os valores per capita são
constantes configuradas no próprio programa.

| Grupo | NCM | Fator de processamento ($f_{\mathrm{proc}}$) | Uso não alimentar ($u_{\mathrm{na}}$) | Perdas ($\ell$) | Aquisição ($c_i$, kg/hab./ano) | Categoria de referência da POF |
|---|---:|---:|---:|---:|---:|---|
| Arroz | 1006 | 0,70 | 2% | 5% | 15,2 | Cereais -- Arroz |
| Feijão | 0713 | 1,00 | 3% | 8% | 5,8 | Leguminosas -- Feijão |
| Soja / óleo | 1507 | 0,18 | 45% | 3% | 4,1 | Óleos e gorduras -- Soja |
| Laranja / hortifrúti | 0805 | 1,00 | 70% | 20% | 8,5 | Frutas -- Laranja |
| Carne bovina | 0201 | 0,78 | 3% | 5% | 17,8 | Carnes -- Carne bovina |
| Carne de frango | 0207 | 0,85 | 2% | 4% | 19,5 | Carnes -- Aves |

Os nomes esperados para a correspondência com a produção são “Arroz (em
casca)”, “Feijão (em grão)”, “Soja (em grão)”, “Laranja”, “Carne Bovina
(carcaça)” e “Carne de Frango (carcaça)”. A oferta líquida da produção é
calculada multiplicando-se a produção bruta pelo fator de processamento, por
$1-u_{\mathrm{na}}$ e por $1-\ell$. As exportações e importações são somadas
pelas massas líquidas declaradas no Comex, sem aplicar novamente esses fatores.
A demanda estimada é $c_i \times \mathrm{POP}/1.000$. Por fim, o saldo
residual é a disponibilidade internacional (oferta líquida da produção mais
importações menos exportações) menos a demanda total. Estoques são considerados
sem variação; o saldo não mede diretamente fluxos interestaduais.

### Contingências e parâmetros de conexão

Se uma fonte falhar, o script contém valores de contingência. Eles não devem ser
confundidos com os dados oficiais usados nos resultados apresentados no corpo
do trabalho. A execução deve ser conferida pelas mensagens do terminal; se
aparecer “Aplicando estrutura de apoio” ou “Aplicando mock calibrado”, a
respectiva fonte não foi obtida e os resultados daquela parte são simulados.

| Produto / NCM | Produção de apoio (t) | Exportação de apoio (kg) | Importação de apoio (kg) |
|---|---:|---:|---:|
| Arroz / 1006 | 80.000 | 5.000.000 | 120.000.000 |
| Feijão / 0713 | 150.000 | 2.000.000 | 30.000.000 |
| Soja / 1507 | 4.200.000 | 250.000.000 | 15.000.000 |
| Laranja / 0805 | 13.000.000 | 0 | 0 |
| Carne bovina / 0201 | 580.000 | 210.000.000 | 25.000.000 |
| Carne de frango / 0207 | 1.350.000 | 320.000.000 | 3.000.000 |

Se a API populacional não retornar dados para nenhum dos anos tentados, o
programa usa 44.411.238 habitantes. As chamadas à API PAM e à pesquisa de abate
usam tempo limite de 30 segundos; a API populacional, 15 segundos. Para o
Comex, cada requisição usa até 60 segundos e o download pode ser retomado por
intervalos, com até 10 tentativas. A variável `DADOS_COMEX_DIR` altera a pasta
dos arquivos locais. `COMEX_CA_BUNDLE` informa um bundle de certificados TLS
para o Comex. `COMEX_SKIP_TLS_VERIFY=1` desativa a validação TLS e reduz a
segurança da conexão; não é recomendado para uso regular.

Para reproduzir os valores reportados, devem ser usados os arquivos Comex
locais da execução e a mesma configuração do script. As consultas às APIs do
IBGE são feitas novamente a cada execução e podem mudar conforme atualizações
ou revisões das bases; recomenda-se arquivar as respostas obtidas, registrar a
data da consulta e preservar os arquivos CSV empregados.

### Código-fonte

[Script Python do balanço de oferta e demanda](src/balanco-alimentar.py).
