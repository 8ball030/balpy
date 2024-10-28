fmt: 
	poetry run isort samples tests 
	poetry run black samples tests
	poetry run autopep8 samples tests --recursive --in-place -a
	poetry run autoflake8 samples tests --recursive --remove-unused-variables --in-place

lint: 
	poetry run flake8 samples tests --max-line-length=150

test:
	poetry run pytest tests

all: fmt lint test