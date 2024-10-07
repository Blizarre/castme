.PHONY: lint env

lint:
	poetry run isort .
	poetry run black .
	poetry run ruff check .

env:
	poetry install
