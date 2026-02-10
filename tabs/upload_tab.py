import streamlit as st
from utils.data_loader import load_file_chamadas, load_file_target, convert_duration_to_seconds
import pandas as pd


def show():
    st.header("📁 Upload de Arquivos")

    # --- ARQUIVO DE CHAMADAS ---
    st.subheader("Arquivo de Chamadas")
    uploaded_file_chamadas = st.file_uploader(
        "Carregar arquivo de chamadas (CSV ou Excel)",
        type=["csv", "xlsx", "xls"],
        key="chamadas_upload"
    )

    if uploaded_file_chamadas:
        df_chamadas, error = load_file_chamadas(uploaded_file_chamadas)
        if error:
            st.error(f"Erro ao carregar arquivo de chamadas: {error}")
            st.session_state.df_chamadas = None
        else:
            if not df_chamadas.empty and 'datetime' in df_chamadas.columns and not df_chamadas['datetime'].isna().all():
                st.session_state.df_chamadas = df_chamadas
                st.success(
                    f"✅ Arquivo de chamadas carregado com sucesso! "
                    f"Total de registros: {len(df_chamadas):,}"
                )
                st.write(f"Colunas detectadas: {list(df_chamadas.columns)}")
                st.write("Primeiras 5 linhas do arquivo de chamadas:")
                st.dataframe(df_chamadas.head())
            else:
                st.error(
                    "❌ O arquivo de chamadas carregado está vazio ou não contém datas válidas após o processamento. "
                    "Verifique o conteúdo do arquivo."
                )
                st.session_state.df_chamadas = None

    # --- ARQUIVO TARGET ---
    st.subheader("Arquivo Target (para Motivos de Rechamadas)")
    uploaded_file_target = st.file_uploader(
        "Carregar arquivo Target (CSV ou Excel)",
        type=["csv", "xlsx", "xls"],
        key="target_upload"
    )

    if uploaded_file_target:
        df_target, error = load_file_target(uploaded_file_target)
        if error:
            st.error(f"Erro ao carregar arquivo target: {error}")
            st.session_state.df_target = None
        else:
            st.session_state.df_target = df_target
            st.success(
                f"✅ Arquivo target carregado com sucesso! "
                f"Total de registros: {len(df_target):,}"
            )
            st.write(f"Colunas detectadas: {list(df_target.columns)}")
            st.write("Primeiras 5 linhas do arquivo target:")
            st.dataframe(df_target.head())

    # --- ARQUIVOS DE DESEMPENHO ---
# ... código existente de upload de chamadas e target ...

    # --- NOVO: ARQUIVO DE NOTA ---
    st.subheader("📊 Arquivo de Nota (Zendesk)")
    uploaded_file_nota = st.file_uploader(
        "Carregar arquivo de Nota",
        type=["csv", "xlsx", "xls"],
        key="nota_upload",
        help="Arquivo com colunas: Nome do atribuído, Notas Atendente, CSAT"
    )

    if uploaded_file_nota:
        with st.spinner("Carregando arquivo de Nota..."):
            df_nota, error = load_file_target(uploaded_file_nota)

            if error:
                st.error(f"❌ Erro ao carregar arquivo de Nota: {error}")
            else:
                # Verifica colunas necessárias
                colunas_necessarias = ['Nome do atribuído', 'Notas Atendente', 'CSAT']
                colunas_faltando = [col for col in colunas_necessarias if col not in df_nota.columns]

                if colunas_faltando:
                    st.error(f"❌ Colunas faltando: {', '.join(colunas_faltando)}")
                    st.info(f"Colunas encontradas: {', '.join(df_nota.columns)}")
                else:
                    # Padroniza nomes
                    df_nota = df_nota.rename(columns={
                        'Nome do atribuído': 'Nome_Agente',
                        'Notas Atendente': 'Notas_Atendente',
                        'CSAT': 'CSAT'
                    })

                    # Limpa dados
                    df_nota = df_nota[df_nota['Nome_Agente'].notna() & (df_nota['Nome_Agente'] != '')]
                    df_nota['Nome_Agente'] = df_nota['Nome_Agente'].astype(str).str.strip().str.lower()
                    df_nota['Notas_Atendente'] = pd.to_numeric(df_nota['Notas_Atendente'], errors='coerce').fillna(0)
                    df_nota['CSAT'] = pd.to_numeric(df_nota['CSAT'], errors='coerce').fillna(0)

                    st.session_state.df_nota = df_nota
                    st.success(f"✅ Arquivo de Nota carregado! {len(df_nota)} agentes.")

                    with st.expander("👁️ Preview"):
                        st.dataframe(df_nota.head(10))

    # --- NOVO: ARQUIVO DE DESEMPENHO ---
    st.subheader("📈 Arquivo de Desempenho (Genesys)")
    uploaded_file_perf = st.file_uploader(
        "Carregar arquivo de Desempenho",
        type=["csv", "xlsx", "xls"],
        key="desempenho_upload",
        help="Arquivo com colunas: Nome do agente, Atendidas, Conversação média, Transferidas, Conversa máx."
    )

    if uploaded_file_perf:
        with st.spinner("Carregando arquivo de Desempenho..."):
            df_perf, error = load_file_target(uploaded_file_perf)

            if error:
                st.error(f"❌ Erro: {error}")
            else:
                colunas_necessarias = ['Nome do agente', 'Atendidas', 'Conversação média', 'Transferidas', 'Conversa máx.']
                colunas_faltando = [col for col in colunas_necessarias if col not in df_perf.columns]

                if colunas_faltando:
                    st.error(f"❌ Colunas faltando: {', '.join(colunas_faltando)}")
                    st.info(f"Colunas encontradas: {', '.join(df_perf.columns)}")
                else:
                    df_perf = df_perf.rename(columns={
                        'Nome do agente': 'Nome_Agente',
                        'Atendidas': 'Atendidas',
                        'Conversação média': 'Conversacao_Media',
                        'Transferidas': 'Transferidas',
                        'Conversa máx.': 'Conversa_Max'
                    })

                    df_perf = df_perf[df_perf['Nome_Agente'].notna() & (df_perf['Nome_Agente'] != '')]
                    df_perf['Nome_Agente'] = df_perf['Nome_Agente'].astype(str).str.strip().str.lower()

                    # Converte durações para segundos
                    df_perf['TMA_Segundos'] = df_perf['Conversacao_Media'].apply(convert_duration_to_seconds)
                    df_perf['Conversa_Max_Segundos'] = df_perf['Conversa_Max'].apply(convert_duration_to_seconds)

                    df_perf['Atendidas'] = pd.to_numeric(df_perf['Atendidas'], errors='coerce').fillna(0).astype(int)
                    df_perf['Transferidas'] = pd.to_numeric(df_perf['Transferidas'], errors='coerce').fillna(0).astype(int)

                    st.session_state.df_desempenho = df_perf
                    st.success(f"✅ Arquivo de Desempenho carregado! {len(df_perf)} agentes.")

                    with st.expander("👁️ Preview"):
                        st.dataframe(df_perf.head(10))

    # --- ARQUIVO DE ATENDIMENTOS DETALHADOS ---
    st.subheader("📋 Arquivo de Atendimentos Detalhados")
    uploaded_file_atendimentos = st.file_uploader(
        "Carregar arquivo de Atendimentos",
        type=["csv", "xlsx", "xls"],
        key="atendimentos_upload",
        help="Arquivo com colunas: Duração, Usuários -Interagiram, Tipo de desconexão"
    )

    if uploaded_file_atendimentos:
        with st.spinner("Carregando arquivo de Atendimentos..."):
            df_atend, error = load_file_target(uploaded_file_atendimentos)

            if error:
                st.error(f"❌ Erro: {error}")
            else:
                # --- NORMALIZAÇÃO DE NOMES DE COLUNA (resolve hífen/traço) ---
                def normalizar_nome_col(col):
                    col = str(col)
                    # troca EN DASH (–) e EM DASH (—) por hífen normal (-)
                    col = col.replace('–', '-').replace('—', '-')
                    # remove espaços duplicados
                    col = ' '.join(col.split())
                    return col.strip()

                df_atend.rename(columns=lambda c: normalizar_nome_col(c), inplace=True)

                # Agora os nomes normalizados:
                # 'Usuários – Interagiram' -> 'Usuários - Interagiram'
                colunas_necessarias = ['Duração', 'Usuários - Interagiram', 'Tipo de desconexão']
                colunas_faltando = [c for c in colunas_necessarias if c not in df_atend.columns]

                if colunas_faltando:
                    st.error(f"❌ Colunas faltando: {', '.join(colunas_faltando)}")
                    st.info(f"Colunas encontradas (normalizadas): {', '.join(df_atend.columns)}")
                else:
                    # Renomeia para padrão interno
                    df_atend = df_atend.rename(columns={
                        'Usuários - Interagiram': 'Nome_Agente',
                        'Duração': 'Duracao',
                        'Tipo de desconexão': 'Tipo_Desconexao'
                    })

                    # 1. NORMALIZA NOME DO AGENTE
                    df_atend['Nome_Agente'] = (
                        df_atend['Nome_Agente']
                        .astype(str)
                        .str.strip()
                        .str.lower()
                    )

                    df_atend = df_atend[
                        df_atend['Nome_Agente'].notna() &
                        (df_atend['Nome_Agente'] != '') &
                        (df_atend['Nome_Agente'] != 'nan')
                    ]

                    # 2. CONVERTE DURAÇÃO PARA SEGUNDOS
                    df_atend['duracao_segundos'] = df_atend['Duracao'].apply(convert_duration_to_seconds)

                    # 3. TIPO DE DESCONEXÃO → marcar AGENTE
                    df_atend['Tipo_Desconexao'] = (
                        df_atend['Tipo_Desconexao']
                        .astype(str)
                        .str.strip()
                        .str.lower()
                    )
                    df_atend['desconexao_agente'] = df_atend['Tipo_Desconexao'] == 'agente'

                    # Estatísticas rápidas
                    total_registros = len(df_atend)
                    total_agentes = df_atend['Nome_Agente'].nunique()
                    total_desconexoes_agente = df_atend['desconexao_agente'].sum()
                    duracao_media = df_atend['duracao_segundos'].mean()

                    st.session_state.df_atendimentos = df_atend
                    st.success("✅ Atendimentos carregados e processados com sucesso!")

                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    with col_m1:
                        st.metric("Total de Atendimentos", f"{total_registros:,}")
                    with col_m2:
                        st.metric("Agentes Únicos", f"{total_agentes}")
                    with col_m3:
                        st.metric("Desconexões (Agente)", f"{total_desconexoes_agente:,}")
                    with col_m4:
                        st.metric("Duração Média", f"{duracao_media/60:.1f} min")

                    with st.expander("👁️ Preview dos Dados Processados"):
                        st.dataframe(
                            df_atend[[
                                'Nome_Agente',
                                'Duracao',
                                'duracao_segundos',
                                'Tipo_Desconexao',
                                'desconexao_agente'
                            ]].head(10),
                            use_container_width=True
                        )

                        st.write("**Distribuição de Tipos de Desconexão:**")
                        dist_desconexao = df_atend['Tipo_Desconexao'].value_counts()
                        st.dataframe(
                            dist_desconexao
                            .reset_index()
                            .rename(columns={'index': 'Tipo', 'Tipo_Desconexao': 'Quantidade'})
                        )

