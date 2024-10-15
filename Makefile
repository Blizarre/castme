.PHONY: lint env

lint:
	poetry run isort --check .
	poetry run black --check .
	poetry run ruff check .
	poetry run mypy . --check-untyped-defs

dev:
	poetry run isort .
	poetry run black .
	poetry run ruff check .
	poetry run mypy . --check-untyped-defs

env:
	poetry install
