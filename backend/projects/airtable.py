"""Small, testable adapter around the real Airtable API."""
import os
import time

from pyairtable import Api


class AirtableExportError(Exception):
    pass


def _is_transient(error):
    status_code = getattr(error, 'status_code', None)
    return status_code == 429 or (isinstance(status_code, int) and status_code >= 500)


def get_table():
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    table_name = os.environ.get('AIRTABLE_TABLE_NAME', 'Tasks')
    if not api_key or not base_id:
        raise AirtableExportError('Airtable is not configured')
    return Api(api_key).table(base_id, table_name)


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
