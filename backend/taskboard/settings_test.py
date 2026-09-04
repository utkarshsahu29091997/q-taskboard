"""SQLite settings for the fast, self-contained test suite."""
import os

from .settings import *  # noqa: F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('SQLITE_DB_PATH', ':memory:'),
    }
}
