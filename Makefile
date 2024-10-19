.PHONY: lint env

VERSION?=$(error Please set the VERSION flag)

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

release:
	poetry version "$(VERSION)"
	git add pyproject.toml
	git commit -m "Bumping version $(VERSION)"
	git tag -a "$(VERSION)" -m "Version bump to $(VERSION)"
	git push --follow-tags