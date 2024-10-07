.PHONY: lint env

lint:
	poetry run isort -c .
	poetry run black -c .
	poetry run ruff check .

dev:
	poetry run isort .
	poetry run black .
	poetry run ruff check .

env:
	poetry install
