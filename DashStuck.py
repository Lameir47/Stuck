import streamlit as st
import pandas as pd
import os

# Configura o layout da página para "wide" (amplo)
st.set_page_config(layout="wide")

# Título do aplicativo Streamlit
st.title('Dashboard de Dados Regionais')

# Define o nome do arquivo CSV
csv_file_name = "Data_Suit_RegionalCONO_CSV.csv"

# Verifica se o arquivo CSV existe no diretório atual
if os.path.exists(csv_file_name):
    try:
        # Carrega o arquivo CSV em um DataFrame do pandas
        df = pd.read_csv(csv_file_name)

        st.success(f'Arquivo "{csv_file_name}" carregado com sucesso!')

        # --- Injeta CSS para estilo da tabela ---
        st.markdown(
            """
            <style>
            /* Estilo para as tabelas exibidas pelo st.dataframe */
            /* Target o container do st.dataframe usando o atributo data-testid para maior estabilidade */
            div[data-testid="stDataFrame"] {
                border: 2px solid #EE4D2D; /* Borda na cor desejada */
                border-radius: 8px; /* Bordas arredondadas para um visual mais moderno */
                padding: 10px; /* Adiciona um preenchimento interno para "aumentar" a visualização */
                box-shadow: 3px 3px 10px rgba(0, 0, 0, 0.1); /* Sombra suave para destacar a tabela */
            }

            /* Garante que as células da tabela interna também tenham um estilo limpo */
            div[data-testid="stDataFrame"] table {
                border-collapse: collapse; /* Colapsa as bordas da tabela interna */
                width: 100%; /* Garante que a tabela interna ocupe todo o espaço do container */
            }

            div[data-testid="stDataFrame"] table th,
            div[data-testid="stDataFrame"] table td {
                border: 1px solid #f0f2f6; /* Uma cor mais clara para as bordas internas das células */
                padding: 8px; /* Espaçamento interno das células */
                text-align: left; /* Alinha o texto à esquerda */
            }

            /* O st.dataframe já é responsivo e se ajusta à largura da coluna.
               Para uma "visualização maior" além da borda e padding, como fonte ou altura fixa,
               seriam necessárias configurações mais complexas que podem afetar a responsividade geral. */
            </style>
            """,
            unsafe_allow_html=True # Permite a injeção de HTML e CSS
        )

        # --- Verificações para depuração ---
        # 1. Verifica se 'df' é um DataFrame
        if not isinstance(df, pd.DataFrame):
            st.error(f"Erro: O arquivo '{csv_file_name}' não foi lido como um DataFrame. Tipo detectado: {type(df)}")
            st.warning("Verifique se o arquivo CSV não está vazio ou malformado.")
            st.stop() # Interrompe a execução para evitar erros posteriores

        # 2. Verifica se as colunas necessárias existem
        required_columns = ['Station Name', 'ageing_last_status']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            st.error(f"Erro: Colunas necessárias não encontradas no arquivo CSV: {', '.join(missing_columns)}")
            st.warning("Por favor, verifique a grafia exata dos nomes das colunas no seu arquivo CSV, incluindo espaços e maiúsculas/minúsculas.")
            st.info(f"Colunas disponíveis no arquivo: {', '.join(df.columns)}")
            st.stop() # Interrompe a execução

        # --- TRATAMENTO DE DADOS: Assegura que 'ageing_last_status' é numérico ---
        # Converte para tipo numérico, tratando erros (valores não numéricos) como NaN
        df['ageing_last_status'] = pd.to_numeric(df['ageing_last_status'], errors='coerce')

        # Remove linhas onde 'ageing_last_status' se tornou NaN após a conversão (valores que não eram numéricos)
        original_rows = df.shape[0]
        df.dropna(subset=['ageing_last_status'], inplace=True)
        rows_after_dropna = df.shape[0]

        if original_rows > rows_after_dropna:
            st.warning(f"Foram removidas {original_rows - rows_after_dropna} linhas contendo valores não numéricos na coluna 'ageing_last_status'.")

        # Converte a coluna para tipo inteiro. Isso é crucial para que os cabeçalhos das colunas na pivot table sejam inteiros.
        df['ageing_last_status'] = df['ageing_last_status'].astype(int)

        # --- PIVOT TABLE DETALHADA USANDO pd.crosstab ---

        # Cria a pivot table detalhada usando pd.crosstab
        # index=df['Station Name']: Linhas da tabela dinâmica
        # columns=df['ageing_last_status']: Colunas da tabela dinâmica (valores únicos desta coluna)
        # margins=True: Adiciona totais de linha e coluna ("Grand Total")
        df_detailed_pivot = pd.crosstab(
            index=df['Station Name'],
            columns=df['ageing_last_status'],
            margins=True # Adiciona a coluna e linha de Grand Total
        )

        # Opcional: Renomear a coluna 'All' gerada por margins=True para 'Grand Total'
        if 'All' in df_detailed_pivot.columns:
            df_detailed_pivot = df_detailed_pivot.rename(columns={'All': 'Grand Total'})
        if 'All' in df_detailed_pivot.index:
            df_detailed_pivot = df_detailed_pivot.rename(index={'All': 'Grand Total'})


        # --- Criação do menu lateral ---
        menu_selection = st.sidebar.radio("Navegação", ["Visão Geral", "Justificativas", "Tabela"])

        if menu_selection == "Visão Geral":
            st.subheader('Contagem por "Station Name" e "ageing_last_status" (usando crosstab):')
            st.dataframe(df_detailed_pivot) # Exibe a pivot table detalhada

        elif menu_selection == "Justificativas":
            st.subheader('Justificativas para o Dashboard')
            st.write("""
            Nesta seção, você pode adicionar textos explicativos sobre o propósito do dashboard,
            a metodologia utilizada, as fontes dos dados, e qualquer outra informação relevante
            para contextualizar as análises apresentadas.
            """)

        elif menu_selection == "Tabela":
            st.subheader('As 10 Primeiras Linhas dos Dados (após tratamento):')
            st.dataframe(df.head(10)) # Exibe as 10 primeiras linhas da tabela

    except Exception as e:
        st.error(f'Ocorreu um erro inesperado ao processar o arquivo CSV: {e}')
        st.warning('Certifique-se de que o arquivo CSV esteja formatado corretamente, e que os dados em "ageing_last_status" sejam numéricos.')
else:
    st.error(f'Erro: O arquivo "{csv_file_name}" não foi encontrado no diretório atual.')
    st.info('Por favor, certifique-se de que o arquivo CSV está no mesmo diretório do seu script Streamlit.')