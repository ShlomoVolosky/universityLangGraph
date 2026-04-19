PYTHON   := python3
PIP      := $(HOME)/.local/bin/pip
RUFF     := $(HOME)/.local/bin/ruff
MYPY     := $(HOME)/.local/bin/mypy
PYTEST   := $(PYTHON) -m pytest

.PHONY: test test-all lint seed seed-force run install format

install:
	$(PIP) install -e ".[dev]"

seed:
	$(PYTHON) scripts/init_db.py

seed-force:
	$(PYTHON) scripts/init_db.py --force

test:
	$(PYTEST) tests/unit tests/integration -v; exit_code=$$?; [ $$exit_code -eq 5 ] && exit 0 || exit $$exit_code

test-all:
	$(PYTEST) tests/ -v -m ""

lint:
	$(RUFF) check .
	$(RUFF) format --check .
	$(MYPY) src/university_qa/domain src/university_qa/ports src/university_qa/agent

format:
	$(RUFF) format .
	$(RUFF) check --fix .

run:
	@echo "Usage: $(PYTHON) -m university_qa.cli \"<your question>\""
	@echo "Example: $(PYTHON) -m university_qa.cli \"How many students are there?\""
