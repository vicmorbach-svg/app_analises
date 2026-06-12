import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine
import warnings

warnings.filterwarnings('ignore')

# --- INJEÇÃO SEGURA DOS SEGREDOS (RAILWAY) ---
# Lê a variável de ambiente e cria o arquivo TOML nativamente pelo Python
if "STREAMLIT_SECRETS" in os.environ:
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write(os.environ["STREAMLIT_SECRETS"])

# --- CONFIGURAÇÃO DO BANCO DE DADOS (POSTGRESQL) ---
# O Railway fornece a URL, garantimos que comece com postgresql:// para o SQLAlchemy
db_url = os.environ.get("DATABASE_URL", "")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url) if db_url else None

st.set_page_config(page_title="Sistema de Análise de Call Center", page_icon="📞", layout="wide")

# Importar tabs
from tabs import upload_tab, rechamadas_tab, motivos_tab, agentes_tab, mailing_tab, ranking_tab


# --- SISTEMA DE LOGIN ---
def check_password():
    def password_entered():
        user = st.session_state["username"]
        pwd = st.session_state["password"]
        if user in st.secrets["passwords"] and pwd == st.secrets["passwords"][user]:
            st.session_state["password_correct"] = True
            st.session_state["role"] = st.secrets["roles"][user]
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Login - Call Center Analytics")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 Login - Call Center Analytics")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar", on_click=password_entered)
        st.error("Usuário ou senha incorretos")
        return False
    return True

if check_password():
    # --- CARREGAMENTO E FILTRO GLOBAL DE DADOS ---
    st.sidebar.header("📅 Filtro Global")

    if engine:
        try:
            # Carrega os dados persistidos do PostgreSQL
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

                # Aplica o filtro
                mask = (df_chamadas_full['datetime'].dt.date >= data_inicio) & (df_chamadas_full['datetime'].dt.date <= data_fim)
                st.session_state.df_chamadas = df_chamadas_full[mask]
            else:
                st.session_state.df_chamadas = None
                st.sidebar.info("Nenhum dado de chamadas no banco.")

        except Exception as e:
            st.sidebar.warning("Banco de dados vazio ou erro de conexão. Faça o upload.")
            if 'df_chamadas' not in st.session_state: st.session_state.df_chamadas = None
    else:
        st.sidebar.error("Variável DATABASE_URL não configurada no Railway.")

    # Inicializa os outros states necessários
    for state in ['df_target', 'df_tma', 'df_desliga', 'df_nota', 'df_desempenho', 'df_atendimentos', 'rechamadas_detalhe', 'rechamadas_result', 'df_final_motivos', 'df_ranking', 'df_mailing_list']:
        if state not in st.session_state:
            st.session_state[state] = None

    st.title("📊 Sistema de Análise de Call Center")
    st.sidebar.write(f"👤 Perfil: **{st.session_state['role'].upper()}**")

    # --- CONTROLE DE ACESSO ÀS ABAS ---
    if st.session_state["role"] == "admin":
        tabs = st.tabs(["📁 Upload", "📞 Rechamadas", "🔍 Motivos", "👥 Agentes", "🏆 Ranking", "📧 Mailing"])
        with tabs[0]: upload_tab.show()
        with tabs[1]: rechamadas_tab.show()
        with tabs[2]: motivos_tab.show()
        with tabs[3]: agentes_tab.show()
        with tabs[4]: ranking_tab.show()
        with tabs[5]: mailing_tab.show()
    else:
        # Usuário comum não vê a aba de Upload
        tabs = st.tabs(["📞 Rechamadas", "🔍 Motivos", "👥 Agentes", "🏆 Ranking", "📧 Mailing"])
        with tabs[0]: rechamadas_tab.show()
        with tabs[1]: motivos_tab.show()
        with tabs[2]: agentes_tab.show()
        with tabs[3]: ranking_tab.show()
        with tabs[4]: mailing_tab.show()
