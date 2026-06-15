import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine
import warnings

warnings.filterwarnings('ignore')

# --- INJEÇÃO SEGURA DOS SEGREDOS (RAILWAY) ---
# Mantido para garantir que o Railway não quebre as quebras de linha do TOML
if "STREAMLIT_SECRETS" in os.environ:
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write(os.environ["STREAMLIT_SECRETS"])

# Configuração da página
st.set_page_config(
    page_title="Sistema de Análise de Call Center",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SISTEMA DE LOGIN (SEU CÓDIGO) ---
def get_users():
    users = {}
    try:
        # Verifica se a seção [users] existe
        if "users" not in st.secrets:
            st.error("🚨 ERRO: A seção '[users]' não foi encontrada. Verifique a variável STREAMLIT_SECRETS no Railway.")
            return users

        secrets  = st.secrets["users"]
        prefixes = set()
        for key in secrets:
            if key.endswith("_user"):
                prefixes.add(key[:-5])

        for prefix in prefixes:
            username = secrets.get(f"{prefix}_user", "")
            password = secrets.get(f"{prefix}_password", "")
            role     = secrets.get(f"{prefix}_role", "user")
            if username:
                users[username] = {"password": password, "role": role}

        if not users:
            st.warning("🚨 A seção '[users]' existe, mas nenhum usuário foi carregado. O Railway pode ter desformatado o texto.")

    except Exception as e:
        st.error(f"🚨 Erro interno ao ler usuários: {e}")

    return users

def login_screen():
    st.title("🔐 Login")
    st.markdown("Faça login para acessar o sistema.")
    with st.form("login_form"):
        username  = st.text_input("Usuário")
        password  = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
    if submitted:
        users = get_users()
        if username in users and str(users[username]["password"]) == str(password):
            st.session_state["logged_in"] = True
            st.session_state["username"]  = username
            st.session_state["role"]      = users[username]["role"]
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

def is_admin():
    return st.session_state.get("role") == "admin"

def logout():
    st.session_state.clear()
    st.rerun()

# --- FLUXO PRINCIPAL DA APLICAÇÃO ---
if not st.session_state.get("logged_in"):
    login_screen()
else:
    # Importar tabs apenas se estiver logado
    try:
        from tabs import upload_tab, rechamadas_tab, motivos_tab, agentes_tab, mailing_tab, ranking_tab
    except ImportError as e:
        st.error(f"❌ Erro ao importar tabs: {e}")
        st.stop()

    # --- CONFIGURAÇÃO DO BANCO DE DADOS (POSTGRESQL) ---
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(db_url) if db_url else None

    # Inicialização do session_state para os dados
    states = ['df_chamadas', 'df_target', 'df_tma', 'df_desliga', 'df_nota', 
              'rechamadas_detalhe', 'rechamadas_result', 'df_final_motivos', 
              'operator_performance', 'df_mailing_list', 'df_desempenho', 'df_atendimentos', 'df_ranking']
    for state in states:
        if state not in st.session_state:
            st.session_state[state] = None

    # --- BARRA LATERAL (INFO DO USUÁRIO E FILTRO) ---
    st.sidebar.write(f"👤 Usuário: **{st.session_state['username']}**")
    st.sidebar.write(f"🔑 Perfil: **{st.session_state['role'].upper()}**")
    st.sidebar.button("Sair", on_click=logout)
    st.sidebar.divider()

    st.sidebar.header("📅 Filtro Global")

    if engine:
        # 1. Carrega e filtra a tabela principal (Chamadas)
        try:
            df_chamadas_full = pd.read_sql('SELECT * FROM chamadas', engine, parse_dates=['datetime'])

            if not df_chamadas_full.empty:
                min_date = df_chamadas_full['datetime'].min().date()
                max_date = df_chamadas_full['datetime'].max().date()

                data_inicio, data_fim = st.sidebar.date_input(
                    "Selecione o Período", 
                    [min_date, max_date],
                    min_value=min_date,
                    max_value=max_date
                )

                mask = (df_chamadas_full['datetime'].dt.date >= data_inicio) & (df_chamadas_full['datetime'].dt.date <= data_fim)
                st.session_state.df_chamadas = df_chamadas_full[mask]
            else:
                st.session_state.df_chamadas = None
                st.sidebar.info("Nenhum dado de chamadas no banco.")

        except Exception as e:
            st.sidebar.warning("Banco de dados vazio ou erro de conexão. Faça o upload.")
            if 'df_chamadas' not in st.session_state: st.session_state.df_chamadas = None

        # 2. Carrega as tabelas secundárias automaticamente para a sessão
        tabelas_secundarias = {
            'target': 'df_target',
            'nota': 'df_nota',
            'desempenho': 'df_desempenho',
            'atendimentos': 'df_atendimentos'
        }

        for tabela, state_key in tabelas_secundarias.items():
            if st.session_state.get(state_key) is None:
                try:
                    df_temp = pd.read_sql(f'SELECT * FROM {tabela}', engine)
                    if not df_temp.empty:
                        st.session_state[state_key] = df_temp
                except Exception:
                    pass # A tabela pode ainda não existir no banco, o que é normal
    else:
        st.sidebar.error("Variável DATABASE_URL não configurada no Railway.")

    # Título
    st.title("📊 Sistema de Análise de Call Center")

    # --- CONTROLE DE ACESSO ÀS ABAS ---
    if is_admin():
        tabs = st.tabs([
            "📁 Upload de Arquivos",
            "📞 Análise de Rechamadas",
            "🔍 Motivos de Rechamadas",
            "👥 Desempenho de Agentes",
            "🏆 Ranking",
            "📧 Lista para Mailing"
        ])
        with tabs[0]: upload_tab.show()
        with tabs[1]: rechamadas_tab.show()
        with tabs[2]: motivos_tab.show()
        with tabs[3]: agentes_tab.show()
        with tabs[4]: ranking_tab.show()
        with tabs[5]: mailing_tab.show()
    else:
        # Usuário comum não vê a aba de Upload (índice 0 removido)
        tabs = st.tabs([
            "📞 Análise de Rechamadas",
            "🔍 Motivos de Rechamadas",
            "👥 Desempenho de Agentes",
            "🏆 Ranking",
            "📧 Lista para Mailing"
        ])
        with tabs[0]: rechamadas_tab.show()
        with tabs[1]: motivos_tab.show()
        with tabs[2]: agentes_tab.show()
        with tabs[3]: ranking_tab.show()
        with tabs[4]: mailing_tab.show()
