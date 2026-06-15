import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime
from utils.data_loader import analisar_motivos_rechamadas
from utils.visualization import set_style, plot_bar_chart

def explodir_assuntos(df, coluna_assunto, nova_coluna='Assunto'):
    """Explode uma coluna de assuntos em múltiplas linhas, um assunto por linha."""
    s = df[coluna_assunto].astype(str)
    # separadores possíveis: ; , / |
    s = s.str.split(r'[;,/|]+')
    df_exp = df.copy()
    df_exp[nova_coluna] = s
    df_exp = df_exp.explode(nova_coluna)
    df_exp[nova_coluna] = df_exp[nova_coluna].astype(str).str.strip()
    df_exp = df_exp[
        df_exp[nova_coluna].notna() &
        (df_exp[nova_coluna] != '') &
        (df_exp[nova_coluna] != 'nan')
    ]
    return df_exp

def show():
    set_style()
    st.header("🔍 Motivos / Assuntos das Rechamadas")

    # Verificações preliminares
    if st.session_state.get('df_chamadas') is None:
        st.warning("⚠️ Nenhum dado de chamadas carregado. Por favor, faça o upload do arquivo na aba 'Upload de Arquivos'.")
        return

    if st.session_state.get('rechamadas_detalhe') is None:
        st.warning("⚠️ Nenhuma análise de rechamadas realizada. Execute a análise na aba 'Análise de Rechamadas' primeiro.")
        return

    if st.session_state.get('df_target') is None:
        st.warning("⚠️ Arquivo Target não carregado. Por favor, faça o upload na aba 'Upload de Arquivos'.")
        return

    df_chamadas = st.session_state.df_chamadas.copy()

    # --- CORREÇÃO 1: Remover duplicatas pelo ID_Conversa para não inflar os cruzamentos ---
    if 'ID_Conversa' in df_chamadas.columns:
        df_chamadas = df_chamadas.drop_duplicates(subset=['ID_Conversa']).copy()

    rechamadas_detalhe = st.session_state.rechamadas_detalhe
    df_target = st.session_state.df_target.copy()

    # --- CONFIGURAÇÃO DO CRUZAMENTO ---
    st.subheader("⚙️ Configuração do Cruzamento")

    col1, col2 = st.columns(2)
    with col1:
        # ID nas chamadas
        opcoes_id_chamadas = []
        if 'ID de conversa' in df_chamadas.columns:
            opcoes_id_chamadas.append('ID de conversa')
        if 'ID_Conversa' in df_chamadas.columns and 'ID_Conversa' not in opcoes_id_chamadas:
            opcoes_id_chamadas.append('ID_Conversa')
        for c in df_chamadas.columns:
            if 'id' in c.lower() and c not in opcoes_id_chamadas:
                opcoes_id_chamadas.append(c)
        if not opcoes_id_chamadas:
            opcoes_id_chamadas = list(df_chamadas.columns)

        id_coluna_chamadas = st.selectbox(
            "Coluna de ID no arquivo de Chamadas",
            opcoes_id_chamadas,
            index=0,
            key="id_coluna_chamadas_motivos"
        )

    with col2:
        # ID no target
        opcoes_id_target = []
        for c in df_target.columns:
            if 'id' in c.lower() and 'genesys' in c.lower():
                opcoes_id_target.insert(0, c)
        if not opcoes_id_target:
            for c in df_target.columns:
                if 'id' in c.lower():
                    opcoes_id_target.append(c)
        if not opcoes_id_target:
            opcoes_id_target = list(df_target.columns)

        id_coluna_target = st.selectbox(
            "Coluna de ID no Target (ID Genesys)",
            opcoes_id_target,
            index=0,
            key="id_coluna_target_motivos"
        )

    # --- CORREÇÃO 2: Inteligência para pré-selecionar a coluna de NOME em vez de CÓDIGO ---
    opcoes_assunto = list(df_target.columns)
    idx_assunto = 0
    for i, col in enumerate(opcoes_assunto):
        col_lower = col.lower()
        # Procura palavras que indicam nome/descrição
        if any(k in col_lower for k in ['assunto', 'motivo', 'nome', 'desc', 'reason', 'wrapup', 'tema']):
            # Ignora se tiver "id" ou "codigo" no nome
            if not any(exc in col_lower for exc in ['id', 'cod', 'cód', 'code']):
                idx_assunto = i
                break

    st.write("**Selecione a coluna de assunto/motivo no Target:**")
    coluna_assunto = st.selectbox(
        "Coluna de Assunto/Motivo (⚠️ Escolha a coluna com os NOMES, evite colunas de código)",
        options=opcoes_assunto,
        index=idx_assunto,
        key="coluna_assunto"
    )

    st.info(f"🔗 Cruzamento: CHAMADAS `{id_coluna_chamadas}` ↔ TARGET `{id_coluna_target}`, assunto `{coluna_assunto}`")

    # --- EXECUÇÃO DO CRUZAMENTO ---
    if st.button("🔄 Executar Análise de Motivos", type="primary"):
        with st.spinner("Cruzando dados de rechamadas com motivos..."):
            # Normaliza ID_Conversa em df_chamadas
            df_chamadas_temp = df_chamadas.copy()
            if id_coluna_chamadas != 'ID_Conversa':
                df_chamadas_temp['ID_Conversa'] = df_chamadas_temp[id_coluna_chamadas].astype(str).str.strip()

            # Usa analisar_motivos_rechamadas para montar base de rechamadas + motivos
            df_final_motivos, error_message = analisar_motivos_rechamadas(
                df_chamadas_temp,
                rechamadas_detalhe,
                df_target,
                id_coluna_target,
                [coluna_assunto]
            )

            if error_message:
                st.error(f"❌ {error_message}")
                st.session_state.df_final_motivos = None
            elif df_final_motivos.empty:
                st.warning("⚠️ Nenhum motivo encontrado para as rechamadas com os critérios selecionados.")
                st.session_state.df_final_motivos = None
            else:
                # ENRIQUECE COM DURAÇÃO DAS CHAMADAS
                df_duracao_primeira = df_chamadas_temp[['ID_Conversa', 'duracao_segundos', 'telefone']].copy()
                df_duracao_primeira.columns = ['ID_Conversa_Primeira', 'duracao_primeira_segundos', 'telefone_primeira']
                df_duracao_primeira['ID_Conversa_Primeira'] = df_duracao_primeira['ID_Conversa_Primeira'].astype(str).str.strip()

                df_duracao_segunda = df_chamadas_temp[['ID_Conversa', 'duracao_segundos', 'telefone']].copy()
                df_duracao_segunda.columns = ['ID_Conversa_Segunda', 'duracao_segunda_segundos', 'telefone_segunda']
                df_duracao_segunda['ID_Conversa_Segunda'] = df_duracao_segunda['ID_Conversa_Segunda'].astype(str).str.strip()

                df_final_motivos = pd.merge(
                    df_final_motivos,
                    df_duracao_primeira,
                    on='ID_Conversa_Primeira',
                    how='left'
                )

                df_final_motivos = pd.merge(
                    df_final_motivos,
                    df_duracao_segunda,
                    on='ID_Conversa_Segunda',
                    how='left'
                )

                df_final_motivos['duracao_primeira_segundos'] = df_final_motivos['duracao_primeira_segundos'].fillna(0)
                df_final_motivos['duracao_segunda_segundos'] = df_final_motivos['duracao_segunda_segundos'].fillna(0)

                # Salva para uso na parte de análise
                st.session_state.df_final_motivos = df_final_motivos
                st.success(f"✅ Cruzamento concluído! {df_final_motivos['ID_Conversa_Segunda'].nunique():,} rechamadas únicas identificadas.")

    # --- EXIBIÇÃO DOS RESULTADOS ---
    if st.session_state.get('df_final_motivos') is None:
        return

    df_final_motivos = st.session_state.df_final_motivos
    coluna_assunto = st.session_state.get('coluna_assunto')

    st.subheader("📊 Métricas Gerais")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        # --- CORREÇÃO 3: Contar apenas IDs únicos da segunda ligação ---
        total_rechamadas = df_final_motivos['ID_Conversa_Segunda'].nunique()
        st.metric("Total de Rechamadas (Ligações Únicas)", f"{total_rechamadas:,}")
    with col_m2:
        # Telefones que geraram rechamadas
        total_primeiros_contatos = df_final_motivos['ID_Conversa_Primeira'].nunique()
        st.metric("Total de Primeiros Contatos (que geraram rechamadas)", f"{total_primeiros_contatos:,}")

    st.write("**Dados Base (Rechamadas + Motivos + Duração):**")
    st.dataframe(df_final_motivos, width='stretch', height=250)

    # --- PREPARAÇÃO PARA CONTAGEM DE ASSUNTOS ---
    st.subheader("📈 Análise de Assuntos e Duração")

    df_chamadas_all = df_chamadas.copy()
    contagem_tel = df_chamadas_all.groupby('telefone').size()
    df_chamadas_all['total_ligacoes_telefone'] = df_chamadas_all['telefone'].map(contagem_tel)
    df_chamadas_all['cliente_uma_ligacao'] = df_chamadas_all['total_ligacoes_telefone'] == 1
    df_chamadas_all['cliente_reincidente'] = df_chamadas_all['total_ligacoes_telefone'] > 1

    df_target_temp = df_target.copy()
    df_target_temp[id_coluna_target] = df_target_temp[id_coluna_target].astype(str).str.strip()

    df_chamadas_all['ID_Conversa'] = df_chamadas_all['ID_Conversa'].astype(str).str.strip()
    df_chamadas_assuntos = pd.merge(
        df_chamadas_all,
        df_target_temp[[id_coluna_target, coluna_assunto]].rename(columns={id_coluna_target: 'ID_Conversa'}),
        on='ID_Conversa',
        how='left'
    )

    df_chamadas_assuntos = df_chamadas_assuntos.sort_values(['telefone', 'datetime'])
    primeira_ligacao_idx = df_chamadas_assuntos.groupby('telefone').head(1).index
    df_chamadas_assuntos['primeira_ligacao'] = False
    df_chamadas_assuntos.loc[primeira_ligacao_idx, 'primeira_ligacao'] = True

    df_all_assuntos = explodir_assuntos(df_chamadas_assuntos, coluna_assunto, 'Assunto')

    cont_todas = df_all_assuntos['Assunto'].value_counts().rename('Qtd_Todas')
    df_uma = df_all_assuntos[df_all_assuntos['cliente_uma_ligacao']]
    cont_uma = df_uma['Assunto'].value_counts().rename('Qtd_Clientes_1_Ligacao')

    df_primeiras_reinc = df_all_assuntos[
        df_all_assuntos['cliente_reincidente'] & df_all_assuntos['primeira_ligacao']
    ]
    cont_primeiras_reinc = df_primeiras_reinc['Assunto'].value_counts().rename('Qtd_Primeiras_Reincidentes')

    all_rech = []
    for periodo, dados in rechamadas_detalhe.items():
        for item in dados:
            all_rech.append({
                'telefone': str(item['telefone']),
                'ID_Conversa_Segunda': str(item['ID_Conversa_Segunda'])
            })
    df_rech = pd.DataFrame(all_rech).drop_duplicates()

    if not df_rech.empty:
        df_rech = pd.merge(
            df_rech,
            df_chamadas_assuntos[['ID_Conversa', 'telefone', coluna_assunto, 'duracao_segundos']].rename(
                columns={'ID_Conversa': 'ID_Conversa_Segunda'}
            ),
            on=['ID_Conversa_Segunda', 'telefone'],
            how='left'
        )
        df_rech_assuntos = explodir_assuntos(df_rech, coluna_assunto, 'Assunto')
        cont_rech = df_rech_assuntos['Assunto'].value_counts().rename('Qtd_Rechamadas')

        temp_rech = df_rech_assuntos.groupby('Assunto')['duracao_segundos'].agg(['sum', 'mean']).rename(
            columns={'sum': 'Tempo_Total_Rech_Seg', 'mean': 'TMA_Rech_Seg'}
        )
    else:
        cont_rech = pd.Series(dtype=int, name='Qtd_Rechamadas')
        temp_rech = pd.DataFrame(columns=['Tempo_Total_Rech_Seg', 'TMA_Rech_Seg']).set_index(pd.Index([], name='Assunto'))

    df_reinc_all = df_all_assuntos[df_all_assuntos['cliente_reincidente']]
    cont_reinc_total = df_reinc_all['Assunto'].value_counts().rename('Qtd_Total_Reincidentes')

    if not df_primeiras_reinc.empty:
        temp_primeiras = df_primeiras_reinc.groupby('Assunto')['duracao_segundos'].agg(['sum', 'mean']).rename(
            columns={'sum': 'Tempo_Total_Prim_Seg', 'mean': 'TMA_Prim_Seg'}
        )
    else:
        temp_primeiras = pd.DataFrame(columns=['Tempo_Total_Prim_Seg', 'TMA_Prim_Seg']).set_index(pd.Index([], name='Assunto'))

    assuntos_index = sorted(
        set(cont_todas.index) |
        set(cont_uma.index) |
        set(cont_primeiras_reinc.index) |
        set(cont_rech.index) |
        set(cont_reinc_total.index)
    )
    resumo = pd.DataFrame({'Assunto': assuntos_index}).set_index('Assunto')
    resumo = resumo.join(cont_todas, how='left')
    resumo = resumo.join(cont_uma, how='left')
    resumo = resumo.join(cont_primeiras_reinc, how='left')
    resumo = resumo.join(cont_rech, how='left')
    resumo = resumo.join(cont_reinc_total, how='left')
    resumo = resumo.join(temp_primeiras, how='left')
    resumo = resumo.join(temp_rech, how='left')

    resumo = resumo.fillna(0)

    resumo['Tempo_Total_Prim_Min'] = (resumo['Tempo_Total_Prim_Seg'] / 60).round(1)
    resumo['TMA_Prim_Min'] = (resumo['TMA_Prim_Seg'] / 60).round(1)
    resumo['Tempo_Total_Rech_Min'] = (resumo['Tempo_Total_Rech_Seg'] / 60).round(1)
    resumo['TMA_Rech_Min'] = (resumo['TMA_Rech_Seg'] / 60).round(1)

    resumo = resumo.astype({
        'Qtd_Todas': 'int64',
        'Qtd_Clientes_1_Ligacao': 'int64',
        'Qtd_Primeiras_Reincidentes': 'int64',
        'Qtd_Rechamadas': 'int64',
        'Qtd_Total_Reincidentes': 'int64'
    }).sort_values('Qtd_Todas', ascending=False).reset_index()

    st.write("""
- **Qtd_Todas**: vezes que o assunto aparece em todas as ligações
- **Qtd_Clientes_1_Ligacao**: vezes que o assunto aparece em clientes que ligaram apenas 1 vez
- **Qtd_Primeiras_Reincidentes**: vezes que o assunto aparece na **primeira ligação** de clientes que ligaram mais de 1 vez
- **Qtd_Rechamadas**: vezes que o assunto aparece nas ligações identificadas como rechamadas
- **Qtd_Total_Reincidentes**: vezes que o assunto aparece em **todas as ligações** de clientes que ligaram mais de 1 vez
- **Tempo_Total_Prim_Min / TMA_Prim_Min**: tempo total e TMA das primeiras ligações (reincidentes) por assunto
- **Tempo_Total_Rech_Min / TMA_Rech_Min**: tempo total e TMA das rechamadas por assunto
    """)

    st.dataframe(resumo, width='stretch')

    # Gráficos (Top 15)
    top = resumo.head(15)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig1, ax1 = plot_bar_chart(
            data=top,
            x='Qtd_Todas',
            y='Assunto',
            title='Top 15 Assuntos - Todas as Ligações',
            color='steelblue',
            figsize=(10, 8),
            is_horizontal=True
        )
        st.pyplot(fig1)

    with col_g2:
        fig2, ax2 = plot_bar_chart(
            data=top,
            x='Qtd_Rechamadas',
            y='Assunto',
            title='Top 15 Assuntos - Rechamadas',
            color='darkorange',
            figsize=(10, 8),
            is_horizontal=True
        )
        st.pyplot(fig2)

    st.subheader("⏱️ TMA por Assunto (Primeiras vs Rechamadas)")
    top_tma = resumo.sort_values('TMA_Rech_Min', ascending=False).head(15)
    fig_tma, ax_tma = plot_bar_chart(
        data=top_tma,
        x='TMA_Rech_Min',
        y='Assunto',
        title='Top 15 Assuntos - TMA em Rechamadas (min)',
        color='purple',
        figsize=(10, 8),
        is_horizontal=True
    )
    st.pyplot(fig_tma)

    # --- DOWNLOAD DOS RESULTADOS ---
    st.subheader("📥 Download dos Resultados")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        resumo.to_excel(writer, sheet_name='Resumo_Assuntos', index=False)
        df_all_assuntos.to_excel(writer, sheet_name='Detalhe_Assuntos_Todas', index=False)
        df_final_motivos.to_excel(writer, sheet_name='Rechamadas_Base', index=False)
    buffer.seek(0)

    st.download_button(
        "📥 Baixar Excel (Assuntos + TMA)",
        data=buffer,
        file_name=f"analise_motivos_rechamadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
