# Startup failure under python3

App startup is failing in management.py with no database because it expects a database to exist, even though it can't exist before being created by the management command.

Disabling `ezidapp` in INSTALLED_APPS lets management run.

## How to run EZID on python 3 from a bare checkout

```
git clone https://github.com/CDLUC3/ezid.git
git checkout -track origin/ezid-py3-startup
```

From the ezid folder:

```
git clone https://github.com/CDLUC3/ezid-info-pages.git templates/info
mkdir -p db
mkdir -p ../download/public
wget https://raw.githubusercontent.com/CDLUC3/ezid/master/master_shoulders.txt
```

Get a copy of minters from somewhere, like `ezid-dev`, place them under `../var/minters`.

```
export DJANGO_SETTINGS_MODULE=settings.test_sqlite_settings
./manage.py migrate
./manage.py loaddata store-init.json
./manage.py shoulder-merge-master --debug
./manage.py runserver
```
