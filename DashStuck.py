import streamlit as st
import pandas as pd
import os
from datetime import date
import gspread # Importa a biblioteca gspread
from oauth2client.service_account import ServiceAccountCredentials # Para autenticação

# Configura o layout da página para "wide" (amplo)
st.set_page_config(layout="wide")

# Título do aplicativo Streamlit
st.title('Dashboard de Dados Regionais')

# Define o nome do arquivo CSV
csv_file_name = "Data_Suit_RegionalCONO.csv" # Mantenha o nome do arquivo CSV original

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
            st.subheader('Justificativas e Filtragem de Dados')

            # --- Segmentação da coluna "Station Name" ---
            all_stations = ['Todas as Estações'] + sorted(df['Station Name'].unique().tolist())
            selected_stations = st.multiselect(
                "Selecione uma ou mais Estações:",
                options=all_stations,
                default=['Todas as Estações'] # Seleção padrão
            )

            # --- Filtra o DataFrame com base na seleção da estação ---
            filtered_df_justificativas = df.copy() # Cria uma cópia para não alterar o DataFrame original

            if 'Todas as Estações' not in selected_stations:
                filtered_df_justificativas = filtered_df_justificativas[
                    filtered_df_justificativas['Station Name'].isin(selected_stations)
                ]

            # Lista de todas as colunas que podem ser exibidas e editadas
            all_possible_display_columns = [
                'shipment_id', 'ageing_last_status', 'cogs(SUM)', 'driver_name',
                'tracking_status', 'buyer_city', 'xpt_received_time', 'app_confirmation_date',
                'Check', 'Justificativa', 'Motivo Lost', 'Observações'
            ]

            # Verifica e cria colunas placeholder se não existirem (para as novas colunas e 'Check')
            for col in ['Check', 'Justificativa', 'Motivo Lost', 'Observações']:
                if col not in filtered_df_justificativas.columns:
                    filtered_df_justificativas[col] = '' # Inicializa com string vazia

            # Lista de opções para 'Justificativa'
            today_date = date.today().strftime("%d/%m") # Formata a data como DD/MM
            justificativa_options = [
                "", # Adiciona uma opção vazia para facilitar a seleção inicial
                "Avaria",
                "BR c/ 02 Etiquetas",
                "Cliente sem Password",
                "Devolução (Pend. Envio)",
                "Devolução (pendente Hub/Soc)",
                "Devolução Concluida",
                "Drive Retorno base",
                "Entregue",
                "Erro de Triagem",
                "Erro Hub - Pacote fora de Rota",
                "Falta",
                "Interception",
                "Lost",
                "Recebido pelo Hub",
                "Pacote em outro XPT",
                f"Rota {today_date}", # Opção dinâmica com a data atual
                "Sem Etiqueta"
            ]

            # Lista de opções para 'Motivo Lost'
            motivo_lost_options = [
                "", # Adiciona uma opção vazia
                "Driver Perdeu durante o Trajeto",
                "Driver Perdeu na casa",
                "Perdido durante o Trajeto Line Haul",
                "Perdido durante o Trajeto XPT > Interior",
                "Driver não soube responder",
                "Perdido durante a separação no XPT",
                "Recebido na base e perdido",
                "Pacote Enviado para o Hub/SOC, sem baixa",
                "Erro de Processo - Entregou sem dar baixa"
            ]

            # Define as configurações de coluna para st.data_editor
            column_configuration = {
                # Colunas NÃO editáveis
                "shipment_id": st.column_config.TextColumn("ID do Envio", disabled=True),
                "ageing_last_status": st.column_config.NumberColumn("Dias Parado", disabled=True),
                "cogs(SUM)": st.column_config.NumberColumn("Cogs (SUM)", disabled=True),
                "driver_name": st.column_config.TextColumn("Nome do Motorista", disabled=True),
                "tracking_status": st.column_config.TextColumn("Status de Rastreamento", disabled=True),
                "buyer_city": st.column_config.TextColumn("Cidade do Comprador", disabled=True),
                "xpt_received_time": st.column_config.TextColumn("Hora Recebida XPT", disabled=True),
                "app_confirmation_date": st.column_config.TextColumn("Data Confirmação App", disabled=True),
                "Check": st.column_config.CheckboxColumn("Check", default=False, disabled=True), # 'Check' não editável

                # Colunas EDITÁVEIS
                "Justificativa": st.column_config.SelectboxColumn(
                    "Justificativa",
                    help="Selecione a justificativa para a ocorrência.",
                    options=justificativa_options,
                    required=False,
                    disabled=False, # Explicitamente editável
                ),
                "Motivo Lost": st.column_config.SelectboxColumn(
                    "Motivo Lost",
                    help="Preencha apenas se a Justificativa for 'Lost'.",
                    options=motivo_lost_options,
                    required=False,
                    disabled=False, # Explicitamente editável
                ),
                "Observações": st.column_config.TextColumn(
                    "Observações",
                    help="Adicione observações (até 120 caracteres).",
                    max_chars=120,
                    default="",
                    disabled=False, # Explicitamente editável
                ),
            }

            # Filtra `all_possible_display_columns` para incluir apenas as colunas que existem
            # no DataFrame (original ou adicionadas como placeholders) para exibição.
            actual_columns_for_display = [col for col in all_possible_display_columns if col in filtered_df_justificativas.columns]

            st.subheader('Tabela Filtrada por Estação (Editável):')

            # Exibir um aviso sobre a limitação de cores
            st.warning(
                "**Nota sobre cores:** As cores de fundo solicitadas para colunas editáveis/não editáveis (#E9EBED e #FFE7A6) "
                "não podem ser aplicadas de forma confiável a colunas individuais dentro da tabela editável "
                "(`st.data_editor`) via código Python ou CSS customizado simples, devido à forma como o Streamlit "
                "renderiza esses componentes. No entanto, a funcionalidade de editar/não editar foi implementada conforme solicitado."
            )

            edited_df = st.data_editor(
                filtered_df_justificativas[actual_columns_for_display],
                column_config=column_configuration,
                num_rows="dynamic", # Permite adicionar novas linhas
                use_container_width=True # Faz a tabela usar a largura total do container
            )

            st.write("Dados Editados (para uso posterior, como salvar no Google Sheets):")
            st.dataframe(edited_df)

            # Botão de salvar registros
            if st.button("Salvar Registros"):
                # Filtra as linhas onde 'Justificativa' não é nula/vazia
                records_to_save = edited_df[edited_df['Justificativa'] != ""].copy()

                if not records_to_save.empty:
                    try:
                        # Autenticação com o Google Sheets
                        # As credenciais são carregadas do .streamlit/secrets.toml
                        scope = ['https://spreadsheets.google.com/feeds',
                                 'https://www.googleapis.com/auth/drive']
                        
                        # Carrega as credenciais do Streamlit secrets
                        creds = ServiceAccountCredentials.from_json_keyfile_dict(
                            st.secrets["gcp_service_account"], scope
                        )
                        client = gspread.authorize(creds)

                        # Abre a planilha pelo URL ou ID
                        spreadsheet_id = "1EMv5yZAaLmTj9wdi-h7-TqppQJCy9WRpFo8aSqMMDis"
                        spreadsheet = client.open_by_key(spreadsheet_id)
                        
                        # Seleciona a aba "Registro"
                        worksheet = spreadsheet.worksheet("Registro")

                        # Define a ordem das colunas para salvar no Google Sheets.
                        # É CRUCIAL que essa ordem corresponda exatamente à ordem das colunas na sua aba "Registro" do Google Sheets.
                        # Por favor, ajuste esta lista se a ordem das colunas na sua Google Sheet for diferente.
                        columns_to_save_order = [
                            'Station Name', 'State Name', 'buyer_city', 'shipment_id', 'to_number', 
                            'tracking_status', 'ageing_range', 'ageing_last_status', 'otp', 
                            'driver_name', 'xpt_received_time', 'app_confirmation_date', 'cogs(SUM)',
                            'Check', 'Justificativa', 'Motivo Lost', 'Observações'
                        ]

                        # Prepara os dados para salvar
                        # Cria uma cópia do DataFrame original para ter acesso a todas as colunas
                        # e então mescla com os dados editados.
                        # Para garantir que todas as colunas originais estejam presentes na linha a ser salva,
                        # é necessário juntar o edited_df com o df original por um ID, como shipment_id.
                        
                        # Vamos criar uma forma de garantir que as colunas originais estejam presentes
                        # na linha que será salva, juntando com o df original.
                        
                        # Pega os índices das linhas que foram editadas e que têm Justificativa
                        edited_non_empty_just_indices = records_to_save.index

                        # Cria um DataFrame final para salvar, incluindo todas as colunas originais
                        # e as novas colunas editáveis, para as linhas que foram modificadas.
                        
                        # Primeiro, pegamos as linhas completas do DataFrame original que correspondem
                        # aos IDs que foram editados e que possuem justificativa.
                        
                        # Pega os shipment_ids das linhas editadas que não são vazias
                        shipment_ids_to_update = records_to_save['shipment_id'].tolist()
                        
                        # Filtra o DataFrame original pelas linhas que foram editadas
                        full_rows_to_save = df[df['shipment_id'].isin(shipment_ids_to_update)].copy()

                        # Atualiza as colunas editáveis com os valores de edited_df
                        for index, row in records_to_save.iterrows():
                            # Encontra o índice correspondente no full_rows_to_save usando shipment_id
                            original_row_index = full_rows_to_save[full_rows_to_save['shipment_id'] == row['shipment_id']].index
                            if not original_row_index.empty:
                                for col in ['Justificativa', 'Motivo Lost', 'Observações', 'Check']: # Incluir Check se for para ser salvo
                                    if col in row: # Verifica se a coluna está no row editado
                                        full_rows_to_save.loc[original_row_index, col] = row[col]

                        # Adiciona colunas que podem não estar no DF original mas são editáveis/necessárias
                        for col in ['Check', 'Justificativa', 'Motivo Lost', 'Observações']:
                            if col not in full_rows_to_save.columns:
                                full_rows_to_save[col] = '' # Adiciona como vazio se não existir

                        # Converte para a ordem desejada e para lista de listas
                        list_of_rows = full_rows_to_save[columns_to_save_order].values.tolist()

                        # Adiciona um cabeçalho para a Google Sheet se for a primeira vez
                        # Esta lógica é mais adequada se a sheet "Registro" começar vazia.
                        # Se ela já tiver cabeçalhos, esta parte deve ser removida.
                        # current_sheet_data = worksheet.get_all_values()
                        # if not current_sheet_data: # Se a planilha estiver vazia, adiciona cabeçalhos
                        #    worksheet.append_row(columns_to_save_order)

                        # Adiciona as linhas à planilha
                        worksheet.append_rows(list_of_rows)
                        st.success("Registros salvos com sucesso no Google Sheets!")

                    except Exception as e:
                        st.error(f"Erro ao salvar registros no Google Sheets: {e}")
                        st.warning("Verifique suas credenciais no `.streamlit/secrets.toml` e as permissões da conta de serviço na planilha.")
                else:
                    st.info("Nenhuma linha com 'Justificativa' preenchida para salvar.")

        elif menu_selection == "Tabela":
            st.subheader('As 10 Primeiras Linhas dos Dados (após tratamento):')
            st.dataframe(df.head(10)) # Exibe as 10 primeiras linhas da tabela

    except Exception as e:
        st.error(f'Ocorreu um erro inesperado ao processar o arquivo CSV: {e}')
        st.warning('Certifique-se de que o arquivo CSV esteja formatado corretamente, e que os dados em "ageing_last_status" sejam numéricos.')
else:
    st.error(f'Erro: O arquivo "{csv_file_name}" não foi encontrado no diretório atual.')
    st.info('Por favor, certifique-se de que o arquivo CSV está no mesmo diretório do seu script Streamlit.')



