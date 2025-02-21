Python Dependency Management for EZID
=====================================

Thu May 30 05:18:33 PM PDT 2024

Our previous installation method using `setup.py install` is no longer
supported for deployments on python `>3.11.x`.  We now use `pip install` to
deploy EZID and [poetry](https://python-poetry.org/docs/) for python package
dependency resolution.  Both tools rely on file `pyproject.toml` for dependency
management.

At this point in time we do not use `poetry install` to deploy EZID, because
this forces us to run the application and all django management commands within
a poetry generated virtual environment (e.g. `poetry run command`). The
trade-off is we do not take advantage of poetry's excellent dependency version
locking mechanism.


The `pyproject.toml` file
-------------------------

The
[`pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#writing-pyproject-toml)
configuration file is used by a veriety of python packaging and installation
tools.  Here is a quick tour of the our EZID `pyproject.toml`:

We declare Poetry as our build tool
```
[build-system]
requires = ["poetry-core>=1.0.0,<2.0.0"]
build-backend = "poetry.core.masonry.api"
```

We use Poetry only for dependency management but not for packaging:
```
[tool.poetry]
# use Poetry only for dependency management but not for packaging
package-mode = false
```

We enumerate python dependencies along with minumum semantic version:
```
[tool.poetry.dependencies]
python = "^3.11"
django = "^4.2.11"
aiomysql = "^0.2.0"
mysqlclient = "^2.2.4"
boto3 = "^1.34.116"
[cut]
```

We enumerate development tools in a `dev` group section:
```
[tool.poetry.group.dev.dependencies]
pytest-django = "^4.8.0"
pytest-mock = "^3.14.0"
```



Installing EZID
---------------

The target host must support python 3.11 or higher.  This can be a python virtual environment.
After install we can use `poetry check` to validate the installed dependencies against the
`poetry.lock` file.  See [Installing Poetry](#installing-poetry) below.

1. Clone the project repostory
   ```
   agould@uc3-opspuppet-dev01:~/projects> git clone git@github.com:CDLUC3/ezid.git
   Cloning into 'ezid'...
   Receiving objects: 100% (32942/32942), 73.36 MiB | 16.44 MiB/s, done.
   Resolving deltas: 100% (21345/21345), done.
   Updating files: 100% (986/986), done.
   ```

1. Activate your virtual environment if using such (example uses [pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#automatic-installer))
   ```
   agould@uc3-opspuppet-dev01:~/projects> pyenv global
   3.11.9
   agould@uc3-opspuppet-dev01:~/projects> pyenv virtualenv ezid-3.11.9
   agould@uc3-opspuppet-dev01:~/projects> pyenv global ezid-3.11.9
   (ezid-3.11.9) agould@uc3-opspuppet-dev01:~/projects> 
   ```

1. Change directory into the root of the working tree of the cloned project repository
   ```
   (ezid-3.11.9) agould@uc3-opspuppet-dev01:~/projects> cd ezid
   (ezid-3.11.9) agould@uc3-opspuppet-dev01:~/projects/ezid> ls -l pyproject.toml 
   -rw-r--r--. 1 agould users 2726 May 31 13:26 pyproject.toml
   ```

1. Run `pip install .` This tells `pip` to source file `pyproject.toml` and
   install all dependencies listed in table `[tool.poetry.dependencies]`
   ```
   (ezid-3.11.9) agould@uc3-opspuppet-dev01:~/projects/ezid> pip install .
   Processing /home/agould/projects/ezid
     Installing build dependencies ... done
     Getting requirements to build wheel ... done
     Preparing metadata (pyproject.toml) ... done
   [cut]
   Successfully installed MarkupSafe-2.1.5 aiomysql-0.2.0 amqp-5.2.0 asgiref-3.8.1 beautifulsoup4-4.12.3 billiard-4.2.0 boto3-1.34.117 botocore-1.34.117 ...
   ```

1. Validate installed packages against `poetry.lock` file
   ```
   (ezid-3.11.9) agould@uc3-opspuppet-dev01:~/projects/ezid> poetry check --lock
   All set!
   ```


Keeping dependencies up-to-date with Poetry
-------------------------------------------

Occassionally we must ensure the minimum semantic versions of python
dependencies are current.  We use a combination of
[Poetry commands](https://python-poetry.org/docs/cli/) to currate the `pyproject.toml` file.


#### Installing Poetry

We recommend to install Poetry globally on your development host, so it may be
used for a veriety of projects regardless of virtual environment.  Do this with
[`pipx`](https://python.land/virtual-environments/pipx):
```
agould@uc3-opspuppet-dev01:~> pipx install poetry
agould@uc3-opspuppet-dev01:~> which poetry
~/.local/bin/poetry
```


The `poetry update` command retrieves latest versions of dependencies listed in
`pyproject.toml` and updates the `poetry.lock` file.  However, it does not
automatically update minimum semantic versions in `pyproject.toml`.  To keep
`pyproject.toml` truly up-to-date, do the following:

1. Update `pyproject.toml` with command `poetry add ${package}@latest`.  This has
   the added benefit of updating `poetry.lock` as well.

   Make a list of all dependency package names and run this command in a for loop:

   ```
   # for now we omit `django-matomo-api-tracking` because of how it is sourced.
   DEPS="
   django
   aiomysql
   mysqlclient
   boto3
   mysql
   myloginpath
   jinja2
   pygments
   fasteners
   feedparser
   filelock
   freezegun
   hjson
   lxml
   python-dateutil
   requests
   toml
   simplegist
   xmltodict
   pymysql
   configparser
   ecs-logging
   celery
   sqlalchemy
   "
   for package in $DEPS; do
     poetry add ${package}@latest
   done
   ```
   Note:
   * A script `update_pyproject.sh` was created to automate the above process.
   * The `django` entry is excluded from the list. Run `poetry add django@version` command to manually upgrade Django to a desired version.
   * The `update_pyproject.sh` script includes a final step `poetry update` which is used to update package dependencies in `poetry.lock`.

1. Review changes with `git diff pyproject.toml`.  Make alterations as needed:
   ```
   (ezid-3.11.9) agould@uc3-opspuppet-dev01:~/projects/ezid> git diff pyproject.toml
   diff --git a/pyproject.toml b/pyproject.toml
   index 83bff875..fafbf330 100644
   --- a/pyproject.toml
   +++ b/pyproject.toml
   @@ -42,7 +42,7 @@ python = "^3.11"
    django = "^4.2.11"
    aiomysql = "^0.2.0"
    mysqlclient = "^2.2.4"
   -boto3 = "^1.34.107"
   +boto3 = "^1.34.117"
    mysql = "^0.0.3"
    myloginpath = "^0.0.4"
    jinja2 = "^3.1.4"
   @@ -54,16 +54,16 @@ freezegun = "^1.5.1"
    hjson = "^3.1.0"
    lxml = "^5.2.2"
    python-dateutil = "^2.9.0.post0"
   -requests = "^2.31.0"
   +requests = "^2.32.3"
    toml = "^0.10.2"
    simplegist = "^1.0.1"
    xmltodict = "^0.13.0"
   -pymysql = "^1.1.0"
   +pymysql = "^1.1.1"
    configparser = "^7.0.0"
    ecs-logging = "^2.1.0"
    celery = "^5.4.0"
    sqlalchemy = "^2.0.30"
   ``` 
Note:
* Run the `poetry update` command if you modified the `pyproject.toml` file manually.
  
3. Review changes with `git diff poetry.lock`
   
4. Commit your updates and cut a new release candidate tag.  Open a pull request so 
   proper integration testing can be scheduled.

   In most cases you will see changes in the `pyproject.toml` and `poetry.lock` files.


