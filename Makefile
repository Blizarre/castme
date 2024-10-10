.PHONY: lint env

lint:
	poetry run isort --check .
	poetry run black --check .
	poetry run ruff check .
	poetry run mypy .

dev:
	poetry run isort .
	poetry run black .
	poetry run ruff check .
	poetry run mypy .

env:
	poetry install
