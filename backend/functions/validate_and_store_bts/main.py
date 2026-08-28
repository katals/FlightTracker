import functions_framework
from google.cloud import storage
import csv
import tempfile
import os

@functions_framework.http
def validate_and_store_bts(request):
    if 'file' not in request.files:
        return "No se envió ningún archivo", 400

    file = request.files['file']
    if file.filename == '':
        return "Nombre de archivo vacío", 400

    if not file.filename.endswith('.csv'):
        return "Solo se permiten archivos CSV", 400

    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # Validate header using csv.DictReader (no pandas)
        with open(tmp_path, newline='', encoding='utf-8') as source:
            headers = set((csv.DictReader(source).fieldnames or []))

        required_columns = {'FL_DATE', 'OP_CARRIER_FL_NUM', 'ORIGIN', 'DEST'}
        has_carrier = 'OP_CARRIER' in headers or 'OP_UNIQUE_CARRIER' in headers
        if not required_columns.issubset(headers) or not has_carrier:
            return "Estructura de CSV inválida", 400

        storage_client = storage.Client()
        bucket = storage_client.bucket('flighttracker-raw-bts')
        blob = bucket.blob(f"bts/{file.filename}")
        blob.upload_from_filename(tmp_path)

        return f"Archivo {file.filename} almacenado correctamente", 201

    except Exception as e:
        return f"Error procesando el archivo: {str(e)}", 500
    finally:
        os.unlink(tmp_path)
