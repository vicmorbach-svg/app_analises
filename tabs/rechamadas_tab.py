import streamlit as st
import pandas as pd
import io
from datetime import datetime
from utils.data_loader import identificar_faixas_rechamada, faixas_ligacoes_e_reincidentes, calcular_impacto_financeiro # Importa as funções de análise
from utils.visualization import set_style, plot_bar_chart, plot_pie_chart, plot_histogram # Importa as funções de visualização

def show():
    set_style() # Aplicar estilo visual
    st.header("📞 Análise de Rechamadas")

    if st.session_state.get('df_chamadas') is None:
        st.warning("⚠️ Nenhum dado de chamadas carregado. Por favor, faça o upload do arquivo na aba 'Upload de Arquivos'.")
        return

    df = st.session_state.df_chamadas.copy()

    st.subheader("Configurações da Análise")

    # REMOVIDOS OS PARÂMETROS DE TEMPO, POIS OS INTERVALOS SÃO FIXOS (0-24h, 24-48h, 48-72h)
    valor_ligacao = st.number_input("Valor médio por ligação (para cálculo de impacto financeiro)", value=7.56, min_value=0.01, format="%.2f")
    min_ligacoes_graf = st.number_input("Mínimo de ligações para um telefone aparecer no gráfico de reincidência", value=2, min_value=1)

    if st.button("Executar Análise de Rechamadas"):
        with st.spinner("Processando análise de rechamadas..."):
            # 1. Identificar rechamadas
            rechamadas_detalhe = identificar_faixas_rechamada(df)
            st.session_state.rechamadas_detalhe = rechamadas_detalhe # Armazena para outras abas

            # 2. Faixas de ligações e reincidentes
            faixas_ligacoes, total_telefones_reincidentes, contagem_por_telefone = faixas_ligacoes_e_reincidentes(df)

            # 3. Clientes frequentes (mais de 1 ligação)
            clientes_frequentes_todos = contagem_por_telefone[contagem_por_telefone > 1].reset_index()
            clientes_frequentes_todos.columns = ['telefone', 'total_ligacoes']

            # 4. Impacto financeiro
            impacto_financeiro = calcular_impacto_financeiro(rechamadas_detalhe, valor_ligacao)

            # 5. Ligações por dia da semana
            df['dia_semana'] = df['datetime'].dt.dayofweek
            dias_semana_pt = {
                0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira',
                3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'
            }
            df['dia_semana_nome'] = df['dia_semana'].map(dias_semana_pt)
            ligacoes_por_dia = df['dia_semana_nome'].value_counts().reindex(dias_semana_pt.values(), fill_value=0)

            # 6. Horários de pico
            df['hora'] = df['datetime'].dt.hour
            horarios_pico = df['hora'].value_counts().sort_index()

            # 7. Consolidar resultados para exibição e download
            consolidado_results = {
                'total_ligacoes': len(df),
                'periodo_analise': f"{df['datetime'].min():%d/%m/%Y} a {df['datetime'].max():%d/%m/%Y}",
                'total_telefones_unicos': df['telefone'].nunique(),
                'total_rechamadas_identificadas': sum(len(v) for k, v in rechamadas_detalhe.items()),
                'impacto_financeiro_rechamadas': impacto_financeiro,
                'ligacoes_por_dia': ligacoes_por_dia,
                'horarios_pico': horarios_pico,
                'faixas_ligacoes': faixas_ligacoes,
                'total_telefones_reincidentes': total_telefones_reincidentes,
                'contagem_por_telefone': contagem_por_telefone,
                'clientes_frequentes_todos': clientes_frequentes_todos
            }
            st.session_state.rechamadas_result = consolidado_results
            st.success("✅ Análise de rechamadas concluída!")

    # Exibir resultados se a análise já foi executada
    if st.session_state.get('rechamadas_result') is not None:
        consolidado = st.session_state.rechamadas_result
        rechamadas_detalhe = st.session_state.rechamadas_detalhe
        contagem_por_telefone = consolidado['contagem_por_telefone']

        st.subheader("Resumo da Análise")
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Total de Ligações", f"{consolidado['total_ligacoes']:,}")
        with col2: st.metric("Telefones Únicos", f"{consolidado['total_telefones_unicos']:,}")
        with col3: st.metric("Rechamadas Identificadas", f"{consolidado['total_rechamadas_identificadas']:,}")
        st.metric("Impacto Financeiro das Rechamadas", f"R$ {consolidado['impacto_financeiro_rechamadas']:,.2f}")
        st.info(f"Período da análise: {consolidado['periodo_analise']}")

        st.subheader("Visualizações Detalhadas")

        # 1. Ligações por Dia da Semana
        st.write("#### Ligações por Dia da Semana")
        if not consolidado['ligacoes_por_dia'].empty:
            dias_ordenados = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
            ligacoes_dia_df = consolidado['ligacoes_por_dia'].reindex(dias_ordenados).reset_index()
            ligacoes_dia_df.columns = ['Dia da Semana', 'Quantidade']
            fig_dia, ax_dia = plot_bar_chart(
                data=ligacoes_dia_df,
                x='Dia da Semana',
                y='Quantidade',
                title='📅 Ligações por Dia da Semana',
                xlabel='Dia da Semana',
                ylabel='Quantidade de Ligações',
                color='skyblue',
                figsize=(10, 5)
            )
            ax_dia.tick_params(axis='x', rotation=45)
            st.pyplot(fig_dia)
        else:
            st.info("Dados de ligações por dia da semana não disponíveis para gráfico.")

        # 2. Horários de Pico (Top 5)
        st.write("#### Top 5 Horários de Pico")
        if not consolidado['horarios_pico'].empty:
            top_5_horarios = consolidado['horarios_pico'].nlargest(5).reset_index()
            top_5_horarios.columns = ['Hora', 'Quantidade']
            fig_hora, ax_hora = plot_bar_chart(
                data=top_5_horarios,
                x='Hora',
                y='Quantidade',
                title='🕐 Top 5 Horários de Pico',
                xlabel='Hora do Dia',
                ylabel='Quantidade de Ligações',
                color='lightgreen',
                figsize=(10, 5)
            )
            st.pyplot(fig_hora)
        else:
            st.info("Dados de horários de pico não disponíveis para gráfico.")

        # 3. Distribuição por Faixas de Ligações (Gráfico de Pizza)
        st.write("#### Distribuição por Faixas de Ligações")
        if consolidado['faixas_ligacoes']:
            faixas_df = pd.DataFrame(list(consolidado['faixas_ligacoes'].items()), columns=['Faixa', 'Quantidade'])
            col_table, col_chart = st.columns(2)
            with col_table:
                st.dataframe(faixas_df)
            with col_chart:
                fig_faixas_pie, ax_faixas_pie = plot_pie_chart(
                    data=faixas_df['Quantidade'],
                    labels=faixas_df['Faixa'],
                    title='Distribuição por Faixas de Ligações',
                    figsize=(8, 8)
                )
                st.pyplot(fig_faixas_pie)
        else:
            st.info("Dados de faixas de ligações não disponíveis para gráfico.")

        # 4. Histograma de Reincidência
        st.write(f"#### Reincidência (Telefones com ≥{min_ligacoes_graf} Ligações)")
        reincidentes_filtrados = contagem_por_telefone[contagem_por_telefone >= min_ligacoes_graf]
        if not reincidentes_filtrados.empty:
            fig_hist, ax_hist = plot_histogram(
                data=reincidentes_filtrados,
                bins=range(min_ligacoes_graf, reincidentes_filtrados.max() + 2),
                title=f'Distribuição de Telefones por Número de Ligações (≥{min_ligacoes_graf})',
                xlabel='Número de Ligações',
                ylabel='Quantidade de Telefones',
                color='navy',
                figsize=(10, 6)
            )
            st.pyplot(fig_hist)
        else:
            st.info(f"Nenhum telefone com {min_ligacoes_graf} ou mais ligações encontrado para o histograma.")

        # 5. Top 10 Clientes que Mais Ligaram
        st.write("#### Top 10 Clientes que Mais Ligaram")
        if not consolidado['clientes_frequentes_todos'].empty:
            st.dataframe(consolidado['clientes_frequentes_todos'].nlargest(10, 'total_ligacoes'))
        else:
            st.info("Nenhum cliente frequente encontrado.")

        # Download dos resultados
        st.subheader("Download dos Resultados")

        # Preparar buffer para Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # Rechamadas por Período (Detalhe)
            if rechamadas_detalhe:
                all_rechamadas_flat = []
                for periodo, items in rechamadas_detalhe.items():
                    for item in items:
                        item_copy = item.copy()
                        item_copy['periodo_rechamada'] = periodo
                        all_rechamadas_flat.append(item_copy)
                if all_rechamadas_flat:
                    df_rechamadas_detalhe_excel = pd.DataFrame(all_rechamadas_flat)
                    df_rechamadas_detalhe_excel.to_excel(writer, sheet_name='Detalhe_Rechamadas', index=False)
                else:
                    pd.DataFrame([{"Mensagem": "Nenhum detalhe de rechamada disponível."}]).to_excel(writer, sheet_name='Detalhe_Rechamadas', index=False)
            else:
                pd.DataFrame([{"Mensagem": "Nenhum detalhe de rechamada disponível."}]).to_excel(writer, sheet_name='Detalhe_Rechamadas', index=False)

            # Faixas de Ligações
            if consolidado['faixas_ligacoes']:
                faixas_df = pd.DataFrame(list(consolidado['faixas_ligacoes'].items()), columns=['Faixa', 'Quantidade'])
                faixas_df.to_excel(writer, sheet_name='Faixas_Ligacoes', index=False)
            else:
                pd.DataFrame([{"Mensagem": "Nenhuma faixa de ligação identificada."}]).to_excel(writer, sheet_name='Faixas_Ligacoes', index=False)

            # Clientes Frequentes
            if not consolidado['clientes_frequentes_todos'].empty:
                clientes_freq_excel = consolidado['clientes_frequentes_todos']
                clientes_freq_excel.to_excel(writer, sheet_name='Clientes_Frequentes', index=False)
            else:
                pd.DataFrame([{"Mensagem": "Nenhum cliente frequente identificado."}]).to_excel(writer, sheet_name='Clientes_Frequentes', index=False)

        buffer.seek(0)

        st.download_button(
            label="📥 Baixar Resultados em Excel",
            data=buffer,
            file_name=f"analise_rechamadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Aguardando a execução da análise de rechamadas para exibir os resultados.")
