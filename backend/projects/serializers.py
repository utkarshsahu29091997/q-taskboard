from rest_framework import serializers
from users.serializers import UserSerializer
from .models import Project, Membership, Task, Comment


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'body', 'author', 'createdAt']


class TaskSerializer(serializers.ModelSerializer):
    assignee = UserSerializer(read_only=True)
    assigneeId = serializers.SerializerMethodField()
    projectId = serializers.SerializerMethodField()
    createdById = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    def get_assigneeId(self, obj):
        return str(obj.assignee_id) if obj.assignee_id else None

    def get_projectId(self, obj):
        return str(obj.project_id)

    def get_createdById(self, obj):
        return str(obj.created_by_id)

    class Meta:
        model = Task
        fields = [
            'id', 'projectId', 'title', 'description', 'status',
            'assigneeId', 'createdById', 'position', 'createdAt', 'updatedAt', 'assignee', 'comments',
        ]


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'role', 'user']


class ProjectDetailSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    ownerId = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    memberships = MembershipSerializer(many=True, read_only=True)
    tasks = TaskSerializer(many=True, read_only=True)

    def get_ownerId(self, obj):
        return str(obj.owner_id)

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'ownerId', 'owner', 'memberships', 'tasks', 'createdAt', 'updatedAt']
