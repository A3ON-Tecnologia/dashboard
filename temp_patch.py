from pathlib import Path
path = Path('app/templates/workflow_view.html')
text = path.read_text(encoding='utf-8')
text = text.replace("workflow.data_criacao.strftime('%d/%m/%Y %H:%M')", "workflow.data_criacao|datetime_sp('%d/%m/%Y %H:%M')")
text = text.replace("arquivo_atual.data_upload.strftime('%d/%m/%Y %H:%M')", "arquivo_atual.data_upload|datetime_sp('%d/%m/%Y %H:%M')")
path.write_text(text, encoding='utf-8')
