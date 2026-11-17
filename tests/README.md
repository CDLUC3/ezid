Test EZID with PyTest
===========================

To perform EZID Unit test, you need to:
1. Prepare Python environment
2. Prepare MySQL environment
3. Setup the `DJANGO_SETTINGS_MODULE` environment variable
4. Create the test environment
5. Run `pytest` to perform the tests
6. Deactivate the Python virtual environment
7. Reactivate the Python virtual environment for testing

**Note:** perform the following steps in the EZID project directory.

## 1. Prepare Python environment

1. Set up & activate a Python virtual environment

```python
    python3 -m venv .test-venv

    source .test-venv/bin/activate
```

2. Run `pip install .` to source file `pyproject.toml` and install all dependencies listed there.

3. Run `pip install -r requirements-dev.txt` to install required packages for testing.

## 2. Prepare MySQL environment

1. Install MySQL
```
brew install mysql
```

2. Start mysql
```
brew services start mysql
```

## 3. Setup the `DJANGO_SETTINGS_MODULE` environment variable

There are a few ways to setup the `DJANGO_SETTINGS_MODULE` variable:

1. Use the `export` command. This tells Django to find configurations from file “ezid/settings/tests.py”.
```
$ export DJANGO_SETTINGS_MODULE=settings.tests
```

2. Use the `pytest` command line `--ds=SETTINGS` option:
```
$ pytest  --ds=settings.tests
```

## 4. Prepare the test environment

Run script `prepare_test_env.sh` to prepare test environment including:
- Create the `logs` directory
- Clone the `ezid-info-pages` repo
- Prepare the test database
- Collect static files

The script is in the ezid project directory. No parameters are required to run the script. Just hit the enter key when prompted for password. This is the default password for the test database.

```
./prepare_test_env.sh
Enter password:
``` 

## 5. Run Pytest
Test scripts and data files are organized in the `ezid/tests` directory. Test scripts are named in the `test_scriptname.py` format.

Run Pytest in the ezid project root directory:
```
pytest --ds=settings.tests tests/
```

To run a specific test script such as `test_api.py`:
```
pytest --ds=settings.tests tests/test_api.py
```

## 6. Deactivate the Python virtual environment
To deactivate the Python virtual environment:
```
deactivate
```

## 7. Reactivate the Python virtual environment for testing
To reactivate the Python virtual environment:
```
source .test-venv/bin/activate
```

Perform pytest:
```
pytest --ds=settings.tests tests/
```

