import streamlit as st
from utils.data_loader import load_file_chamadas, load_file_target, convert_duration_to_seconds
import pandas as pd
import os
from sqlalchemy import create_engine

# --- FUNÇÃO AUXILIAR PARA SALVAR NO BANCO ---
def salvar_no_banco(df, nome_tabela, modo):
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    if db_url:
        try:
            engine = create_engine(db_url)
            df.to_sql(nome_tabela, engine, if_exists=modo, index=False)
            acao = "adicionados ao histórico" if modo == 'append' else "substituídos"
            st.success(f"✅ Dados {acao} na tabela '{nome_tabela}' do banco! Total: {len(df):,}")
            return True
        except Exception as e:
            st.error(f"❌ Erro ao salvar na tabela '{nome_tabela}': {e}")
            return False
    else:
        st.warning("⚠️ DATABASE_URL não encontrada. Dados salvos apenas na sessão atual.")
        return False

def show():
    st.header("📁 Upload de Arquivos")

    # --- CONTROLE DE SALVAMENTO NO BANCO ---
    st.info("💡 **Configuração de Banco de Dados:** Escolha como os novos dados serão salvos.")
    modo_salvamento = st.radio(
        "Modo de Salvamento:",
        options=["Adicionar aos dados existentes (Append)", "Substituir dados existentes (Replace)"],
        horizontal=True
    )
    if_exists_mode = 'append' if 'Adicionar' in modo_salvamento else 'replace'
    st.divider()

    # --- ARQUIVO DE CHAMADAS ---
    st.subheader("Arquivo de Chamadas")
    uploaded_file_chamadas = st.file_uploader(
        "Carregar arquivo de chamadas (CSV, Excel ou Parquet)",
        type=["csv", "xlsx", "xls", "parquet"],
        key="chamadas_upload"
    )

    if uploaded_file_chamadas:
        if st.button("🚀 Processar e Salvar Chamadas", type="primary", key="btn_chamadas"):
            with st.spinner("Processando..."):
                df_chamadas, error = load_file_chamadas(uploaded_file_chamadas)
                if error:
                    st.error(f"Erro ao carregar arquivo de chamadas: {error}")
                elif not df_chamadas.empty and 'datetime' in df_chamadas.columns and not df_chamadas['datetime'].isna().all():
                    salvar_no_banco(df_chamadas, 'chamadas', if_exists_mode)
                    st.session_state.df_chamadas = df_chamadas
                    with st.expander("👁️ Preview"):
                        st.dataframe(df_chamadas.head())
                else:
                    st.error("❌ O arquivo está vazio ou sem datas válidas.")

    st.divider()

    # --- ARQUIVO TARGET ---
    st.subheader("Arquivo Target (para Motivos de Rechamadas)")
    uploaded_file_target = st.file_uploader(
        "Carregar arquivo Target (CSV, Excel ou Parquet)",
        type=["csv", "xlsx", "xls", "parquet"],
        key="target_upload"
    )

    if uploaded_file_target:
        if st.button("🚀 Processar e Salvar Target", type="primary", key="btn_target"):
            with st.spinner("Processando..."):
                df_target, error = load_file_target(uploaded_file_target)
                if error:
                    st.error(f"Erro ao carregar arquivo target: {error}")
                else:
                    salvar_no_banco(df_target, 'target', if_exists_mode)
                    st.session_state.df_target = df_target
                    with st.expander("👁️ Preview"):
                        st.dataframe(df_target.head())

    st.divider()

    # --- ARQUIVO DE NOTA ---
    st.subheader("📊 Arquivo de Nota (Zendesk)")
    uploaded_file_nota = st.file_uploader(
        "Carregar arquivo de Nota (CSV, Excel ou Parquet)",
        type=["csv", "xlsx", "xls", "parquet"],
        key="nota_upload",
        help="Arquivo com colunas: Nome do atribuído, Notas Atendente, CSAT"
    )

    if uploaded_file_nota:
        if st.button("🚀 Processar e Salvar Notas", type="primary", key="btn_notas"):
            with st.spinner("Processando..."):
                df_nota, error = load_file_target(uploaded_file_nota)
                if error:
                    st.error(f"❌ Erro: {error}")
                else:
                    colunas_necessarias = ['Nome do atribuído', 'Notas Atendente', 'CSAT']
                    colunas_faltando = [col for col in colunas_necessarias if col not in df_nota.columns]

                    if colunas_faltando:
                        st.error(f"❌ Colunas faltando: {', '.join(colunas_faltando)}")
                    else:
                        df_nota = df_nota.rename(columns={'Nome do atribuído': 'Nome_Agente', 'Notas Atendente': 'Notas_Atendente', 'CSAT': 'CSAT'})
                        df_nota = df_nota[df_nota['Nome_Agente'].notna() & (df_nota['Nome_Agente'] != '')]
                        df_nota['Nome_Agente'] = df_nota['Nome_Agente'].astype(str).str.strip().str.lower()
                        df_nota['Notas_Atendente'] = pd.to_numeric(df_nota['Notas_Atendente'], errors='coerce').fillna(0)
                        df_nota['CSAT'] = pd.to_numeric(df_nota['CSAT'], errors='coerce').fillna(0)

                        salvar_no_banco(df_nota, 'nota', if_exists_mode)
                        st.session_state.df_nota = df_nota
                        with st.expander("👁️ Preview"):
                            st.dataframe(df_nota.head())

    st.divider()

    # --- ARQUIVO DE DESEMPENHO ---
    st.subheader("📈 Arquivo de Desempenho (Genesys)")
    uploaded_file_perf = st.file_uploader(
        "Carregar arquivo de Desempenho (CSV, Excel ou Parquet)",
        type=["csv", "xlsx", "xls", "parquet"],
        key="desempenho_upload",
        help="Arquivo com colunas: Nome do agente, Atendidas, Conversação média, Transferidas, Conversa máx."
    )

    if uploaded_file_perf:
        if st.button("🚀 Processar e Salvar Desempenho", type="primary", key="btn_perf"):
            with st.spinner("Processando..."):
                df_perf, error = load_file_target(uploaded_file_perf)
                if error:
                    st.error(f"❌ Erro: {error}")
                else:
                    colunas_necessarias = ['Nome do agente', 'Atendidas', 'Conversação média', 'Transferidas', 'Conversa máx.']
                    colunas_faltando = [col for col in colunas_necessarias if col not in df_perf.columns]

                    if colunas_faltando:
                        st.error(f"❌ Colunas faltando: {', '.join(colunas_faltando)}")
                    else:
                        df_perf = df_perf.rename(columns={'Nome do agente': 'Nome_Agente', 'Atendidas': 'Atendidas', 'Conversação média': 'Conversacao_Media', 'Transferidas': 'Transferidas', 'Conversa máx.': 'Conversa_Max'})
                        df_perf = df_perf[df_perf['Nome_Agente'].notna() & (df_perf['Nome_Agente'] != '')]
                        df_perf['Nome_Agente'] = df_perf['Nome_Agente'].astype(str).str.strip().str.lower()
                        df_perf['TMA_Segundos'] = df_perf['Conversacao_Media'].apply(convert_duration_to_seconds)
                        df_perf['Conversa_Max_Segundos'] = df_perf['Conversa_Max'].apply(convert_duration_to_seconds)
                        df_perf['Atendidas'] = pd.to_numeric(df_perf['Atendidas'], errors='coerce').fillna(0).astype(int)
                        df_perf['Transferidas'] = pd.to_numeric(df_perf['Transferidas'], errors='coerce').fillna(0).astype(int)

                        salvar_no_banco(df_perf, 'desempenho', if_exists_mode)
                        st.session_state.df_desempenho = df_perf
                        with st.expander("👁️ Preview"):
                            st.dataframe(df_perf.head())

    st.divider()

    # --- ARQUIVO DE ATENDIMENTOS DETALHADOS ---
    st.subheader("📋 Arquivo de Atendimentos Detalhados")
    uploaded_file_atendimentos = st.file_uploader(
        "Carregar arquivo de Atendimentos (CSV, Excel ou Parquet)",
        type=["csv", "xlsx", "xls", "parquet"],
        key="atendimentos_upload",
        help="Arquivo com colunas: Duração, Usuários - Interagiram, Tipo de desconexão"
    )

    if uploaded_file_atendimentos:
        if st.button("🚀 Processar e Salvar Atendimentos", type="primary", key="btn_atend"):
            with st.spinner("Processando..."):
                df_atend, error = load_file_target(uploaded_file_atendimentos)
                if error:
                    st.error(f"❌ Erro: {error}")
                else:
                    def normalizar_nome_col(col):
                        col = str(col).replace('–', '-').replace('—', '-')
                        return ' '.join(col.split()).strip()

                    df_atend.rename(columns=lambda c: normalizar_nome_col(c), inplace=True)
                    colunas_necessarias = ['Duração', 'Usuários - Interagiram', 'Tipo de desconexão']
                    colunas_faltando = [c for c in colunas_necessarias if c not in df_atend.columns]

                    if colunas_faltando:
                        st.error(f"❌ Colunas faltando: {', '.join(colunas_faltando)}")
                    else:
                        df_atend = df_atend.rename(columns={'Usuários - Interagiram': 'Nome_Agente', 'Duração': 'Duracao', 'Tipo de desconexão': 'Tipo_Desconexao'})
                        df_atend['Nome_Agente'] = df_atend['Nome_Agente'].astype(str).str.strip().str.lower()
                        df_atend = df_atend[df_atend['Nome_Agente'].notna() & (df_atend['Nome_Agente'] != '') & (df_atend['Nome_Agente'] != 'nan')]
                        df_atend['duracao_segundos'] = df_atend['Duracao'].apply(convert_duration_to_seconds)
                        df_atend['Tipo_Desconexao'] = df_atend['Tipo_Desconexao'].astype(str).str.strip().str.lower()
                        df_atend['desconexao_agente'] = df_atend['Tipo_Desconexao'] == 'agente'

                        salvar_no_banco(df_atend, 'atendimentos', if_exists_mode)
                        st.session_state.df_atendimentos = df_atend
                        with st.expander("👁️ Preview"):
                            st.dataframe(df_atend.head())
