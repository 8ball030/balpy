fmt: 
	poetry run ruff format samples tests balpy
	poetry run ruff format samples tests balpy

lint: 
	poetry run ruff check samples tests balpy --fix

test:
	poetry run pytest tests

all: fmt lint test