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

4. Migrations

```
docker compose exec app python manage.py migrate
```

5. Create a superuser

```
docker compose exec app python manage.py createsuperuser
```

6. Create staticfiles

```
docker compose exec app python manage.py collectstatic
```

