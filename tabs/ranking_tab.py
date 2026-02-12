import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt
from datetime import datetime
from utils.visualization import set_style, plot_bar_chart
from utils.data_loader import convert_duration_to_seconds

def normalizar_metrica(serie, inverter=False):
    """Normaliza métrica para escala 0-100. Se inverter=True, menor valor = melhor."""
    if serie.max() == serie.min():
        return pd.Series([50] * len(serie), index=serie.index)

    if inverter:
        # Menor valor = 100, maior valor = 0
        normalized = 100 - ((serie - serie.min()) / (serie.max() - serie.min()) * 100)
    else:
        # Maior valor = 100, menor valor = 0
        normalized = ((serie - serie.min()) / (serie.max() - serie.min()) * 100)

    return normalized

def show():
    set_style()
    st.header("🏆 Ranking de Desempenho dos Agentes")

    # ============================================================
    # 1. VERIFICAÇÃO DE ARQUIVOS
    # ============================================================
    arquivos_faltando = []
    if st.session_state.get('df_nota') is None:
        arquivos_faltando.append("Arquivo de Nota")
    if st.session_state.get('df_desempenho') is None:
        arquivos_faltando.append("Arquivo de Desempenho")
    if st.session_state.get('df_atendimentos') is None:
        arquivos_faltando.append("Arquivo de Atendimentos")

    if arquivos_faltando:
        st.warning(f"⚠️ Arquivos não carregados: {', '.join(arquivos_faltando)}")
        st.info("Faça o upload na aba 'Upload de Arquivos'")
        return

    # ============================================================
    # 2. CONFIGURAÇÃO DE LIMITES DE TEMPO
    # ============================================================
    st.subheader("⚙️ Configuração de Limites de Tempo")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        t_min_input = st.text_input(
            "T Min (formato mm:ss ou segundos)",
            value="00:30",
            help="Tempo mínimo ideal de atendimento"
        )
    with col_t2:
        t_max_input = st.text_input(
            "T Max (formato mm:ss ou segundos)",
            value="05:00",
            help="Tempo máximo ideal de atendimento"
        )

    # Converte para segundos
    t_min = convert_duration_to_seconds(t_min_input)
    t_max = convert_duration_to_seconds(t_max_input)

    st.info(f"📊 T Min: {t_min}s ({t_min/60:.1f} min) | T Max: {t_max}s ({t_max/60:.1f} min)")

    # ============================================================
    # 3. CONFIGURAÇÃO DE PESOS
    # ============================================================
    st.subheader("⚖️ Configuração de Pesos dos Indicadores")

    st.write("**Defina o peso de cada indicador (0 = não considerar):**")

    col_p1, col_p2 = st.columns(2)

    with col_p1:
        usar_tma = st.checkbox("Usar TMA (Tempo Médio de Atendimento)", value=True, key="usar_tma")
        peso_tma = st.slider(
            "Peso TMA (menor é melhor)",
            0.0, 1.0, 0.20, 0.05,
            disabled=not usar_tma,
            key="peso_tma"
        ) if usar_tma else 0.0

        usar_csat = st.checkbox("Usar CSAT", value=True, key="usar_csat")
        peso_csat = st.slider(
            "Peso CSAT (maior é melhor)",
            0.0, 1.0, 0.30, 0.05,
            disabled=not usar_csat,
            key="peso_csat"
        ) if usar_csat else 0.0

        usar_encaminhamento = st.checkbox("Usar % Encaminhamento para Pesquisa", value=True, key="usar_enc")
        peso_encaminhamento = st.slider(
            "Peso % Encaminhamento Pesquisa (maior é melhor)",
            0.0, 1.0, 0.15, 0.05,
            disabled=not usar_encaminhamento,
            key="peso_enc"
        ) if usar_encaminhamento else 0.0

    with col_p2:
        usar_desconexoes = st.checkbox("Usar Desconexões pelo Agente", value=True, key="usar_desc")
        peso_desconexoes = st.slider(
            "Peso Desconexões (menor é melhor)",
            0.0, 1.0, 0.20, 0.05,
            disabled=not usar_desconexoes,
            key="peso_desc"
        ) if usar_desconexoes else 0.0

        usar_acima_tmax = st.checkbox("Usar % Acima de T Max", value=True, key="usar_tmax")
        peso_acima_tmax = st.slider(
            "Peso % Acima T Max (menor é melhor)",
            0.0, 1.0, 0.15, 0.05,
            disabled=not usar_acima_tmax,
            key="peso_tmax"
        ) if usar_acima_tmax else 0.0

    # Calcula total de pesos
    total_pesos = peso_tma + peso_csat + peso_encaminhamento + peso_desconexoes + peso_acima_tmax

    if total_pesos == 0:
        st.error("❌ Selecione pelo menos um indicador com peso maior que zero!")
        return

    # Normaliza pesos
    pesos_normalizados = {
        'TMA': peso_tma / total_pesos,
        'CSAT': peso_csat / total_pesos,
        'Encaminhamento_Pesquisa': peso_encaminhamento / total_pesos,
        'Desconexoes': peso_desconexoes / total_pesos,
        'Acima_TMax': peso_acima_tmax / total_pesos
    }

    st.write("**Pesos Normalizados:**")
    df_pesos = pd.DataFrame([pesos_normalizados]).T
    df_pesos.columns = ['Peso (%)']
    df_pesos['Peso (%)'] = (df_pesos['Peso (%)'] * 100).round(1)
    st.dataframe(df_pesos)

    # ============================================================
    # 4. GERAR RANKING
    # ============================================================
    if st.button("🏆 Gerar Ranking de Desempenho", type="primary"):
        with st.spinner("Calculando ranking..."):
            df_nota = st.session_state.df_nota.copy()
            df_perf = st.session_state.df_desempenho.copy()
            df_atend = st.session_state.df_atendimentos.copy()

            # Normaliza nomes
            df_nota['Nome_Agente'] = df_nota['Nome_Agente'].astype(str).str.strip().str.lower()
            df_perf['Nome_Agente'] = df_perf['Nome_Agente'].astype(str).str.strip().str.lower()
            df_atend['Nome_Agente'] = df_atend['Nome_Agente'].astype(str).str.strip().str.lower()

            # ========================================================
            # 4.1 CONSOLIDAR DADOS BASE (Nota + Desempenho)
            # ========================================================
            df_ranking = pd.merge(df_perf, df_nota, on='Nome_Agente', how='outer')

            # ========================================================
            # 4.2 CALCULAR MÉTRICAS DO ARQUIVO DE ATENDIMENTOS
            # ========================================================
            # Garante que a coluna de flag exista
            if 'desconexao_agente' not in df_atend.columns:
                df_atend['desconexao_agente'] = False

            metricas_atend = df_atend.groupby('Nome_Agente').agg(
                total_atendimentos=('Nome_Agente', 'count'),
                acima_tmax=('duracao_segundos', lambda x: (x > t_max).sum()),
                abaixo_tmin=('duracao_segundos', lambda x: (x < t_min).sum()),
                desconexoes_agente=('desconexao_agente', 'sum')
            ).reset_index()

            # Calcula percentuais
            metricas_atend['perc_acima_tmax'] = (metricas_atend['acima_tmax'] / metricas_atend['total_atendimentos'] * 100).fillna(0)
            metricas_atend['perc_abaixo_tmin'] = (metricas_atend['abaixo_tmin'] / metricas_atend['total_atendimentos'] * 100).fillna(0)
            metricas_atend['perc_desconexoes'] = (metricas_atend['desconexoes_agente'] / metricas_atend['total_atendimentos'] * 100).fillna(0)

            # ========================================================
            # 4.3 MERGE COM RANKING
            # ========================================================
            df_ranking = pd.merge(df_ranking, metricas_atend, on='Nome_Agente', how='left')

            # ========================================================
            # 4.4 REMOVE AGENTES SEM ATENDIMENTOS
            # ========================================================
            df_ranking['Atendidas'] = pd.to_numeric(df_ranking['Atendidas'], errors='coerce').fillna(0)
            df_ranking = df_ranking[df_ranking['Atendidas'] > 0].copy()

            # Preenche NaN
            df_ranking = df_ranking.fillna(0)

            # ========================================================
            # 4.5 CALCULA PERCENTUAL DE ENCAMINHAMENTO PARA PESQUISA
            # ========================================================
            df_ranking['Transferidas'] = pd.to_numeric(df_ranking['Transferidas'], errors='coerce').fillna(0)
            df_ranking['Perc_Encaminhamento_Pesquisa'] = (
                (df_ranking['Transferidas'] / df_ranking['Atendidas']) * 100
            ).fillna(0).round(2)
            df_ranking['Perc_Encaminhamento_Pesquisa'] = df_ranking['Perc_Encaminhamento_Pesquisa'].clip(upper=100)

            # ========================================================
            # 4.6 CONVERTE TMA PARA MINUTOS
            # ========================================================
            if 'TMA_Segundos' in df_ranking.columns:
                df_ranking['TMA_Minutos'] = (df_ranking['TMA_Segundos'] / 60).round(2)
            else:
                df_ranking['TMA_Minutos'] = 0

            if 'Conversa_Max_Segundos' in df_ranking.columns:
                df_ranking['Conversa_Max_Minutos'] = (df_ranking['Conversa_Max_Segundos'] / 60).round(2)
            else:
                df_ranking['Conversa_Max_Minutos'] = 0

            # ========================================================
            # 4.7 NORMALIZA MÉTRICAS (0-100)
            # ========================================================
            if usar_tma and 'TMA_Segundos' in df_ranking.columns:
                df_ranking['TMA_Score'] = normalizar_metrica(df_ranking['TMA_Segundos'], inverter=True)
            else:
                df_ranking['TMA_Score'] = 0

            if usar_csat and 'CSAT' in df_ranking.columns:
                df_ranking['CSAT_Score'] = normalizar_metrica(df_ranking['CSAT'], inverter=False)
            else:
                df_ranking['CSAT_Score'] = 0

            if usar_encaminhamento and 'Perc_Encaminhamento_Pesquisa' in df_ranking.columns:
                # MAIOR % de encaminhamento = MELHOR
                df_ranking['Encaminhamento_Pesquisa_Score'] = normalizar_metrica(
                    df_ranking['Perc_Encaminhamento_Pesquisa'],
                    inverter=False
                )
            else:
                df_ranking['Encaminhamento_Pesquisa_Score'] = 0

            if usar_desconexoes:
                df_ranking['Desconexoes_Score'] = normalizar_metrica(df_ranking['perc_desconexoes'], inverter=True)
            else:
                df_ranking['Desconexoes_Score'] = 0

            if usar_acima_tmax:
                df_ranking['AcimaTMax_Score'] = normalizar_metrica(df_ranking['perc_acima_tmax'], inverter=True)
            else:
                df_ranking['AcimaTMax_Score'] = 0

            # ========================================================
            # 4.8 CALCULA SCORE FINAL
            # ========================================================
            df_ranking['Score_Final'] = (
                df_ranking['TMA_Score'] * pesos_normalizados['TMA'] +
                df_ranking['CSAT_Score'] * pesos_normalizados['CSAT'] +
                df_ranking['Encaminhamento_Pesquisa_Score'] * pesos_normalizados['Encaminhamento_Pesquisa'] +
                df_ranking['Desconexoes_Score'] * pesos_normalizados['Desconexoes'] +
                df_ranking['AcimaTMax_Score'] * pesos_normalizados['Acima_TMax']
            )

            # ========================================================
            # 4.9 GERA RANKING
            # ========================================================
            df_ranking['Posicao'] = df_ranking['Score_Final'].rank(ascending=False, method='min').astype(int)
            df_ranking = df_ranking.sort_values('Posicao')

            # Salva no session_state
            st.session_state.df_ranking = df_ranking
            st.success(f"✅ Ranking gerado com {len(df_ranking)} agentes!")

    # ============================================================
    # 5. EXIBIÇÃO DO RANKING
    # ============================================================
    if st.session_state.get('df_ranking') is not None:
        df_ranking = st.session_state.df_ranking

        st.subheader("🏆 Ranking de Desempenho")

        # Métricas gerais
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Total de Agentes", len(df_ranking))
        with col_m2:
            st.metric("Score Médio", f"{df_ranking['Score_Final'].mean():.1f}")
        with col_m3:
            st.metric("Melhor Score", f"{df_ranking['Score_Final'].max():.1f}")

        # ========================================================
        # 5.1 TABELA DE RANKING
        # ========================================================
        colunas_desejadas = [
            'Posicao',
            'Nome_Agente',
            'Score_Final',
            'Atendidas',
            'TMA_Minutos',
            'CSAT',
            'Perc_Encaminhamento_Pesquisa',
            'perc_desconexoes',
            'perc_acima_tmax',
            'perc_abaixo_tmin'
        ]

        # Filtra apenas as que existem
        colunas_disponiveis = [col for col in colunas_desejadas if col in df_ranking.columns]

        df_display = df_ranking[colunas_disponiveis].copy()

        # Renomeia
        rename_map = {
            'Posicao': 'Rank',
            'Nome_Agente': 'Agente',
            'Score_Final': 'Score',
            'Atendidas': 'Atendidas',
            'TMA_Minutos': 'TMA (min)',
            'CSAT': 'CSAT',
            'Perc_Encaminhamento_Pesquisa': '% Encaminhamentos Pesquisa',
            'perc_desconexoes': 'Desconex. (%)',
            'perc_acima_tmax': 'Acima TMax (%)',
            'perc_abaixo_tmin': 'Abaixo TMin (%)'
        }

        df_display = df_display.rename(columns={k: v for k, v in rename_map.items() if k in df_display.columns})

        # Formata nome do agente
        if 'Agente' in df_display.columns:
            df_display['Agente'] = df_display['Agente'].str.title()

        # Formata números
        if 'Score' in df_display.columns:
            df_display['Score'] = df_display['Score'].round(1)
        if 'TMA (min)' in df_display.columns:
            df_display['TMA (min)'] = df_display['TMA (min)'].round(1)
        if 'CSAT' in df_display.columns:
            df_display['CSAT'] = df_display['CSAT'].round(2)
        if '% Encaminhamentos Pesquisa' in df_display.columns:
            df_display['% Encaminhamentos Pesquisa'] = df_display['% Encaminhamentos Pesquisa'].round(1)
        if 'Desconex. (%)' in df_display.columns:
            df_display['Desconex. (%)'] = df_display['Desconex. (%)'].round(1)
        if 'Acima TMax (%)' in df_display.columns:
            df_display['Acima TMax (%)'] = df_display['Acima TMax (%)'].round(1)
        if 'Abaixo TMin (%)' in df_display.columns:
            df_display['Abaixo TMin (%)'] = df_display['Abaixo TMin (%)'].round(1)

        st.dataframe(df_display, use_container_width=True, height=400)

        # ========================================================
        # 5.2 GRÁFICOS
        # ========================================================
        st.subheader("📊 Análises Visuais")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            top15 = df_ranking.head(15).copy()
            top15['Nome_Agente'] = top15['Nome_Agente'].str.title()
            fig1, ax1 = plot_bar_chart(
                data=top15,
                x='Score_Final',
                y='Nome_Agente',
                title='Top 15 - Score Final',
                color='#2ecc71',
                figsize=(10, 8),
                is_horizontal=True
            )
            st.pyplot(fig1)

        with col_g2:
            bottom15 = df_ranking.tail(15).sort_values('Score_Final').copy()
            bottom15['Nome_Agente'] = bottom15['Nome_Agente'].str.title()
            fig2, ax2 = plot_bar_chart(
                data=bottom15,
                x='Score_Final',
                y='Nome_Agente',
                title='Bottom 15 - Score Final',
                color='#e74c3c',
                figsize=(10, 8),
                is_horizontal=True
            )
            st.pyplot(fig2)

        # ========================================================
        # 5.3 DOWNLOAD
        # ========================================================
        st.subheader("📥 Download")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # Aba 1: Ranking completo
            df_export = df_display.copy()
            df_export.to_excel(writer, sheet_name='Ranking', index=False)

            # Aba 2: Scores detalhados
            colunas_scores_desejadas = [
                'Nome_Agente', 
                'Posicao', 
                'Score_Final',
                'TMA_Score', 
                'CSAT_Score', 
                'Encaminhamento_Pesquisa_Score',
                'Desconexoes_Score', 
                'AcimaTMax_Score'
            ]

            colunas_scores_disponiveis = [col for col in colunas_scores_desejadas if col in df_ranking.columns]
            df_scores = df_ranking[colunas_scores_disponiveis].copy()
            df_scores['Nome_Agente'] = df_scores['Nome_Agente'].str.title()
            df_scores.to_excel(writer, sheet_name='Scores_Detalhados', index=False)

        buffer.seek(0)

        st.download_button(
            "📥 Baixar Ranking Completo",
            data=buffer,
            file_name=f"ranking_agentes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
