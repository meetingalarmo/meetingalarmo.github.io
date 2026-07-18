.DEFAULT_GOAL := help

.PHONY: help test

help:
	@echo "Available targets:"
	@echo "  make test  Validate the public legal pages"

test:
	python3 -m unittest discover -s tests -p 'test_*.py'
