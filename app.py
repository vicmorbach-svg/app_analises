import streamlit as st
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="Sistema de Análise de Call Center",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importar tabs
try:
    from tabs import upload_tab, rechamadas_tab, motivos_tab, agentes_tab, mailing_tab, ranking_tab
except ImportError as e:
    st.error(f"❌ Erro ao importar tabs: {e}")
    st.stop()

# Inicialização do session_state
if 'df_chamadas' not in st.session_state:
    st.session_state.df_chamadas = None
if 'df_target' not in st.session_state:
    st.session_state.df_target = None
if 'df_tma' not in st.session_state:
    st.session_state.df_tma = None
if 'df_desliga' not in st.session_state:
    st.session_state.df_desliga = None
if 'df_nota' not in st.session_state:
    st.session_state.df_nota = None
if 'rechamadas_detalhe' not in st.session_state:
    st.session_state.rechamadas_detalhe = None
if 'rechamadas_result' not in st.session_state:
    st.session_state.rechamadas_result = None
if 'df_final_motivos' not in st.session_state:
    st.session_state.df_final_motivos = None
if 'operator_performance' not in st.session_state:
    st.session_state.operator_performance = None
if 'df_mailing_list' not in st.session_state:
    st.session_state.df_mailing_list = None

# Título
st.title("📊 Sistema de Análise de Call Center")

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📁 Upload de Arquivos",
    "📞 Análise de Rechamadas",
    "🔍 Motivos de Rechamadas",
    "👥 Desempenho de Agentes",
    "🏆 Ranking",
    "📧 Lista para Mailing"
])

with tab1:
    upload_tab.show()

with tab2:
    rechamadas_tab.show()

with tab3:
    motivos_tab.show()

with tab4:
    agentes_tab.show()

with tab5:
    ranking_tab.show()

with tab6:
    mailing_tab.show()
