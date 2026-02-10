import streamlit as st
import pandas as pd
import io
from datetime import datetime
from utils.visualization import set_style, plot_bar_chart

def show():
    set_style()
    st.header("👥 Desempenho de Agentes")

    # ============================================================
    # 1. VERIFICAÇÃO DE ARQUIVOS CARREGADOS
    # ============================================================
    if st.session_state.get('df_nota') is None:
        st.warning("⚠️ Arquivo de Nota não carregado. Faça o upload na aba 'Upload de Arquivos'.")
        return

    if st.session_state.get('df_desempenho') is None:
        st.warning("⚠️ Arquivo de Desempenho não carregado. Faça o upload na aba 'Upload de Arquivos'.")
        return

    df_nota = st.session_state.df_nota.copy()
    df_perf = st.session_state.df_desempenho.copy()

    # Garantia extra: normaliza nomes novamente (case-insensitive)
    df_nota['Nome_Agente'] = df_nota['Nome_Agente'].astype(str).str.strip().str.lower()
    df_perf['Nome_Agente'] = df_perf['Nome_Agente'].astype(str).str.strip().str.lower()

    # ============================================================
    # 2. CONSOLIDAÇÃO DOS DADOS
    # ============================================================
    if st.button("🔄 Consolidar Dados dos Agentes", type="primary"):
        with st.spinner("Consolidando dados..."):
            # Merge usando Nome_Agente como chave (case-insensitive)
            df_consolidado = pd.merge(
                df_perf,
                df_nota,
                on='Nome_Agente',
                how='outer'
            )

            # Preenche valores faltantes
            df_consolidado = df_consolidado.fillna({
                'Atendidas': 0,
                'TMA_Segundos': 0,
                'Transferidas': 0,
                'Conversa_Max_Segundos': 0,
                'Notas_Atendente': 0,
                'CSAT': 0
            })

            # ========================================================
            # 2.1 EXCLUSÃO DE AGENTES SEM ATENDIMENTOS
            # ========================================================
            antes_exclusao = len(df_consolidado)

            # Converte para numérico e remove zeros/nulls
            df_consolidado['Atendidas'] = pd.to_numeric(df_consolidado['Atendidas'], errors='coerce')
            df_consolidado = df_consolidado[df_consolidado['Atendidas'] > 0].copy()

            depois_exclusao = len(df_consolidado)
            agentes_excluidos = antes_exclusao - depois_exclusao

            if agentes_excluidos > 0:
                st.warning(f"⚠️ {agentes_excluidos} agentes foram excluídos por não terem atendimentos (Atendidas = 0 ou null)")

            # ========================================================
            # 2.2 CÁLCULO DAS MÉTRICAS DERIVADAS
            # ========================================================

            # Converte TMA de segundos para minutos
            df_consolidado['TMA_Minutos'] = (df_consolidado['TMA_Segundos'] / 60).round(2)

            # Converte Conversa_Max de segundos para minutos
            df_consolidado['Conversa_Max_Minutos'] = (df_consolidado['Conversa_Max_Segundos'] / 60).round(2)

            # ========================================================
            # 2.3 CÁLCULO CORRETO DO ENCAMINHAMENTO PARA PESQUISA
            # ========================================================
            # Garante que Transferidas seja numérico
            df_consolidado['Transferidas'] = pd.to_numeric(
                df_consolidado['Transferidas'], 
                errors='coerce'
            ).fillna(0)

            # Calcula o percentual de encaminhamento para pesquisa
            df_consolidado['Perc_Encaminhamento_Pesquisa'] = (
                (df_consolidado['Transferidas'] / df_consolidado['Atendidas']) * 100
            ).fillna(0).round(2)

            # Garante que não ultrapasse 100%
            df_consolidado['Perc_Encaminhamento_Pesquisa'] = df_consolidado['Perc_Encaminhamento_Pesquisa'].clip(upper=100)

            # Ordena por CSAT (maior para menor)
            df_consolidado = df_consolidado.sort_values('CSAT', ascending=False)

            # Salva no session_state
            st.session_state.df_agentes_consolidado = df_consolidado
            st.success(f"✅ Dados consolidados! {len(df_consolidado)} agentes ativos.")

    # ============================================================
    # 3. EXIBIÇÃO DOS RESULTADOS
    # ============================================================
    if st.session_state.get('df_agentes_consolidado') is not None:
        df_consolidado = st.session_state.df_agentes_consolidado

        st.subheader("📊 Métricas Gerais")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de Agentes Ativos", f"{len(df_consolidado)}")

        with col2:
            total_atendidas = df_consolidado['Atendidas'].sum()
            st.metric("Total Atendidas", f"{total_atendidas:,.0f}")

        with col3:
            csat_medio = df_consolidado['CSAT'].mean()
            st.metric("CSAT Médio", f"{csat_medio:.2f}")

        with col4:
            tma_medio = df_consolidado['TMA_Minutos'].mean()
            st.metric("TMA Médio", f"{tma_medio:.1f} min")

        # ========================================================
        # 3.1 MÉTRICAS DE ENCAMINHAMENTO PARA PESQUISA
        # ========================================================
        st.subheader("📋 Métricas de Encaminhamento para Pesquisa")

        col_enc1, col_enc2, col_enc3 = st.columns(3)

        with col_enc1:
            total_transferidas = df_consolidado['Transferidas'].sum()
            st.metric("Total de Encaminhamentos", f"{total_transferidas:,.0f}")

        with col_enc2:
            perc_medio_enc = df_consolidado['Perc_Encaminhamento_Pesquisa'].mean()
            st.metric("% Médio de Encaminhamento", f"{perc_medio_enc:.1f}%")

        with col_enc3:
            agentes_acima_50 = len(df_consolidado[df_consolidado['Perc_Encaminhamento_Pesquisa'] >= 50])
            st.metric("Agentes com ≥50% Encaminhamento", f"{agentes_acima_50}")

        # ========================================================
        # 3.2 TABELA CONSOLIDADA
        # ========================================================
        st.subheader("📋 Dados Consolidados")

        df_display = df_consolidado[[
            'Nome_Agente',
            'Atendidas',
            'TMA_Minutos',
            'Transferidas',
            'Perc_Encaminhamento_Pesquisa',
            'Conversa_Max_Minutos',
            'Notas_Atendente',
            'CSAT'
        ]].copy()

        # Renomeia colunas para exibição
        df_display = df_display.rename(columns={
            'Nome_Agente': 'Agente',
            'Atendidas': 'Atendidas',
            'TMA_Minutos': 'TMA (min)',
            'Transferidas': 'Qtd Encaminhamentos',
            'Perc_Encaminhamento_Pesquisa': '% Encaminhamento Pesquisa',
            'Conversa_Max_Minutos': 'Conversa Máx (min)',
            'Notas_Atendente': 'Nota Atendente',
            'CSAT': 'CSAT'
        })

        # Formata a coluna do agente para exibição (primeira letra maiúscula)
        df_display['Agente'] = df_display['Agente'].str.title()

        st.dataframe(df_display, use_container_width=True)

        # ========================================================
        # 3.3 GRÁFICOS DE ANÁLISE
        # ========================================================
        st.subheader("📈 Análises Visuais")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            # Top 15 por CSAT
            top_csat = df_consolidado.nlargest(15, 'CSAT')
            top_csat_display = top_csat.copy()
            top_csat_display['Nome_Agente'] = top_csat_display['Nome_Agente'].str.title()

            fig1, ax1 = plot_bar_chart(
                data=top_csat_display,
                x='CSAT',
                y='Nome_Agente',
                title='Top 15 - CSAT',
                color='#2ecc71',
                figsize=(10, 8),
                is_horizontal=True
            )
            st.pyplot(fig1)

        with col_g2:
            # Top 15 por Atendidas
            top_atendidas = df_consolidado.nlargest(15, 'Atendidas')
            top_atendidas_display = top_atendidas.copy()
            top_atendidas_display['Nome_Agente'] = top_atendidas_display['Nome_Agente'].str.title()

            fig2, ax2 = plot_bar_chart(
                data=top_atendidas_display,
                x='Atendidas',
                y='Nome_Agente',
                title='Top 15 - Atendidas',
                color='#3498db',
                figsize=(10, 8),
                is_horizontal=True
            )
            st.pyplot(fig2)

        # ========================================================
        # 3.4 GRÁFICO DE ENCAMINHAMENTO PARA PESQUISA
        # ========================================================
        st.subheader("📊 Encaminhamento para Pesquisa")

        col_g3, col_g4 = st.columns(2)

        with col_g3:
            # Top 15 por % de encaminhamento
            top_enc = df_consolidado.nlargest(15, 'Perc_Encaminhamento_Pesquisa')
            top_enc_display = top_enc.copy()
            top_enc_display['Nome_Agente'] = top_enc_display['Nome_Agente'].str.title()

            fig3, ax3 = plot_bar_chart(
                data=top_enc_display,
                x='Perc_Encaminhamento_Pesquisa',
                y='Nome_Agente',
                title='Top 15 - % Encaminhamento Pesquisa',
                color='#f39c12',
                figsize=(10, 8),
                is_horizontal=True
            )
            st.pyplot(fig3)

        with col_g4:
            # Top 15 por quantidade de encaminhamentos
            top_qtd_enc = df_consolidado.nlargest(15, 'Transferidas')
            top_qtd_enc_display = top_qtd_enc.copy()
            top_qtd_enc_display['Nome_Agente'] = top_qtd_enc_display['Nome_Agente'].str.title()

            fig4, ax4 = plot_bar_chart(
                data=top_qtd_enc_display,
                x='Transferidas',
                y='Nome_Agente',
                title='Top 15 - Quantidade de Encaminhamentos',
                color='#e67e22',
                figsize=(10, 8),
                is_horizontal=True
            )
            st.pyplot(fig4)

        # ========================================================
        # 3.5 TMA
        # ========================================================
        st.subheader("⏱️ Tempo Médio de Atendimento")

        top_tma = df_consolidado[df_consolidado['TMA_Minutos'] > 0].nsmallest(15, 'TMA_Minutos')

        if not top_tma.empty:
            top_tma_display = top_tma.copy()
            top_tma_display['Nome_Agente'] = top_tma_display['Nome_Agente'].str.title()

            fig5, ax5 = plot_bar_chart(
                data=top_tma_display,
                x='TMA_Minutos',
                y='Nome_Agente',
                title='Top 15 - Menor TMA',
                color='#9b59b6',
                figsize=(10, 8),
                is_horizontal=True
            )
            st.pyplot(fig5)
        else:
            st.info("Nenhum agente com TMA válido para exibir.")

        # ========================================================
        # 3.6 DOWNLOAD DOS RESULTADOS
        # ========================================================
        st.subheader("📥 Download")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # Aba 1: Dados consolidados
            df_export = df_consolidado.copy()
            df_export['Nome_Agente'] = df_export['Nome_Agente'].str.title()
            df_export.to_excel(writer, sheet_name='Desempenho_Agentes', index=False)

            # Aba 2: Resumo de encaminhamentos
            df_resumo_enc = df_consolidado[[
                'Nome_Agente',
                'Atendidas',
                'Transferidas',
                'Perc_Encaminhamento_Pesquisa'
            ]].copy()
            df_resumo_enc['Nome_Agente'] = df_resumo_enc['Nome_Agente'].str.title()
            df_resumo_enc = df_resumo_enc.sort_values('Perc_Encaminhamento_Pesquisa', ascending=False)
            df_resumo_enc.to_excel(writer, sheet_name='Encaminhamentos_Pesquisa', index=False)

        buffer.seek(0)

        st.download_button(
            "📥 Baixar Excel - Desempenho de Agentes",
            data=buffer,
            file_name=f"desempenho_agentes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
