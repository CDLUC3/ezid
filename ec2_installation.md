Installing EZID on EC2

Find libs etc, e.g. `yum list | grep ssl-devel`

```shell script
sudo yum install build-essential llvm make bash curl wget git xz-utils
sudo yum install sqlite-devel.x86_64
sudo yum install readline-devel.x86_64
sudo yum install openssl-devel.x86_64
sudo yum install bzip2-devel.x86_64
sudo yum install lzma-devel
sudo yum install xz-lzma-compat.x86_64
```

Open terminal as ezid user.

```shell script
$cat .profile

export PATH="/apps/ezid/.pyenv/bin:$PATH"
export venv=ezid_2.7.17
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

```shell script
curl https://pyenv.run | bash
# logout and back in

export pyver=2.7.17
pyenv install $pyver
pyenv virtualenv $pyver $venv
pyenv global $venv
```

```shell script
git clone https://github.com/CDLUC3/ezid.git
git clone https://github.com/CDLUC3/ezid-info-pages.git ezid/templates/info
cd ezid
git pull
git checkout initial-setup
git fetch --all
cd templates/info/
git fetch --all
git checkout initial-setup
```

```shell script
pip install -r requirements.txt
./dev_prep_env.sh
ls -la
curl "https://raw.githubusercontent.com/CDLUC3/ezid-shoulders/master/master_shoulders.txt" > master_shoulders.txt
django-admin migrate
django-admin migrate --database=search
django-admin loaddata store-init.json
django-admin loaddata --database=search search-init.json
django-admin loaddata store-init.json
```

The last step fails:
```shell script
(ezid_2.7.17) -bash-4.2$ django-admin loaddata --database=search search-init.json
Traceback (most recent call last):
  File "/apps/ezid/.pyenv/versions/ezid_2.7.17/bin/django-admin", line 8, in <module>
    sys.exit(execute_from_command_line())
  File "/apps/ezid/.pyenv/versions/2.7.17/envs/ezid_2.7.17/lib/python2.7/site-packages/django/core/management/__init__.py", line 364, in execute_from_command_line
    utility.execute()
  File "/apps/ezid/.pyenv/versions/2.7.17/envs/ezid_2.7.17/lib/python2.7/site-packages/django/core/management/__init__.py", line 338, in execute
    django.setup()
  File "/apps/ezid/.pyenv/versions/2.7.17/envs/ezid_2.7.17/lib/python2.7/site-packages/django/__init__.py", line 27, in setup
    apps.populate(settings.INSTALLED_APPS)
  File "/apps/ezid/.pyenv/versions/2.7.17/envs/ezid_2.7.17/lib/python2.7/site-packages/django/apps/registry.py", line 116, in populate
    app_config.ready()
  File "/apps/ezid/ezid/code/startup.py", line 50, in ready
    ezid.loadConfig()
AttributeError: 'module' object has no attribute 'loadConfig'
```
