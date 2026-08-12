# Test EZID

To perform EZID Unit test, you need to:
* prepare Python environment
* setup the `DJANGO_SETTINGS_MODULE` environment variable
* create test database
* run `pytest` to perform the tests

Refer [Unit & CI tests](https://github.com/CDLUC3/ezid-docs-internal/blob/main/docs/unit_integration_tests.md) for detailed instructions on how to run EZID unit tests.

## Prepare Python environment
Run `pip install .` to source file `pyproject.toml` and install all dependencies listed there.

Run `pip install -r requirements-dev.txt` to install required packages for testing.

## Setup the `DJANGO_SETTINGS_MODULE` environment variable

There are a few ways to setup the `DJANGO_SETTINGS_MODULE` variable:

a. Use the `export` command. This tells Django to find configurations from file “ezid/settings/tests.py”.
```
$ export DJANGO_SETTINGS_MODULE=settings.tests
```

b. Use the command line option `--ds=SETTINGS`:
```
$ pytest  --ds=settings.tests
```

## Setup test database

A script `prepare_test_db.sh` was created to automate the test database setup process. The script is in the home directory of the ezid project. The script does not require any parameters. Provide the root user password for your local mysql database when prompted.

```
./prepare_test_db.sh
Enter password:
``` 

## Run Pytest
Test scripts and data files are organized in the `ezid/tests` directory. Test scripts are named in the `test_scriptname.py` format.

To run all tests using the test settings:
```
pytest --ds=settings.tests tests/
```
To run a specific test script:
```
pytest --ds=settings.tests tests/test_api.py
```

