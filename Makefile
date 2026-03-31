.PHONY: tests lint format

tests:
	@uv run -m pytest --cov --cov-config=.coveragerc  --cov-report term --cov-report xml:./coverage-reports/coverage.xml -s tests/

lint:
	@uvx ruff check --extend-select I --fix bigdata_thematic_screener/ tests/

lint-check:
	@uvx ruff check --extend-select I bigdata_thematic_screener/ tests/

format:
	@uvx ruff format bigdata_thematic_screener/ tests/

format-check:
	@uvx ruff format --check bigdata_thematic_screener/ tests/

type-check:
	@uvx ty@0.0.1-alpha.25 check bigdata_thematic_screener/ tests/