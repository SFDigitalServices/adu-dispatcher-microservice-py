web: pipenv run gunicorn 'service.microservice:start_service()'
release: pipenv run alembic upgrade head
worker: celery worker --app=tasks.app
crontab: celery -A tasks beat --loglevel=info