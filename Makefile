.PHONY: init build migrate user run update-deps

init:
	poetry install --all-extras

build:
	poetry build

migrate:
	poetry run python manage.py migrate

static:
	poetry run python manage.py collectstatic --no-input

user:
	poetry run python create_user.py -u kai -p deptrai

run:
	gunicorn testproject.wsgi:application -b 0.0.0.0:8000 -w 1 -k eventlet --reload

update-deps:
	poetry update
