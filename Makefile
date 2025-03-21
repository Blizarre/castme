.PHONY: lint dev env test release

VERSION?=$(error Please set the VERSION flag)

lint: test
	poetry run isort --check .
	poetry run black --check .
	poetry run ruff check .
	poetry run mypy . --check-untyped-defs

env: env_installed

env_installed: poetry.lock
	poetry install --with=dev
	touch env_installed

poetry.lock: pyproject.toml
	poetry lock --no-update

dev: test
	poetry run isort .
	poetry run black .
	poetry run ruff check .
	poetry run mypy . --check-untyped-defs

test: env
	poetry run pytest -vv

release:
	poetry version "$(VERSION)"
	git add pyproject.toml
	git commit -m "Bumping version $(VERSION)"
	git tag -a "$(VERSION)" -m "Version bump to $(VERSION)"
	git push --follow-tags
