"""Small, testable adapter around the real Airtable API."""
import os
import json
import subprocess
import time
from pathlib import Path


class AirtableExportError(Exception):
    pass


def _load_local_env():
    """Load local development values when Django was started outside Compose."""
    env_path = Path(__file__).resolve().parents[2] / '.env'
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _is_transient(error):
    status_code = getattr(error, 'status_code', None)
    if status_code == 429 or (isinstance(status_code, int) and status_code >= 500):
        return True

    # The Airtable Node client does not expose an HTTP status when its request
    # fails before a response is received (for example, a connection reset or
    # timeout). Those failures are safe to retry just like 5xx responses.
    message = str(error).lower()
    return (
        'request to https://api.airtable.com/' in message
        or 'network' in message
        or 'econnreset' in message
        or 'etimedout' in message
    )


def get_table():
    _load_local_env()
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    table_name = os.environ.get('AIRTABLE_TABLE_NAME', 'Tasks')
    if not api_key or not base_id:
        raise AirtableExportError('Airtable is not configured')
    return NpmAirtableTable(api_key, base_id, table_name)


class NpmAirtableTable:
    """Small server-side bridge to the official Airtable npm package."""

    def __init__(self, api_key, base_id, table_name):
        self.api_key = api_key
        self.base_id = base_id
        self.table_name = table_name

    def _run(self, fields, record_id=None):
        payload = {
            'apiKey': self.api_key,
            'baseId': self.base_id,
            'tableName': self.table_name,
            'fields': fields,
            'recordId': record_id,
        }
        client = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'airtable_client.mjs')
        result = subprocess.run(
            ['node', client], input=json.dumps(payload), text=True,
            capture_output=True, check=False,
        )
        if result.returncode:
            try:
                detail = json.loads(result.stderr)
                error = RuntimeError(detail.get('message', 'Airtable request failed'))
                error.status_code = detail.get('statusCode')
                raise error
            except json.JSONDecodeError:
                raise RuntimeError(result.stderr or 'Airtable request failed')
        return json.loads(result.stdout)

    def create(self, fields, typecast=True):
        return self._run(fields)

    def update(self, record_id, fields, typecast=True):
        return self._run(fields, record_id)


def task_fields(task):
    return {
        'TaskBoard ID': str(task.id),
        'Title': task.title,
        'Description': task.description or '',
        'Status': task.status,
        'Assignee': task.assignee.email if task.assignee else '',
        'Created At': task.created_at.isoformat(),
        'Updated At': task.updated_at.isoformat(),
    }


def export_task(table, task, retries=2):
    """Create or update one task, retrying only transient provider errors."""
    for attempt in range(retries + 1):
        try:
            if task.airtable_record_id:
                table.update(task.airtable_record_id, task_fields(task), typecast=True)
                return 'updated'
            record = table.create(task_fields(task), typecast=True)
            task.airtable_record_id = record['id']
            task.save(update_fields=['airtable_record_id'])
            return 'created'
        except Exception as error:
            if not _is_transient(error) or attempt == retries:
                raise AirtableExportError(str(error)) from error
            time.sleep(0.25 * (2 ** attempt))
