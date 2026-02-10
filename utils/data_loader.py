import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta

# --- FUNÇÕES AUXILIARES GERAIS ---

def convert_duration_to_seconds(duracao_str):
    """
    Converte string de duração para segundos.
    Aceita formatos: mm:ss, hh:mm:ss, hh:mm:ss.mmm (com milissegundos)
    """
    if pd.isna(duracao_str) or duracao_str is None or duracao_str == '':
        return 0

    try:
        duracao_str = str(duracao_str).strip()

        # Verifica strings vazias ou inválidas
        if not duracao_str or duracao_str.lower() in ['nan', 'none', 'nat']:
            return 0

        # === NOVO: Remove milissegundos se existirem ===
        # Exemplo: "00:13:56.528" vira "00:13:56"
        if '.' in duracao_str:
            duracao_str = duracao_str.split('.')[0]

        # Processa formato hh:mm:ss ou mm:ss
        if ':' in duracao_str:
            partes = [int(p) for p in duracao_str.split(':')]

            if len(partes) == 2:   # mm:ss
                minutos, segundos = partes
                return minutos * 60 + segundos

            elif len(partes) == 3: # hh:mm:ss
                horas, minutos, segundos = partes
                return horas * 3600 + minutos * 60 + segundos

            else:
                return 0  # Formato desconhecido

        else:
            # Já é um número (segundos)
            return int(float(duracao_str))

    except (ValueError, TypeError, AttributeError):
        return 0


# --- FUNÇÕES DE CARREGAMENTO ---

def load_file_chamadas(uploaded_file):
    """
    Carrega arquivo de CHAMADAS (CSV ou Excel) e retorna DataFrame padronizado.
    EXIGE coluna de data/hora válida.
    """
    if uploaded_file is None:
        return None, "Nenhum arquivo enviado."

    file_extension = uploaded_file.name.split('.')[-1].lower()
    dfs = []

    try:
        if file_extension == 'csv':
            uploaded_file_content = uploaded_file.getvalue()
            df_temp = None
            for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                for sep in [',', ';', '\t']:
                    try:
                        df_temp = pd.read_csv(io.StringIO(uploaded_file_content.decode(encoding)), sep=sep)
                        if not df_temp.empty and len(df_temp.columns) > 1:
                            dfs.append(df_temp)
                            break
                    except Exception:
                        continue
                if dfs:
                    break
            if not dfs:
                return None, "Não foi possível carregar o arquivo CSV. Verifique o formato."

        elif file_extension in ['xlsx', 'xls']:
            uploaded_file.seek(0)
            excel_file = pd.ExcelFile(uploaded_file)
            for sheet_name in excel_file.sheet_names:
                df_temp = pd.read_excel(excel_file, sheet_name=sheet_name)
                if not df_temp.empty and len(df_temp.columns) > 1:
                    dfs.append(df_temp)
            if not dfs:
                return None, "Nenhum dado válido foi carregado de nenhuma aba do Excel."

        else:
            return None, f"Formato de arquivo não suportado: {file_extension}"

        df_combined = pd.concat(dfs, ignore_index=True)
        return process_dataframe_chamadas(df_combined), None

    except Exception as e:
        return None, f"Erro ao carregar arquivo: {e}"


def load_file_target(uploaded_file):
    """
    Carrega arquivo TARGET (CSV ou Excel) SEM processar data/hora.
    Apenas remove colunas Unnamed e mantém dados originais.
    """
    if uploaded_file is None:
        return None, "Nenhum arquivo enviado."

    file_extension = uploaded_file.name.split('.')[-1].lower()
    dfs = []

    try:
        if file_extension == 'csv':
            uploaded_file_content = uploaded_file.getvalue()
            df_temp = None
            for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                for sep in [',', ';', '\t']:
                    try:
                        df_temp = pd.read_csv(io.StringIO(uploaded_file_content.decode(encoding)), sep=sep)
                        if not df_temp.empty and len(df_temp.columns) > 1:
                            dfs.append(df_temp)
                            break
                    except Exception:
                        continue
                if dfs:
                    break
            if not dfs:
                return None, "Não foi possível carregar o arquivo CSV. Verifique o formato."

        elif file_extension in ['xlsx', 'xls']:
            uploaded_file.seek(0)
            excel_file = pd.ExcelFile(uploaded_file)
            for sheet_name in excel_file.sheet_names:
                df_temp = pd.read_excel(excel_file, sheet_name=sheet_name)
                if not df_temp.empty and len(df_temp.columns) > 1:
                    dfs.append(df_temp)
            if not dfs:
                return None, "Nenhum dado válido foi carregado de nenhuma aba do Excel."

        else:
            return None, f"Formato de arquivo não suportado: {file_extension}"

        df_combined = pd.concat(dfs, ignore_index=True)

        # Remove apenas colunas Unnamed
        df_combined = df_combined.loc[:, ~df_combined.columns.str.contains('^Unnamed', na=False)]

        return df_combined, None

    except Exception as e:
        return None, f"Erro ao carregar arquivo: {e}"


# --- PROCESSAMENTO DE DATAFRAMES ---

def process_dataframe_chamadas(df):
    """
    Processa DataFrame de CHAMADAS.
    Garante que 'datetime', 'telefone', 'duracao_segundos' e 'ID_Conversa' existam.
    EXCLUI telefones bloqueados e inválidos.
    """
    import streamlit as st

    # Remove colunas Unnamed
    df = df.loc[:, ~df.columns.str.contains('^Unnamed', na=False)]


    st.info(f"🔍 DEBUG: Total de linhas no CSV: {len(df)}")

    # --- DETECTAR COLUNA DE DATA/HORA (PRIORIDADE PARA NOMES EXATOS) ---
    datetime_col_name = None

    # PASSO 1: Procurar por nomes EXATOS de colunas de data (prioridade máxima)
    exact_datetime_names = ['Data', 'data', 'DATA', 'Date', 'date', 'Datetime', 'datetime']

    for exact_name in exact_datetime_names:
        if exact_name in df.columns:
            datetime_col_name = exact_name
            break

    # PASSO 2: Se não encontrou, procura por palavras-chave genéricas
    if not datetime_col_name:
        datetime_keywords = ['hora', 'time', 'timestamp', 'dt']

        for col in df.columns:
            col_lower = str(col).lower().strip()
            # Ignora colunas que contenham "parcial" ou "carimbo" (são metadados)
            if 'parcial' in col_lower or 'carimbo' in col_lower:
                continue
            if any(k in col_lower for k in datetime_keywords):
                datetime_col_name = col
                break

    if not datetime_col_name:
        st.error("❌ DEBUG: Nenhuma coluna de data/hora foi detectada!")
        df['datetime'] = pd.NaT
        return df


    # Normaliza a coluna
    df['data_hora'] = df[datetime_col_name].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)


    datetime_formats = [
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M',
        '%m/%d/%Y',
        '%H:%M:%S',
        '%H:%M',
        '%Y-%m-%d %H:%M:%S.%f',
    ]

    df['datetime'] = pd.NaT

    # Tenta cada formato
    for fmt in datetime_formats:
        mask = df['datetime'].isna()
        if not mask.any():
            break

        try:
            converted = pd.to_datetime(df.loc[mask, 'data_hora'], format=fmt, errors='coerce')
            converted_count = converted.notna().sum()

            if converted_count > 0:
                df.loc[mask, 'datetime'] = converted
        except Exception as e:
            continue

    # Última tentativa com inferência
    mask_final = df['datetime'].isna()
    if mask_final.any():
        df.loc[mask_final, 'datetime'] = pd.to_datetime(
            df.loc[mask_final, 'data_hora'],
            dayfirst=True,
            errors='coerce'
        )

    # Conta quantas datas foram convertidas
    valid_dates = df['datetime'].notna().sum()
    total_rows = len(df)


    if valid_dates == 0:
        st.error("❌ DEBUG: NENHUMA data foi convertida com sucesso!")
        return df

    # Remove linhas sem data válida
    df = df.dropna(subset=['datetime']).copy()

    # --- DETECTAR TELEFONE ---
    telefone_col_name = None

    # Primeiro procura por "ANI" (que é o nome no seu CSV)
    if 'ANI' in df.columns:
        telefone_col_name = 'ANI'
    else:
        telefone_keywords = ['telefone', 'phone', 'numero', 'número', 'fone', 'tel', 'ani']

        for col in df.columns:
            col_lower = str(col).lower().strip()
            if any(k in col_lower for k in telefone_keywords):
                telefone_col_name = col
                break

    if telefone_col_name:

        # === NOVO: FILTRO PARA TELEFONES BLOQUEADOS ===

        # 1. Remove linhas com telefones bloqueados (sip:anonymous, etc.)
        telefones_bloqueados = [
            'sip:anonymous@anonymous.invalid',
            'anonymous',
            'blocked',
            'bloqueado',
            'privado',
            'private',
            'unknown',
            'desconhecido'
        ]

        # Cria máscara para identificar telefones bloqueados
        mask_bloqueados = df[telefone_col_name].astype(str).str.lower().isin(telefones_bloqueados)

        # Também verifica se contém "sip:" ou "@" (padrão de telefone bloqueado)
        mask_sip = df[telefone_col_name].astype(str).str.contains('sip:', case=False, na=False)
        mask_arroba = df[telefone_col_name].astype(str).str.contains('@', na=False)

        # Combina todas as máscaras
        mask_total_bloqueados = mask_bloqueados | mask_sip | mask_arroba

        linhas_bloqueadas = mask_total_bloqueados.sum()
        if linhas_bloqueadas > 0:
            st.warning(f"⚠️ DEBUG: Removendo {linhas_bloqueadas} linhas com telefones bloqueados")
            df = df[~mask_total_bloqueados].copy()

        # 2. Limpa o telefone (remove tudo que não seja dígito)
        df['telefone'] = df[telefone_col_name].astype(str).str.replace(r'[^\d]', '', regex=True)

        # 3. Remove números específicos inválidos (como 2020159147)
        numeros_invalidos = [
            '2020159147',  # número que aparece incorretamente
            '0000000000',
            '1111111111',
            '9999999999'
        ]

        mask_invalidos = df['telefone'].isin(numeros_invalidos)
        linhas_invalidas = mask_invalidos.sum()
        if linhas_invalidas > 0:
            df = df[~mask_invalidos].copy()

        # 4. Mantém apenas telefones com 8 ou mais dígitos
        before_filter = len(df)
        df = df[df['telefone'].str.len() >= 8].copy()
        after_filter = len(df)

        if before_filter != after_filter:
            st.warning(f"⚠️ DEBUG: {before_filter - after_filter} linhas removidas por telefone inválido (< 8 dígitos)")

        # 5. Remove telefones que são apenas zeros ou apenas um dígito repetido
        mask_zeros = df['telefone'].str.match(r'^0+$')
        mask_repetidos = df['telefone'].apply(lambda x: len(set(x)) == 1 if len(x) > 0 else False)

        mask_padroes_invalidos = mask_zeros | mask_repetidos
        linhas_padroes = mask_padroes_invalidos.sum()
        if linhas_padroes > 0:
            st.warning(f"⚠️ DEBUG: Removendo {linhas_padroes} linhas com padrões inválidos (zeros, repetições)")
            df = df[~mask_padroes_invalidos].copy()


    else:
        st.warning("⚠️ DEBUG: Nenhuma coluna de telefone detectada")
        df['telefone'] = ''

        # --- DETECTAR DURAÇÃO ---
    duracao_col_name = None

    # Procura por "Duração" ou variações
    duracao_keywords = ['duracao', 'duração', 'duration', 'tempo', 'tma']

    for col in df.columns:
        col_lower = str(col).lower().strip()

        # === CORREÇÃO: Normalização COMPLETA de caracteres especiais ===
        # Remove acentos e caracteres HTML
        import unicodedata

        # Remove entidades HTML como &nbsp;
        col_normalized = col_lower.replace('&nbsp;', '').replace('&', '').replace('<', '').replace('>', '')

        # Normaliza caracteres com encoding incorreto
        replacements = {
            'ã': 'a', 'Ã': 'a', 'á': 'a', 'à': 'a', 'â': 'a',
            'é': 'e', 'ê': 'e', 'è': 'e',
            'í': 'i', 'ì': 'i', 'î': 'i',
            'ó': 'o', 'ô': 'o', 'õ': 'o', 'ò': 'o',
            'ú': 'u', 'ù': 'u', 'û': 'u',
            'ç': 'c', '§': 'c',
            'ñ': 'n'
        }

        for old_char, new_char in replacements.items():
            col_normalized = col_normalized.replace(old_char, new_char)

        # Remove qualquer caractere não-ASCII restante
        col_normalized = ''.join(char for char in col_normalized if ord(char) < 128)


        # Verifica se alguma palavra-chave está na coluna normalizada
        if any(k in col_normalized for k in duracao_keywords):
            duracao_col_name = col
            break

    if duracao_col_name:

        # Aplica a conversão
        df['duracao_segundos'] = df[duracao_col_name].apply(
            lambda x: convert_duration_to_seconds(x) if pd.notna(x) else 0
        )


        # === DEBUG: Estatísticas da duração ===
        total_segundos = df['duracao_segundos'].sum()
        media_segundos = df['duracao_segundos'].mean()
        zeros_count = (df['duracao_segundos'] == 0).sum()


        if zeros_count > 0:

            # Mostra alguns exemplos de valores que ficaram zerados
            exemplos_zero = df[df['duracao_segundos'] == 0][duracao_col_name].head(5).tolist()
            
    else:
        st.warning("⚠️ DEBUG: Nenhuma coluna de duração detectada")
        df['duracao_segundos'] = 0



    # --- DETECTAR ID DE CONVERSA ---
    id_conversa_col_name = None

    # Primeiro procura por "ID de conversa" (que é o nome no seu CSV)
    if 'ID de conversa' in df.columns:
        id_conversa_col_name = 'ID de conversa'
    else:
        id_conversa_keywords = ['id', 'conversa', 'protocolo', 'ticket', 'call_id']

        for col in df.columns:
            col_lower = str(col).lower().strip()
            if any(k in col_lower for k in id_conversa_keywords):
                id_conversa_col_name = col
                break

    if id_conversa_col_name:
        df['ID_Conversa'] = df[id_conversa_col_name].astype(str)
    else:
        df['ID_Conversa'] = (
            df.index.astype(str) + '_' +
            df['datetime'].dt.strftime('%Y%m%d%H%M%S').fillna('NA')
        )

    df = df.sort_values(['telefone', 'datetime']).reset_index(drop=True)

    return df


# --- FUNÇÕES DE ANÁLISE DE RECHAMADAS ---

def identificar_faixas_rechamada(df):
    """
    Identifica rechamadas em faixas de 0-24h, 24-48h, 48-72h.
    Cada rechamada é comparada com a PRIMEIRA ligação do telefone.
    A primeira ligação nunca é considerada rechamada.
    """
    rechamadas = {'0-24h': [], '24-48h': [], '48-72h': [], 'mais_72h': []}

    if 'telefone' not in df.columns or 'datetime' not in df.columns or 'ID_Conversa' not in df.columns:
        return rechamadas

    for telefone, grupo in df.groupby('telefone'):
        grupo = grupo.sort_values('datetime')

        # Se tiver menos de 2 ligações, não há rechamada
        if len(grupo) < 2:
            continue

        # Pega os dados ordenados
        ids_conversa = grupo['ID_Conversa'].values
        datas = grupo['datetime'].values

        # Verifica se há coluna de duração
        if 'duracao_segundos' in df.columns:
            duras = grupo['duracao_segundos'].values
        else:
            duras = np.zeros(len(grupo))

        # === CORREÇÃO: Todas as rechamadas são comparadas com a PRIMEIRA ligação (i=0) ===
        primeira_data = datas[0]
        primeira_id = ids_conversa[0]
        primeira_duracao = duras[0]

        # Começa da segunda ligação (i=1) e compara SEMPRE com a primeira (i=0)
        for i in range(1, len(datas)):
            # Calcula diferença em horas entre ligação atual e a PRIMEIRA
            diff_h = (datas[i] - primeira_data) / np.timedelta64(1, 'h')

            if diff_h <= 0:
                continue

            rec = {
                'telefone': telefone,
                'primeira_ligacao': pd.to_datetime(primeira_data),      # SEMPRE a primeira ligação
                'segunda_ligacao': pd.to_datetime(datas[i]),           # Ligação atual (rechamada)
                'diferenca_horas': float(diff_h),
                'duracao_primeira_seg': primeira_duracao,              # SEMPRE duração da primeira
                'duracao_segunda_seg': duras[i],                       # Duração da ligação atual
                'ID_Conversa_Primeira': primeira_id,                   # SEMPRE ID da primeira
                'ID_Conversa_Segunda': ids_conversa[i]                 # ID da ligação atual
            }

            # Classifica por faixa de tempo
            if diff_h <= 24:
                rechamadas['0-24h'].append(rec)
            elif 24 < diff_h <= 48:
                rechamadas['24-48h'].append(rec)
            elif 48 < diff_h <= 72:
                rechamadas['48-72h'].append(rec)
            else:
                rechamadas['mais_72h'].append(rec)

    return rechamadas


def faixas_ligacoes_e_reincidentes(df):
    """Calcula a contagem de ligações por telefone e as faixas de reincidência."""
    if 'telefone' not in df.columns:
        return {}, 0, pd.Series()

    contagem_por_telefone = df.groupby("telefone").size()
    faixas = {
        '1 ligação': len(contagem_por_telefone[contagem_por_telefone == 1]),
        '2-5 ligações': len(contagem_por_telefone[(contagem_por_telefone >= 2) & (contagem_por_telefone <= 5)]),
        '6-10 ligações': len(contagem_por_telefone[(contagem_por_telefone >= 6) & (contagem_por_telefone <= 10)]),
        '11-20 ligações': len(contagem_por_telefone[(contagem_por_telefone >= 11) & (contagem_por_telefone <= 20)]),
        '21-50 ligações': len(contagem_por_telefone[(contagem_por_telefone >= 21) & (contagem_por_telefone <= 50)]),
        'Mais de 50 ligações': len(contagem_por_telefone[contagem_por_telefone > 50])
    }
    telefones_ligaram_mais_de_uma_vez = len(contagem_por_telefone[contagem_por_telefone > 1])
    return faixas, telefones_ligaram_mais_de_uma_vez, contagem_por_telefone

def calcular_impacto_financeiro(rechamadas, valor_ligacao=7.56):
    """Calcula o impacto financeiro das rechamadas."""
    impacto_por_faixa = {
        '0-24h': len(rechamadas.get('0-24h', [])) * valor_ligacao,
        '24-48h': len(rechamadas.get('24-48h', [])) * valor_ligacao,
        '48-72h': len(rechamadas.get('48-72h', [])) * valor_ligacao,
        'mais_72h': 0
    }
    total_religacoes_com_impacto = sum(len(rechamadas.get(k, [])) for k in ['0-24h', '24-48h', '48-72h'])
    return total_religacoes_com_impacto * valor_ligacao

def analisar_motivos_rechamadas(df_chamadas, rechamadas_detalhe, df_target, id_coluna_target, colunas_retorno):
    """
    Cruza as rechamadas identificadas com os motivos de contato de um arquivo target.
    Garante 1 linha por rechamada (ID_Conversa_Primeira + ID_Conversa_Segunda),
    mesmo que o target tenha múltiplos registros por ID Genesys.
    """
    if not rechamadas_detalhe or df_target.empty:
        return pd.DataFrame(), "Dados de rechamadas ou arquivo target vazios."

    # 1) Achata o dicionário de rechamadas em um DataFrame
    all_rechamadas_list = []
    for periodo, dados in rechamadas_detalhe.items():
        for item in dados:
            all_rechamadas_list.append({
                'telefone': str(item['telefone']),
                'primeira_ligacao_datetime': item['primeira_ligacao'],
                'segunda_ligacao_datetime': item['segunda_ligacao'],
                'diferenca_horas': item['diferenca_horas'],
                'periodo_rechamada': periodo,
                'ID_Conversa_Primeira': str(item['ID_Conversa_Primeira']),
                'ID_Conversa_Segunda': str(item['ID_Conversa_Segunda'])
            })

    df_rechamadas_consolidado = pd.DataFrame(all_rechamadas_list)

    if df_rechamadas_consolidado.empty:
        return pd.DataFrame(), "Nenhuma rechamada consolidada."

    if id_coluna_target not in df_target.columns:
        return pd.DataFrame(), f"Coluna '{id_coluna_target}' não encontrada no target."

    # 2) Garante que só usaremos colunas de retorno que existem
    colunas_existentes_retorno = [col for col in colunas_retorno if col in df_target.columns]
    if not colunas_existentes_retorno:
        return pd.DataFrame(), "Nenhuma coluna selecionada existe no target."

    # 3) Normaliza o ID do target e AGREGA motivos por ID (1 linha por ID genesys)
    df_target_reduzido = df_target[[id_coluna_target] + colunas_existentes_retorno].copy()
    df_target_reduzido[id_coluna_target] = df_target_reduzido[id_coluna_target].astype(str).str.strip()

    # Para cada coluna de motivo, agregamos valores distintos em uma string única por ID
    agg_dict = {}
    for col in colunas_existentes_retorno:
        # Junta valores distintos não nulos, ordenados, separados por " | "
        agg_dict[col] = lambda s: ' | '.join(sorted({str(v).strip() for v in s.dropna() if str(v).strip()})) or None

    df_target_agg = df_target_reduzido.groupby(id_coluna_target, as_index=False).agg(agg_dict)

    # 4) Normaliza IDs das rechamadas
    df_rechamadas_consolidado['ID_Conversa_Primeira'] = df_rechamadas_consolidado['ID_Conversa_Primeira'].astype(str).str.strip()
    df_rechamadas_consolidado['ID_Conversa_Segunda'] = df_rechamadas_consolidado['ID_Conversa_Segunda'].astype(str).str.strip()

    # 5) Prepara mapeamentos de nome de coluna para primeira e segunda ligação
    rename_map_primeira = {col: f'motivo_primeira_{col}' for col in colunas_existentes_retorno}
    rename_map_segunda = {col: f'motivo_segunda_{col}' for col in colunas_existentes_retorno}

    # 6) Merge da PRIMEIRA ligação (left join mantém 1 linha por rechamada)
    df_resultado = pd.merge(
        df_rechamadas_consolidado,
        df_target_agg.rename(columns=rename_map_primeira),
        left_on='ID_Conversa_Primeira',
        right_on=id_coluna_target,
        how='left'
    )

    if id_coluna_target not in colunas_existentes_retorno:
        df_resultado = df_resultado.drop(columns=[id_coluna_target], errors='ignore')

    # 7) Merge da SEGUNDA ligação
    df_resultado = pd.merge(
        df_resultado,
        df_target_agg.rename(columns=rename_map_segunda),
        left_on='ID_Conversa_Segunda',
        right_on=id_coluna_target,
        how='left',
        suffixes=('', '_dup')
    )

    if id_coluna_target not in colunas_existentes_retorno:
        df_resultado = df_resultado.drop(columns=[id_coluna_target], errors='ignore')

    # 8) Garante que não houve duplicação de linhas
    df_resultado = df_resultado.drop_duplicates(
        subset=['telefone', 'ID_Conversa_Primeira', 'ID_Conversa_Segunda', 'primeira_ligacao_datetime', 'segunda_ligacao_datetime']
    ).reset_index(drop=True)

    return df_resultado, None


# --- FUNÇÕES DE ANÁLISE DE DESEMPENHO DE AGENTES ---

def process_performance_file(uploaded_file, file_type):
    """Processa arquivo de desempenho de agentes."""
    if uploaded_file is None:
        return None, f"Arquivo {file_type} não carregado."

    try:
        df = pd.read_excel(uploaded_file)

        if file_type == 'tma':
            required_cols = ['Nome do agente', 'Atendidas', 'Transferidas', 'TMA']
            col_map = {
                'Nome do agente': 'ID_Agente',
                'Atendidas': 'Total_Chamadas',
                'Transferidas': 'Total_Pesquisas_Oferecidas'
            }
        elif file_type == 'desliga':
            required_cols = ['Nome do agente', 'Desligou']
            col_map = {'Nome do agente': 'ID_Agente'}
        elif file_type == 'nota':
            required_cols = ['Nome do atribuído', 'NPS Atendente']
            col_map = {'Nome do atribuído': 'ID_Agente'}
        else:
            return None, f"Tipo de arquivo {file_type} não reconhecido."

        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return None, f"Colunas ausentes no arquivo {file_type}: {', '.join(missing_cols)}"

        df = df.rename(columns=col_map)
        df['ID_Agente'] = df['ID_Agente'].astype(str).str.lower().str.strip()

        if file_type == 'tma':
            df['TMA_segundos'] = df['TMA'].astype(str).str.extract(r'(\d{2}:\d{2}:\d{2})')[0]
            df['TMA_segundos'] = pd.to_timedelta(df['TMA_segundos']).dt.total_seconds()
            df['TMA_segundos'] = df['TMA_segundos'].fillna(0)
            df['Total_Chamadas'] = pd.to_numeric(df['Total_Chamadas'], errors='coerce').fillna(0)
            df['Total_Pesquisas_Oferecidas'] = pd.to_numeric(df['Total_Pesquisas_Oferecidas'], errors='coerce').fillna(0)

        elif file_type == 'desliga':
            df['Ligacao_Encerrada_Operador_Bin'] = (df['Desligou'].astype(str).str.lower().str.strip() == 'agente').astype(int)
            df = df.groupby('ID_Agente')['Ligacao_Encerrada_Operador_Bin'].sum().reset_index()
            df = df.rename(columns={'Ligacao_Encerrada_Operador_Bin': 'Total_Ligacoes_Encerradas_Operador'})

        elif file_type == 'nota':
            df['NPS_Score_Numeric'] = pd.to_numeric(df['NPS Atendente'], errors='coerce')
            df = df.dropna(subset=['NPS_Score_Numeric']).groupby('ID_Agente')['NPS_Score_Numeric'].mean().reset_index()
            df = df.rename(columns={'NPS_Score_Numeric': 'Nota_Media_Satisfacao'})

        return df, None
    except Exception as e:
        return None, f"Erro ao processar arquivo {file_type}: {e}"

def analisar_desempenho_agentes(df_tma, df_desliga, df_nota, normalized_weights, max_operator_ended_calls_percentage):
    """Analisa o desempenho dos agentes."""
    if df_tma is None:
        return None, "Arquivo TMA é obrigatório."

    operator_performance = df_tma.copy()

    if df_desliga is not None:
        operator_performance = pd.merge(operator_performance, df_desliga, on='ID_Agente', how='outer')

    if df_nota is not None:
        operator_performance = pd.merge(operator_performance, df_nota, on='ID_Agente', how='outer')

    operator_performance = operator_performance.fillna({
        'Total_Chamadas': 0,
        'Total_Pesquisas_Oferecidas': 0,
        'TMA_segundos': 0,
        'Total_Ligacoes_Encerradas_Operador': 0,
        'Nota_Media_Satisfacao': 0
    })

    operator_performance = operator_performance[operator_performance['Total_Chamadas'] > 0].copy()

    if operator_performance.empty:
        return None, "Nenhum operador com chamadas válidas."

    operator_performance['Percentual_Encaminhamento_Pesquisa'] = (operator_performance['Total_Pesquisas_Oferecidas'] / operator_performance['Total_Chamadas']) * 100
    operator_performance['Percentual_Encaminhamento_Pesquisa'] = operator_performance['Percentual_Encaminhamento_Pesquisa'].fillna(0).clip(upper=100)

    operator_performance['Percentual_Ligacoes_Encerradas_Operador'] = (operator_performance['Total_Ligacoes_Encerradas_Operador'] / operator_performance['Total_Chamadas']) * 100
    operator_performance['Percentual_Ligacoes_Encerradas_Operador'] = operator_performance['Percentual_Ligacoes_Encerradas_Operador'].fillna(0).clip(upper=100)

    def normalize_metric(series, reverse=False):
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series(0.5, index=series.index)
        normalized = (series - min_val) / (max_val - min_val)
        return 1 - normalized if reverse else normalized

    operator_performance['TMA_Normalizado'] = normalize_metric(operator_performance['TMA_segundos'], reverse=True)
    operator_performance['CSAT_Normalizado'] = normalize_metric(operator_performance['Nota_Media_Satisfacao'], reverse=False)
    operator_performance['Pesquisa_Encaminhamento_Normalizado'] = normalize_metric(operator_performance['Percentual_Encaminhamento_Pesquisa'], reverse=False)

    operator_performance['Ligacoes_Encerradas_Normalizado'] = normalize_metric(operator_performance['Percentual_Ligacoes_Encerradas_Operador'], reverse=True)

    penalty_factor = 1.0 - (operator_performance['Percentual_Ligacoes_Encerradas_Operador'] / max_operator_ended_calls_percentage).clip(upper=1)
    operator_performance['Ligacoes_Encerradas_Normalizado'] = operator_performance['Ligacoes_Encerradas_Normalizado'] * penalty_factor

    operator_performance['Score_Desempenho'] = (
        operator_performance['TMA_Normalizado'] * normalized_weights['TMA'] +
        operator_performance['CSAT_Normalizado'] * normalized_weights['CSAT'] +
        operator_performance['Pesquisa_Encaminhamento_Normalizado'] * normalized_weights['Encaminhamento'] +
        operator_performance['Ligacoes_Encerradas_Normalizado'] * normalized_weights['Encerramento']
    )

    operator_performance['Rank'] = operator_performance['Score_Desempenho'].rank(ascending=False).astype(int)

    return operator_performance.sort_values('Rank').reset_index(drop=True), None
import streamlit as st
from utils.data_loader import load_file_chamadas, load_file_target

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
    st.subheader("Arquivos de Desempenho de Agentes (Opcional)")

    uploaded_file_tma = st.file_uploader(
        "Carregar arquivo TMA",
        type=["xlsx", "xls"],
        key="tma_upload"
    )

    uploaded_file_desliga = st.file_uploader(
        "Carregar arquivo Desliga",
        type=["xlsx", "xls"],
        key="desliga_upload"
    )

    uploaded_file_nota = st.file_uploader(
        "Carregar arquivo Nota",
        type=["xlsx", "xls"],
        key="nota_upload"
    )

    if uploaded_file_tma:
        from utils.data_loader import process_performance_file
        df_tma, error = process_performance_file(uploaded_file_tma, 'tma')
        if error:
            st.error(f"Erro ao carregar arquivo TMA: {error}")
            st.session_state.df_tma = None
        else:
            st.session_state.df_tma = df_tma
            st.success(f"✅ Arquivo TMA carregado com sucesso! Total de registros: {len(df_tma):,}")

    if uploaded_file_desliga:
        from utils.data_loader import process_performance_file
        df_desliga, error = process_performance_file(uploaded_file_desliga, 'desliga')
        if error:
            st.error(f"Erro ao carregar arquivo Desliga: {error}")
            st.session_state.df_desliga = None
        else:
            st.session_state.df_desliga = df_desliga
            st.success(f"✅ Arquivo Desliga carregado com sucesso! Total de registros: {len(df_desliga):,}")

    if uploaded_file_nota:
        from utils.data_loader import process_performance_file
        df_nota, error = process_performance_file(uploaded_file_nota, 'nota')
        if error:
            st.error(f"Erro ao carregar arquivo Nota: {error}")
            st.session_state.df_nota = None
        else:
            st.session_state.df_nota = df_nota
            st.success(f"✅ Arquivo Nota carregado com sucesso! Total de registros: {len(df_nota):,}")
