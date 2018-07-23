test:
	flake8 --max-line-length=100 --ignore=F841
	pytest --verbose --cov=aioinflux --cov-append --cov-report html tests/

cov: test
	open htmlcov/index.html

clean:
	rm -rf build dist *.egg-info docs/_build/*
	rm -rf .cache htmlcov .coverage .pytest_cache
	rm -f .DS_Store README.html

docs: clean
	cd docs && $(MAKE) html

build: clean test docs
	python setup.py sdist bdist_wheel

upload: build
	twine upload dist/*

upload-test: build
	twine upload --repository testpypi dist/*
