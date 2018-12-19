HTMLCOV_DIR ?= htmlcov

# test
coverage-html:
	coverage html -d $(HTMLCOV_DIR) --fail-under 100

coverage-report:
	coverage report -m

test:
	coverage run -m pytest test $(ARGS)

coverage: test coverage-report coverage-html