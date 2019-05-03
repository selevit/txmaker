lint: isort flake8 mypy

run:
	python -X dev main.py

run-testnet:
	TESTNET=1 python -X dev main.py

isort:
	isort --recursive --check --skip .

flake8:
	flake8 --max-line-length=120 .

mypy:
	mypy --ignore-missing-imports .

fix: isort-fix

isort-fix:
	isort -rc .

.PHONY: lint run run-testnet isort flake8 mypy fix isort-fix
