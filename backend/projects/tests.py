import pytest
from rest_framework.test import APIClient
from users.models import User
from projects.models import Project, Membership, Task, Comment


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email='meera@taskboard.dev', name='Meera Iyer', password='password123')


@pytest.fixture
def auth_client(client, user):
    response = client.post('/api/auth/login', {
        'email': 'meera@taskboard.dev',
        'password': 'password123',
    }, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['token']}")
    return client


@pytest.mark.django_db
class TestProjects:
    def test_create_project(self, auth_client, user):
        response = auth_client.post('/api/projects', {'name': 'My Project'}, format='json')
        assert response.status_code == 201
        assert response.data['project']['name'] == 'My Project'

    def test_list_only_returns_member_projects(self, auth_client, user):
        p1 = Project.objects.create(name='Mine', owner=user)
        Membership.objects.create(user=user, project=p1, role='admin')
        other = User.objects.create_user(email='other@example.com', name='Other', password='password123')
        p2 = Project.objects.create(name='Not Mine', owner=other)
        Membership.objects.create(user=other, project=p2, role='admin')

        response = auth_client.get('/api/projects')
        assert response.status_code == 200
        names = [p['name'] for p in response.data['projects']]
        assert 'Mine' in names
        assert 'Not Mine' not in names

    def test_get_project_detail(self, auth_client, user):
        project = Project.objects.create(name='My Project', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')

        response = auth_client.get(f'/api/projects/{project.id}')
        assert response.status_code == 200
        assert response.data['project']['name'] == 'My Project'

    def test_non_member_cannot_view_project(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='Private', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')

        resp = client.post('/api/auth/login', {'email': 'meera@taskboard.dev', 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")

        response = client.get(f'/api/projects/{project.id}')
        assert response.status_code == 403


@pytest.mark.django_db
class TestTasks:
    def test_create_task(self, auth_client, user):
        project = Project.objects.create(name='P', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')

        response = auth_client.post(f'/api/projects/{project.id}/tasks', {'title': 'Do a thing'}, format='json')
        assert response.status_code == 201
        assert response.data['task']['title'] == 'Do a thing'

    def test_viewers_cannot_create_tasks(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='P', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        Membership.objects.create(user=user, project=project, role='viewer')

        resp = client.post('/api/auth/login', {'email': 'meera@taskboard.dev', 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")

        response = client.post(f'/api/projects/{project.id}/tasks', {'title': 'A task'}, format='json')
        assert response.status_code == 403

    def test_delete_task_requires_membership(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='P', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        task = Task.objects.create(project=project, title='A task', created_by=owner)

        resp = client.post('/api/auth/login', {'email': 'meera@taskboard.dev', 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")

        response = client.delete(f'/api/tasks/{task.id}')
        assert response.status_code == 403

    def test_non_member_cannot_update_task(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='P', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        task = Task.objects.create(project=project, title='Private task', created_by=owner)
        resp = client.post('/api/auth/login', {'email': user.email, 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")

        response = client.patch(f'/api/tasks/{task.id}', {'title': 'Stolen'}, format='json')
        assert response.status_code == 403
        task.refresh_from_db()
        assert task.title == 'Private task'

    def test_search_treats_injection_as_plain_text(self, auth_client, user):
        project = Project.objects.create(name='P', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')
        Task.objects.create(project=project, title='Safe task', created_by=user)

        response = auth_client.get(f"/api/projects/{project.id}/tasks?q=' OR 1=1 --")
        assert response.status_code == 200
        assert response.data['tasks'] == []


@pytest.mark.django_db
class TestComments:
    def test_member_can_add_chronological_comment_and_viewer_cannot_post(self, client, auth_client, user):
        project = Project.objects.create(name='P', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')
        viewer = User.objects.create_user(email='viewer@example.com', name='Viewer', password='password123')
        Membership.objects.create(user=viewer, project=project, role='viewer')
        task = Task.objects.create(project=project, title='Task', created_by=user)

        response = auth_client.post(f'/api/tasks/{task.id}/comments', {'body': 'First note'}, format='json')
        assert response.status_code == 201
        assert response.data['comment']['author']['email'] == user.email
        assert [comment['body'] for comment in response.data['comments']] == ['First note']
        assert Comment.objects.filter(task=task).count() == 1

        login = client.post('/api/auth/login', {'email': viewer.email, 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
        response = client.post(f'/api/tasks/{task.id}/comments', {'body': 'I should not post'}, format='json')
        assert response.status_code == 403
        response = client.get(f'/api/tasks/{task.id}/comments')
        assert response.status_code == 200
        assert [comment['body'] for comment in response.data['comments']] == ['First note']


@pytest.mark.django_db
class TestAirtableExport:
    def test_export_is_idempotent_and_continues_after_one_failure(self, auth_client, user, monkeypatch):
        project = Project.objects.create(name='P', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')
        first = Task.objects.create(project=project, title='First', created_by=user)
        second = Task.objects.create(project=project, title='Second', created_by=user)

        class Table:
            def create(self, fields, typecast=True):
                if fields['Title'] == 'Second':
                    raise ValueError('invalid record')
                return {'id': 'rec_first'}
            def update(self, record_id, fields, typecast=True):
                assert record_id == 'rec_first'

        monkeypatch.setattr('projects.views.get_table', lambda: Table())
        response = auth_client.post(f'/api/projects/{project.id}/export')
        assert response.status_code == 200
        assert response.data['created'] == 1
        assert len(response.data['failed']) == 1
        first.refresh_from_db()
        assert first.airtable_record_id == 'rec_first'

        response = auth_client.post(f'/api/projects/{project.id}/export')
        assert response.status_code == 200
        assert response.data['updated'] == 1
