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
2 test files passed, 10 tests passed

npm run build --prefix frontend
✓ production build completed

DJANGO_SETTINGS_MODULE=taskboard.settings_test .venv/bin/python backend/manage.py makemigrations --check --dry-run
No changes detected
```

## Live Airtable export demo

Docker and PostgreSQL were unavailable, so this demo used a freshly migrated and seeded **isolated SQLite database**. The running Django API was authenticated as `meera@taskboard.dev` and exported the seeded Q3 Launch project (7 tasks) to the configured Airtable table.

```text
First export:  {"created":7,"updated":0,"failed":[]}
Second export: {"created":0,"updated":7,"failed":[]}
```

The second result confirms that the stored Airtable record IDs update existing records rather than creating duplicates.

After migrating the adapter to the official `airtable` npm package, the same seeded project was exported again through the running Django endpoint:

```text
Npm-client export:        {"created":0,"updated":7,"failed":[]}
Second npm-client export: {"created":0,"updated":7,"failed":[]}
```

## HTTP bug proof

The exact vulnerable and fixed request shape, including the expected `200 OK` before the fix and `403 Forbidden` afterward, is documented in `REVIEW.md`. A pre-fix running-server capture still requires checking out the vulnerable revision in a separate environment; the current server correctly rejects the unauthorized request.
