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
docker compose exec django-docker python manage.py migrate
```

6. Create a superuser

```
docker compose exec django-docker manage.py createsuperuser
```

7. Create staticfiles (Styles, Images, etc.)

```
docker compose exec django-docker python manage.py collectstatic
```

8. Create seeders

```
docker compose exec django-docker python manage.py seeders
```

## Production

Build a production-ready stack that serves the Django application through
Nginx:

1. Ensure a `.env` file with the required settings exists in the project
   root.
2. Build and start the services:

   ```
   docker compose -f compose.prod.yml up --build
   ```
3. Apply database migrations:

   ```
   docker compose -f compose.prod.yml exec django python manage.py migrate
   ```

Nginx will expose the application on port `80`.

