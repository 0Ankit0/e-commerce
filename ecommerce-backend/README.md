# E-Commerce Backend

Django REST API backend with Auth, Payments, Subscriptions, Multi-tenancy, CMS & OpenAI.

## Features
- Authentication (JWT + Social Auth)
- Payments & Subscriptions (Stripe)
- Multi-tenancy
- CMS Integration (Contentful)
- OpenAI Integration
- Email (Django SES)
- Notifications

## Quick Start
1. pip install -r requirements.txt
2. Copy .env.example to .env and configure
3. python manage.py migrate
4. python manage.py createsuperuser
5. python manage.py runserver

## API Docs
- Swagger: http://localhost:8000/doc/
- ReDoc: http://localhost:8000/redoc/
