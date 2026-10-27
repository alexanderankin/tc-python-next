all:

ifeq ($(OS),Windows_NT)
venv: ./.venv/Scripts/activate.bat
ACTIVATE = source ./.venv/Scripts/activate.bat

./.venv/Scripts/activate.bat:
	python -m venv .venv
	$(ACTIVATE); pip install -U pip; pip install -e . --group dev
else
venv: ./.venv/bin/activate
ACTIVATE = source ./.venv/bin/activate

./.venv/bin/activate:
	python -m venv .venv
	$(ACTIVATE); pip install -U pip; pip install -e . --group dev
endif

format: venv
	$(ACTIVATE); ruff format
