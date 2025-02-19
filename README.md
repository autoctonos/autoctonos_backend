# Development Guide

This guide will help you set up and run the project in a development environment.

## Prerequisites

- Docker and Docker Compose
- Git

## Setup 

2. Copy a `.env-dev` file in the root directory and rename it to `.env` and fill with your own values.


3. Run the development server:

```
docker compose up --build
```
4. Make Migrations

```
docker exec -it django-docker python manage.py makemigrations
```

5. Migrations

```
docker compose exec django-web python manage.py migrate
```

6. Create a superuser

```
docker compose exec app python manage.py createsuperuser
```

7. Create staticfiles (Styles, Images, etc.)

```
docker compose exec app python manage.py collectstatic
```

