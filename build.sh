#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py makemigrations --no-input
python manage.py migrate
python manage.py load_municipios
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autoctonos.settings')
django.setup()
from users.models import Usuario
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
if username and not Usuario.objects.filter(username=username).exists():
    Usuario.objects.create_superuser(username, email, password)
    print(f'Superuser {username} created')
else:
    print('Superuser already exists or username not set')
"
