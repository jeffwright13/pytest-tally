.PHONY: venv test clean

clean: venv-delete
	echo Cleaning...

	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	find . -name '.pytest_cache' -delete
	find . -name '.coverage' -delete
	find . -name '.mypy_cache' -delete
	find . -name '.cache' -delete
	find . -name '.ipynb_checkpoints' -delete
	find . -name '.DS_Store' -delete
	find . -name 'coverage.xml' -delete
	find . -name 'htmlcov' -delete
	find . -name 'dist' -delete
	find . -name 'build' -delete
	find . -name '*.egg-info' -delete

venv:
	echo Making venv...

	pwd

	if [ -d "~/Dropbox" ]; then \
		echo "venv directory already exists"; \
		exit 1; \
	fi

	python3 -m venv venv
	. source venv/bin/activate
	venv/bin/pip install --upgrade pip setuptools wheel
	deactivate

venv-delete:
	echo Deleting venv...

	rm -rf venv

install:
	echo Installing requirements...

	pip install \
	-r requirements.txt

dev:
	echo Installing dev requirements...

	pip install \
	-r requirements.txt \
	-r requirements-dev.txt

compile:
	echo Compiling requirements...

	rm -f requirements*.txt
	pip-compile requirements.in
	pip-compile requirements-dev.in

sync:
	echo Syncing requirements...

	pip-sync requirements*.txt
