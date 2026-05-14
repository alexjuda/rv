.PHONY: test format

test:
	uv run pytest

typecheck:
	uv run ty check .

format:
	uv run ruff format .
	uv run ruff check --fix --unsafe-fixes .
