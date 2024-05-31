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


Installing EZID
---------------

To install EZID clone the project repostory and run `pip install .` in the root
of the working tree.  `pip` sources file `pyproject.toml` and installs all
dependencies listed in table `[tool.poetry.dependencies]` according to semantic
version ranges defined therein.

```
[tool.poetry.dependencies]
python = "^3.11"
django = "^4.2.11"
aiomysql = "^0.2.0"
mysqlclient = "^2.2.4"
boto3 = "^1.34.116"
[cut]
```


