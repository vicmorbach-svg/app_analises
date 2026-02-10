import streamlit as st
import pandas as pd
import io
from datetime import datetime
from utils.data_loader import identificar_faixas_rechamada # Importa a função de análise de rechamadas (se precisar)

def show():
    st.header("📧 Lista para Mailing")

    if st.session_state.get('df_chamadas') is None:
        st.warning("⚠️ Nenhum dado de chamadas carregado. Por favor, faça o upload do arquivo de atendimentos na aba 'Upload de Arquivos'.")
        return

    df = st.session_state.df_chamadas.copy()

    st.subheader("Critérios para Geração de Lista")

    criterios = st.multiselect(
        "Selecione os critérios para incluir na lista de mailing:",
        [
            "Clientes que mais ligaram",
            "Clientes com rechamadas",
            "Clientes com ligações longas",
            # "Clientes com notas baixas" # Adicionar quando a aba de agentes estiver completa
        ],
        default=["Clientes que mais ligaram"]
    )

    # Variáveis para armazenar os valores dos inputs, inicializadas com valores padrão
    min_ligacoes_mailing = 5
    periodos_mailing = []
    duracao_minima_mailing_seg = 0 # Inicializa com 0 segundos

    # Configurações específicas para cada critério
    if "Clientes que mais ligaram" in criterios:
        min_ligacoes_mailing = st.number_input(
            "Mínimo de ligações para incluir na lista (Clientes que mais ligaram)",
            value=5,
            min_value=2,
            key="min_ligacoes_mailing"
        )

    if "Clientes com rechamadas" in criterios:
        if st.session_state.get('rechamadas_detalhe') is None:
            st.warning("Para o critério 'Clientes com rechamadas', execute a análise de rechamadas primeiro na aba 'Análise de Rechamadas'.")
            # periodos_mailing permanece vazio se não houver dados ou análise
        else:
            periodos_mailing = st.multiselect(
                "Períodos de rechamadas a considerar (Clientes com rechamadas)",
                ["0-24h", "24-48h", "48-72h"],
                default=["0-24h"],
                key="periodos_mailing"
            )

    if "Clientes com ligações longas" in criterios:
        duracao_minima_mailing_min = st.number_input(
            "Duração mínima da ligação (minutos) para incluir na lista (Clientes com ligações longas)",
            value=10,
            min_value=1,
            max_value=120,
            key="duracao_minima_mailing"
        )
        duracao_minima_mailing_seg = duracao_minima_mailing_min * 60 # Converte para segundos aqui

    # if "Clientes com notas baixas" in criterios:
    #     if st.session_state.get('df_nota') is None:
    #         st.warning("Para o critério 'Clientes com notas baixas', carregue o arquivo de notas na aba 'Upload de Arquivos'.")
    #     else:
    #         nota_maxima_mailing = st.slider("Nota máxima para considerar 'baixa'", 1, 10, 6, key="nota_max_mailing")

    if st.button("Gerar Lista para Mailing"):
        with st.spinner("Gerando lista..."):
            lista_mailing = pd.DataFrame()

            # Clientes que mais ligaram
            if "Clientes que mais ligaram" in criterios:
                contagem = df.groupby('telefone').size()
                clientes_frequentes_mailing = contagem[contagem >= min_ligacoes_mailing].reset_index()
                clientes_frequentes_mailing.columns = ['telefone', 'total_ligacoes']
                if not lista_mailing.empty:
                    lista_mailing = pd.merge(lista_mailing, clientes_frequentes_mailing, on='telefone', how='outer')
                else:
                    lista_mailing = clientes_frequentes_mailing

            # Clientes com rechamadas
            if "Clientes com rechamadas" in criterios and st.session_state.get('rechamadas_detalhe') and periodos_mailing:
                telefones_rechamadas = set()
                for periodo in periodos_mailing:
                    if periodo in st.session_state.rechamadas_detalhe:
                        telefones_rechamadas.update([item['telefone'] for item in st.session_state.rechamadas_detalhe[periodo]])
                df_rechamadas_mailing = pd.DataFrame({'telefone': list(telefones_rechamadas), 'tem_rechamada': True})
                if not lista_mailing.empty:
                    lista_mailing = pd.merge(lista_mailing, df_rechamadas_mailing, on='telefone', how='outer')
                else:
                    lista_mailing = df_rechamadas_mailing

            # Clientes com ligações longas
            if "Clientes com ligações longas" in criterios:
                ligacoes_longas_filtradas = df[df['duracao_segundos'] >= duracao_minima_mailing_seg]
                telefones_ligacoes_longas = ligacoes_longas_filtradas['telefone'].unique()
                df_ligacoes_longas_mailing = pd.DataFrame({'telefone': telefones_ligacoes_longas, 'tem_ligacao_longa': True})
                if not lista_mailing.empty:
                    lista_mailing = pd.merge(lista_mailing, df_ligacoes_longas_mailing, on='telefone', how='outer')
                else:
                    lista_mailing = df_ligacoes_longas_mailing

            # Clientes com notas baixas (placeholder)
            # if "Clientes com notas baixas" in criterios and st.session_state.get('df_nota') is not None:
            #     df_nota_mailing = st.session_state.df_nota.copy()
            #     # Lógica para identificar clientes com notas baixas
            #     # Exemplo: df_clientes_notas_baixas = df_nota_mailing[df_nota_mailing['Nota_Media_Satisfacao'] <= nota_maxima_mailing]
            #     # telefones_notas_baixas = df_clientes_notas_baixas['telefone'].unique()
            #     # df_notas_baixas_mailing = pd.DataFrame({'telefone': telefones_notas_baixas, 'tem_nota_baixa': True})
            #     # if not lista_mailing.empty:
            #     #     lista_mailing = pd.merge(lista_mailing, df_notas_baixas_mailing, on='telefone', how='outer')
            #     # else:
            #     #     lista_mailing = df_notas_baixas_mailing


            if lista_mailing.empty:
                st.warning("Nenhum cliente atende aos critérios selecionados.")
            else:
                lista_mailing = lista_mailing.drop_duplicates(subset=['telefone'])
                st.success(f"✅ Lista gerada com {len(lista_mailing)} contatos!")
                st.session_state.df_mailing_list = lista_mailing # Armazena na session_state

                st.subheader("Lista para Mailing")
                st.dataframe(lista_mailing)

                csv = lista_mailing.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar Lista de Mailing (CSV)",
                    data=csv,
                    file_name=f"lista_mailing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )
