# Code review

This review covers the initial repository state. Issues are ordered by business impact; the first two are fixed in this submission.

## 1. Any authenticated user could modify any task

- **Location:** `backend/projects/views.py:164-185`
- **Category:** Security
- **Severity:** Critical

`TaskDetailView.patch` loaded a task and saved arbitrary changes without checking that the caller belonged to its project. An authenticated user could therefore change another team's title, status, description, or assignee by guessing or obtaining a task UUID. The fix verifies membership and role before mutation, and rejects assignees who are not project members.

Before the fix, with a valid token for a user who is not a member of the task's project:

```bash
curl -i -X PATCH "http://localhost:8000/api/tasks/<other-project-task-id>" \
  -H "Authorization: Bearer <non-member-token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"changed by outsider"}'
```

The vulnerable endpoint returned `HTTP/1.1 200 OK` with the changed task. After the fix, the same request returns:

```http
HTTP/1.1 403 Forbidden

{"error":"forbidden"}
```

## 2. Task search was vulnerable to SQL injection

- **Location:** `backend/projects/views.py:110-123`
- **Category:** Security
- **Severity:** High

The `q` parameter was interpolated directly into a raw SQL string, making quotes and operators part of the query rather than search text. This could expose task records or cause a database error; it also bypassed the serializer response shape used by the normal list endpoint. The implementation now uses Django ORM filters, which parameterize user input.

## 3. Task assignment did not enforce project membership

- **Location:** `backend/projects/views.py:151-160, 180-181`
- **Category:** Data Integrity
- **Severity:** Medium

Both create and update accepted an arbitrary `assigneeId`, so a task could be assigned to an account with no access to its project. That creates an inconsistent board and can disclose task metadata through future notification or assignment features. Both paths now validate assignee membership before saving.

## 4. The advertised Airtable export was a no-op

- **Location:** `backend/projects/views.py:234-243`
- **Category:** Architecture
- **Severity:** Medium

The endpoint authorized callers and returned serialized tasks, but made no Airtable API request and always reported zero exported records. This leaves users believing an export succeeded when no external data exists. The new adapter uses `pyairtable`, retries transient failures, keeps processing after an individual error, and stores the Airtable record ID for idempotent re-runs.
