import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Iterable, Set

import pandas as pd
from flask import Blueprint, current_app, jsonify, redirect, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from sqlalchemy import distinct
from sqlalchemy.orm import defer

from app import db
from app.models.analise_upload import AnaliseUpload
from app.models.workflow import Workflow
from app.services.theme_service import get_theme_context


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


def _serialize_upload(upload: AnaliseUpload, include_data: bool = False) -> Dict[str, object]:
    payload: Dict[str, object] = {
        'id': upload.id,
        'workflow_id': upload.workflow_id,
        'categoria': upload.categoria,
        'nome_arquivo': upload.nome_arquivo,
        'caminho_arquivo': upload.caminho_arquivo,
        'linhas_ocultas': _normalise_indices(upload.linhas_ocultas or []),
        'created_at': upload.created_at.isoformat() if upload.created_at else None,
        'data_upload': upload.data_upload.isoformat() if upload.data_upload else None,
    }

    if include_data:
        payload['dados_extraidos'] = (
            upload.dados_extraidos if isinstance(upload.dados_extraidos, list) else []
        )

    return payload


def build_analise_jp_dashboard_context(workflow: Workflow) -> Dict[str, object]:
    theme = get_theme_context()
    existing_categories = {
        row[0]
        for row in (
            db.session.query(distinct(AnaliseUpload.categoria))
            .filter_by(workflow_id=workflow.id)
            .all()
        )
    }
    category_status = {
        categoria: categoria in existing_categories
        for categoria in ANALISE_JP_CATEGORIES
    }
    return {
        'workflow': workflow,
        'theme': theme,
        'categories': ANALISE_JP_CATEGORIES,
        'category_status': category_status,
    }


def _validate_category(categoria: str) -> None:
    if categoria not in ANALISE_JP_CATEGORIES:
        raise ValueError('Categoria invalida.')


def _slug_to_label(slug: str) -> str:
    parts = [part.capitalize() for part in slug.split('_') if part]
    return ' '.join(parts) if parts else slug


def _get_latest_upload_for_category(
    workflow_id: int,
    categoria: str,
    *,
    include_data: bool = True,
) -> Optional[AnaliseUpload]:
    query = (
        AnaliseUpload.query
        .filter_by(workflow_id=workflow_id, categoria=categoria)
        .order_by(AnaliseUpload.created_at.desc())
    )

    if not include_data:
        query = query.options(defer(AnaliseUpload.dados_extraidos))

    return query.first()


def _normalise_indices(values: Iterable) -> List[int]:
    indices: Set[int] = set()
    for value in values or []:
        try:
            index = int(value)
        except (TypeError, ValueError):
            continue
        if index < 0:
            continue
        indices.add(index)
    return sorted(indices)


def _get_hidden_index_set(upload: Optional[AnaliseUpload]) -> Set[int]:
    if not upload or not upload.linhas_ocultas:
        return set()
    return set(_normalise_indices(upload.linhas_ocultas))


def _get_visible_records(upload: Optional[AnaliseUpload]) -> List[dict]:
    if not upload or not isinstance(upload.dados_extraidos, list):
        return []

    hidden_indices = _get_hidden_index_set(upload)
    visible: List[dict] = []
    for index, record in enumerate(upload.dados_extraidos):
        if index in hidden_indices:
            continue
        if isinstance(record, dict):
            visible.append(record)
    return visible


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


@analise_jp_bp.route('/analise_jp/<int:workflow_id>')
@login_required
def analise_jp_view(workflow_id: int):
    workflow = _get_workflow_or_404(workflow_id)
    return redirect(url_for('workflow.workflow_view', workflow_nome=workflow.nome), code=302)


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/graficos')
@login_required
def analise_jp_charts_view(workflow_id: int):
    workflow = _get_workflow_or_404(workflow_id)
    return redirect(url_for('workflow.workflow_view', workflow_nome=workflow.nome), code=302)


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/uploads/<string:categoria>', methods=['GET'])
@login_required
def listar_uploads(workflow_id: int, categoria: str):
    workflow = _get_workflow_or_404(workflow_id)
    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    uploads = (
        AnaliseUpload.query
        .options(defer(AnaliseUpload.dados_extraidos))
        .filter_by(workflow_id=workflow.id, categoria=categoria)
        .order_by(AnaliseUpload.created_at.desc())
        .all()
    )

    return jsonify({'uploads': [_serialize_upload(upload) for upload in uploads]})


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/api/categorias/<string:categoria>/dataset', methods=['GET'])
@login_required
def obter_dataset_categoria(workflow_id: int, categoria: str):
    workflow = _get_workflow_or_404(workflow_id)
    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    upload = _get_latest_upload_for_category(workflow.id, categoria)
    if not upload or not upload.dados_extraidos:
        return jsonify({'error': 'Nenhum upload encontrado para a categoria selecionada.'}), 404

    records = upload.dados_extraidos if isinstance(upload.dados_extraidos, list) else []
    visible_records = _get_visible_records(upload)
    total_records = len(records)
    fields: List[str] = []
    reference_records = visible_records if visible_records else records
    for record in reference_records:
        if isinstance(record, dict):
            fields = list(record.keys())
            break

    return jsonify({
        'categoria': categoria,
        'categoria_label': _slug_to_label(categoria),
        'record_count': len(visible_records),
        'total_records': total_records,
        'hidden_count': total_records - len(visible_records),
        'linhas_ocultas': _normalise_indices(upload.linhas_ocultas or []),
        'fields': fields,
        'records': visible_records,
        'upload': {
            'id': upload.id,
            'nome_arquivo': upload.nome_arquivo,
            'created_at': upload.created_at.isoformat() if upload.created_at else None
        }
    })


@analise_jp_bp.route(
    '/analise_jp/<int:workflow_id>/uploads/<string:categoria>/<int:upload_id>/dataset',
    methods=['GET']
)
@login_required
def obter_dataset_upload(workflow_id: int, categoria: str, upload_id: int):
    workflow = _get_workflow_or_404(workflow_id)
    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    upload = (
        AnaliseUpload.query
        .filter_by(id=upload_id, workflow_id=workflow.id, categoria=categoria)
        .first()
    )

    if not upload:
        return jsonify({'error': 'Upload nao encontrado.'}), 404

    payload = _serialize_upload(upload, include_data=True)

    return jsonify({'upload': payload})


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
        dados_extraidos=registros,
        linhas_ocultas=[]
    )

    db.session.add(upload)
    db.session.commit()

    payload = _serialize_upload(upload, include_data=True)

    return jsonify({'message': 'Upload realizado com sucesso!', 'upload': payload}), 201


@analise_jp_bp.route(
    '/analise_jp/<int:workflow_id>/uploads/<string:categoria>/<int:upload_id>',
    methods=['DELETE']
)
@login_required
def excluir_upload(workflow_id: int, categoria: str, upload_id: int):
    workflow = _get_workflow_or_404(workflow_id)
    if workflow.tipo != 'analise_jp':
        return jsonify({'error': 'Workflow nao suporta exclusao de uploads de analise_jp.'}), 400

    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    upload = (
        AnaliseUpload.query
        .filter_by(id=upload_id, workflow_id=workflow.id, categoria=categoria)
        .first()
    )

    if not upload:
        return jsonify({'error': 'Upload nao encontrado.'}), 404

    file_path = Path(upload.caminho_arquivo)
    try:
        if file_path.exists():
            file_path.unlink()
    except OSError:
        current_app.logger.exception('Falha ao remover arquivo do upload %s', upload_id)
        return jsonify({'error': 'Nao foi possivel remover o arquivo associado ao upload.'}), 500

    db.session.delete(upload)
    db.session.commit()

    return jsonify({'message': 'Upload removido com sucesso.'}), 200


@analise_jp_bp.route(
    '/analise_jp/<int:workflow_id>/uploads/<string:categoria>/<int:upload_id>/linhas_ocultas',
    methods=['POST']
)
@login_required
def atualizar_linhas_ocultas(workflow_id: int, categoria: str, upload_id: int):
    workflow = _get_workflow_or_404(workflow_id)
    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    upload = (
        AnaliseUpload.query
        .filter_by(id=upload_id, workflow_id=workflow.id, categoria=categoria)
        .first()
    )

    if not upload:
        return jsonify({'error': 'Upload nao encontrado.'}), 404

    payload = request.get_json() or {}
    action = (payload.get('acao') or '').strip().lower()
    indices = payload.get('indices')

    if action not in {'ocultar', 'restaurar'}:
        return jsonify({'error': 'Acao invalida. Utilize "ocultar" ou "restaurar".'}), 400

    if not isinstance(indices, list):
        return jsonify({'error': 'Informe os indices das linhas.'}), 400

    total_records = len(upload.dados_extraidos or [])
    cleaned_indices = []
    for value in indices:
        try:
            index = int(value)
        except (TypeError, ValueError):
            continue
        if index < 0 or index >= total_records:
            continue
        cleaned_indices.append(index)

    if not cleaned_indices:
        return jsonify({'error': 'Nenhuma linha valida informada.'}), 400

    hidden_indices = _get_hidden_index_set(upload)

    if action == 'ocultar':
        hidden_indices.update(cleaned_indices)
        message = 'Linha ocultada com sucesso.' if len(cleaned_indices) == 1 else 'Linhas ocultadas com sucesso.'
    else:
        hidden_indices.difference_update(cleaned_indices)
        message = 'Linha restaurada com sucesso.' if len(cleaned_indices) == 1 else 'Linhas restauradas com sucesso.'

    upload.linhas_ocultas = sorted(hidden_indices)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Falha ao atualizar linhas ocultas do upload %s', upload_id)
        return jsonify({'error': 'Nao foi possivel atualizar as linhas ocultas.'}), 500

    visible_records = _get_visible_records(upload)

    return jsonify({
        'message': message,
        'linhas_ocultas': upload.linhas_ocultas,
        'registros_visiveis': visible_records,
        'total_registros': total_records,
        'hidden_count': total_records - len(visible_records)
    })


