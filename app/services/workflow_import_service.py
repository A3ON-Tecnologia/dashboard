import io
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class ImportacaoArquivoErro(Exception):
    """Erro controlado para importacao de arquivos de workflow."""


ALLOWED_EXTENSIONS = {'.csv', '.xlsx'}


def _normalize_header(value: Any) -> str:
    if value is None:
        return ''

    text = str(value).strip()
    if not text:
        return ''

    normalized = unicodedata.normalize('NFKD', text)
    without_accents = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    sanitized = (
        without_accents
        .lower()
        .replace('%', '')
        .replace('-', ' ')
        .replace('/', ' ')
    )
    return '_'.join(sanitized.split())


def _decode_csv_bytes(data: bytes) -> io.StringIO:
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = data.decode('latin-1')
    return io.StringIO(text)


def _load_dataframe(file_bytes: bytes, extension: str) -> pd.DataFrame:
    if extension == '.csv':
        buffer = _decode_csv_bytes(file_bytes)
        df = pd.read_csv(buffer, sep=None, engine='python')
    else:
        buffer = io.BytesIO(file_bytes)
        df = pd.read_excel(buffer, engine='openpyxl')
    return df


def _sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ImportacaoArquivoErro('Arquivo sem dados para processar.')

    df = df.dropna(how='all')
    df.columns = [str(col).strip() for col in df.columns]

    if not df.columns.tolist() or len(df.columns) < 3:
        raise ImportacaoArquivoErro('Arquivo deve conter pelo menos tres colunas: indicador e dois periodos.')

    if not df.columns[0]:
        df.columns = ['Indicador'] + list(df.columns[1:])

    primeiro_header = _normalize_header(df.columns[0])
    if primeiro_header not in {'indicador', 'indice', ''}:
        raise ImportacaoArquivoErro('Primeira coluna deve corresponder ao indicador.')

    return df


def _convert_numeric(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace('%', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace('\u00a0', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    return pd.to_numeric(cleaned, errors='coerce')


def _build_payload(df: pd.DataFrame) -> Dict[str, Any]:
    indicador_col = df.columns[0]
    periodo1_col = df.columns[1]
    periodo2_col = df.columns[2]

    periodo1_label = str(periodo1_col).strip() or 'Periodo 1'
    periodo2_label = str(periodo2_col).strip() or 'Periodo 2'

    df[indicador_col] = df[indicador_col].astype(str).str.strip()
    df = df[df[indicador_col] != '']

    df[periodo1_col] = _convert_numeric(df[periodo1_col])
    df[periodo2_col] = _convert_numeric(df[periodo2_col])

    indicadores = []
    for _, row in df.iterrows():
        valor1 = row[periodo1_col]
        valor2 = row[periodo2_col]

        diff_abs = None
        if pd.notna(valor1) and pd.notna(valor2):
            diff_abs = valor2 - valor1

        if diff_abs is not None and pd.isna(diff_abs):
            diff_abs = None

        if valor1 in [None, 0] or pd.isna(valor1):
            diff_pct = None
        elif pd.isna(valor2):
            diff_pct = None
        else:
            diff_pct = ((valor2 - valor1) / valor1) * 100

        tendencia = 'flat'
        if diff_abs is not None:
            if diff_abs > 0:
                tendencia = 'up'
            elif diff_abs < 0:
                tendencia = 'down'

        indicadores.append({
            'indicador': row[indicador_col],
            'valor_periodo_1': None if pd.isna(valor1) else float(valor1),
            'valor_periodo_2': None if pd.isna(valor2) else float(valor2),
            'diferenca_absoluta': None if diff_abs is None else float(diff_abs),
            'diferenca_percentual': None if diff_pct is None or pd.isna(diff_pct) else float(diff_pct),
            'tendencia': tendencia
        })

    return {
        'periodo_1_label': periodo1_label,
        'periodo_2_label': periodo2_label,
        'total_indicadores': len(indicadores),
        'indicadores': indicadores
    }


def process_workflow_upload(file: FileStorage, workflow_id: int, upload_root: Path) -> Dict[str, Any]:
    if not file or not file.filename:
        raise ImportacaoArquivoErro('Nenhum arquivo foi enviado.')

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ImportacaoArquivoErro('Formato invalido. Utilize arquivos CSV ou XLSX.')

    safe_name = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    stored_name = f"{workflow_id}_{timestamp}_{safe_name}"

    upload_root.mkdir(parents=True, exist_ok=True)

    file.stream.seek(0)
    file_bytes = file.stream.read()

    try:
        dataframe = _load_dataframe(file_bytes, extension)
        dataframe = _sanitize_dataframe(dataframe)
        payload = _build_payload(dataframe)
    except ImportacaoArquivoErro:
        raise
    except Exception as exc:
        raise ImportacaoArquivoErro('Falha ao processar o arquivo. Confirme o layout e tente novamente.') from exc

    destino = upload_root / stored_name
    with open(destino, 'wb') as output_file:
        output_file.write(file_bytes)

    return {
        'arquivo_salvo': destino,
        'nome_arquivo': safe_name,
        'payload': payload
    }