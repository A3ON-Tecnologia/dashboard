import io
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app import db
from app.models.analise_upload import AnaliseUpload
from app.models.workflow import Workflow
from app.services.theme_service import get_theme_context
from sqlalchemy.exc import SQLAlchemyError


analise_jp_bp = Blueprint('analise_jp', __name__)

ANALISE_JP_CATEGORIES: List[str] = [
    'simples_nacional',
    'lucro_real',
    'banco_horas',
    'notas',
    'lucro_presumido',
    'departamento_pessoal',
    'colaboradores',
    'impostos_fiscal',
    'empresas_mes',
    'servicos_simples',
    'servicos_lucro_presumido',
    'servicos_contabil',
    'servicos_contabil_det',
]

ALLOWED_EXTENSIONS = {'.csv', '.xlsx'}


def _get_workflow_or_404(workflow_id: int) -> Workflow:
    return Workflow.query.filter_by(id=workflow_id, usuario_id=current_user.id).first_or_404()


def _validate_category(categoria: str) -> None:
    if categoria not in ANALISE_JP_CATEGORIES:
        raise ValueError('Categoria invalida.')


def _decode_csv_bytes(data: bytes) -> io.StringIO:
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = data.decode('latin-1')
    return io.StringIO(text)


def _load_dataframe(file_bytes: bytes, extension: str) -> pd.DataFrame:
    """
    Load the uploaded file into a dataframe preserving the original textual values.

    When pandas infers numeric types automatically, numbers such as 0.1034 can end up
    represented as 0.10339999999999999 due to floating point precision. For these
    uploads the goal is to keep the exact content provided in the CSV/XLSX templates
    so the data shown in the UI matches the spreadsheet. Reading everything as
    strings avoids unwanted conversions while still letting us normalise empty
    values later in the pipeline.
    """

    if extension == '.csv':
        buffer = _decode_csv_bytes(file_bytes)
        dataframe = pd.read_csv(
            buffer,
            sep=None,
            engine='python',
            dtype=str,
            keep_default_na=False,
        )
    else:
        buffer = io.BytesIO(file_bytes)
        dataframe = pd.read_excel(
            buffer,
            engine='openpyxl',
            dtype=str,
            na_filter=False,
        )

    dataframe = dataframe.dropna(how='all')
    return dataframe


def _dataframe_to_records(dataframe: pd.DataFrame) -> List[dict]:
    if dataframe.empty:
        raise ValueError('Arquivo sem dados para processar.')

    normalized_columns = []
    for idx, column in enumerate(dataframe.columns, start=1):
        header = str(column).strip()
        if not header:
            header = f'Coluna {idx}'
        normalized_columns.append(header)
    dataframe.columns = normalized_columns

    dataframe = dataframe.fillna('')
    records: List[dict] = []
    for _, row in dataframe.iterrows():
        if all(str(value).strip() == '' for value in row.values):
            continue
        record = {}
        for column in dataframe.columns:
            value = row[column]

            if value is None:
                cleaned_value = ''
            else:
                value_str = str(value)
                cleaned_value = value_str.strip()

            record[column] = cleaned_value
        records.append(record)

    if not records:
        raise ValueError('Nenhum dado valido encontrado no arquivo enviado.')

    return records


def _extract_payload(file: FileStorage) -> Tuple[List[dict], bytes]:
    filename = file.filename or ''
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError('Formato invalido. Utilize arquivos CSV ou XLSX.')

    file.stream.seek(0)
    file_bytes = file.stream.read()
    if not file_bytes:
        raise ValueError('Arquivo vazio.')

    dataframe = _load_dataframe(file_bytes, extension)
    records = _dataframe_to_records(dataframe)

    return records, file_bytes


def _load_template_upload(categoria: str) -> Optional[dict]:
    template_dir = current_app.config.get('ANALISE_JP_TEMPLATE_DIR')
    if not template_dir:
        return None

    template_path = Path(template_dir)
    if not template_path.exists() or not template_path.is_dir():
        return None

    candidate_files = [
        template_path / f'{categoria}.csv',
        template_path / f'{categoria}.xlsx'
    ]

    file_path = next((path for path in candidate_files if path.exists()), None)
    if not file_path:
        return None

    try:
        file_bytes = file_path.read_bytes()
        dataframe = _load_dataframe(file_bytes, file_path.suffix.lower())
        records = _dataframe_to_records(dataframe)
    except Exception:
        current_app.logger.exception('Falha ao carregar planilha modelo da categoria %s', categoria)
        return None

    return {
        'id': f'template::{categoria}',
        'workflow_id': None,
        'categoria': categoria,
        'nome_arquivo': file_path.name,
        'caminho_arquivo': str(file_path),
        'dados_extraidos': records,
        'created_at': datetime.utcnow().isoformat(),
        'is_template': True
    }


@analise_jp_bp.route('/analise_jp/<int:workflow_id>')
@login_required
def analise_jp_view(workflow_id: int):
    workflow = _get_workflow_or_404(workflow_id)
    if workflow.tipo != 'analise_jp':
        return redirect(url_for('workflow.workflow_view', workflow_nome=workflow.nome))

    theme = get_theme_context()
    return render_template(
        'analise_jp.html',
        workflow=workflow,
        theme=theme,
        categories=ANALISE_JP_CATEGORIES
    )


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/uploads/<string:categoria>', methods=['GET'])
@login_required
def listar_uploads(workflow_id: int, categoria: str):
    workflow = _get_workflow_or_404(workflow_id)
    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    try:
        uploads = (
            AnaliseUpload.query
            .filter_by(workflow_id=workflow.id, categoria=categoria)
            .order_by(AnaliseUpload.created_at.desc())
            .all()
        )
    except SQLAlchemyError:
        current_app.logger.exception('Falha ao consultar uploads da categoria %s', categoria)
        template_upload = _load_template_upload(categoria)
        if template_upload:
            return jsonify({
                'uploads': [template_upload],
                'warning': 'Não foi possível consultar os uploads salvos. Exibindo o modelo padrão da categoria.'
            })
        return jsonify({'error': 'Falha ao carregar uploads da categoria informada.'}), 500

    uploads_data = [upload.to_dict() for upload in uploads]
    if not uploads_data:
        template_upload = _load_template_upload(categoria)
        if template_upload:
            uploads_data.append(template_upload)

    return jsonify({'uploads': uploads_data})


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/upload/<string:categoria>', methods=['POST'])
@login_required
def upload_categoria(workflow_id: int, categoria: str):
    workflow = _get_workflow_or_404(workflow_id)
    if workflow.tipo != 'analise_jp':
        return jsonify({'error': 'Workflow nao suporta uploads de analise_jp.'}), 400

    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    arquivo = request.files.get('arquivo')
    if not arquivo or not arquivo.filename:
        return jsonify({'error': 'Nenhum arquivo foi enviado.'}), 400

    try:
        registros, file_bytes = _extract_payload(arquivo)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception:
        current_app.logger.exception('Falha ao processar upload da categoria %s', categoria)
        return jsonify({'error': 'Falha ao processar o arquivo enviado.'}), 500

    safe_name = secure_filename(arquivo.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    stored_name = f"{workflow_id}_{categoria}_{timestamp}_{safe_name}"

    upload_root = Path(current_app.config['UPLOAD_FOLDER'])
    destination = AnaliseUpload.build_storage_path(upload_root, workflow_id, categoria, stored_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(file_bytes)

    upload = AnaliseUpload(
        workflow_id=workflow.id,
        categoria=categoria,
        nome_arquivo=safe_name,
        caminho_arquivo=str(destination),
        dados_extraidos=registros
    )

    db.session.add(upload)
    db.session.commit()

    return jsonify({'message': 'Upload realizado com sucesso!', 'upload': upload.to_dict()}), 201
