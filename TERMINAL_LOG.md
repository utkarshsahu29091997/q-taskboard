# Terminal log

## Setup

```text
git clone https://github.com/ajackus/q-taskboard.git
python3.11 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
npm install --prefix frontend
```

## Verification

```text
DJANGO_SETTINGS_MODULE=taskboard.settings_test .venv/bin/python -m pytest backend/projects/tests.py
11 passed

npm test --prefix frontend
2 test files passed, 9 tests passed

npm run build --prefix frontend
✓ built in 526ms

DJANGO_SETTINGS_MODULE=taskboard.settings_test .venv/bin/python backend/manage.py makemigrations --check --dry-run
No changes detected
```

## Runtime checks still required

Docker and a local PostgreSQL service were unavailable in this environment, so an HTTP curl session against the running stack could not be recorded here. The precise pre-/post-fix curl reproduction is in `REVIEW.md`.

No Airtable credentials were supplied. Configure `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, and `AIRTABLE_TABLE_NAME`, then run the app and use **Export to Airtable** from a project as an admin or member. Run it twice to verify that saved Airtable record IDs cause updates rather than duplicate creates.
