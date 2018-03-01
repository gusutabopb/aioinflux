test:
	pytest --verbose --cov=aioinflux --cov-report html tests/

cov: test
	open htmlcov/index.html

clean:
	rm -rf build dist *.egg-info
	rm -rf .cache htmlcov .coverage .pytest_cache
	rm -f .DS_Store

build: clean test
	python setup.py sdist bdist_wheel

upload: build
	twine upload dist/*

upload-test: build
	twine upload --repository testpypi dist/*
