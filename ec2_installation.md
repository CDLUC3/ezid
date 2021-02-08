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

Edit `~/.profile` to contain:
```shell script
export PATH="/apps/ezid/.pyenv/bin:${PATH}/bin:${PATH}"
export venv=ezid_2.7.17
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

```shell script
curl https://pyenv.run | bash
# logout and back in

export pyver=2.7.17
CONFIGURE_OPTS=--enable-shared pyenv install $pyver
pyenv virtualenv $pyver $venv
pyenv global $venv
```

```shell script
mkdir -p apps/init.d apps/ssl apps/sw
cd apps
git clone https://github.com/CDLUC3/ezid-config.git apache
mkdir -p apache/WARTS apache/ezid
cd apache
git clone https://github.com/CDLUC3/ezid-shoulders.git
cd ezid
mkdir -p ezid_dev_2.7.17
cd ezid_dev_2.7.17
mkdir -p db download/public logs 
git clone https://github.com/CDLUC3/ezid.git
git clone https://github.com/CDLUC3/ezid-info-pages.git ezid/templates/info
cd ezid
git pull
git checkout initial-setup
git fetch --all
cd templates/info/
git fetch --all
git checkout initial-setup
cd ../..
mv master_shoulders.txt ~/apps/apache/ezid-shoulders/
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
 The failure is because of a namespace collision between the root folder "ezid" and the "ezid.py" file under code
 . Remove `/ezid/__init__.py` to resolve.
 
Now seeing a failure:
```shell script
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
  File "/apps/ezid/apps/apache/ezid/ezid_dev_2.7.17/ezid/code/startup.py", line 94, in ready
    ui_common.loadConfig()
  File "/apps/ezid/apps/apache/ezid/ezid_dev_2.7.17/ezid/code/ui_common.py", line 44, in loadConfig
    p = ezidapp.models.shoulder.getArkTestShoulder()
  File "/apps/ezid/apps/apache/ezid/ezid_dev_2.7.17/ezid/ezidapp/models/shoulder.py", line 319, in wrapped
    return f(*args, **kwargs)
  File "/apps/ezid/apps/apache/ezid/ezid_dev_2.7.17/ezid/ezidapp/models/shoulder.py", line 347, in getArkTestShoulder
    return _shoulders[_arkTestPrefix]
KeyError: 'ark:/99999/fk4'
```  

Apparently because the test should global variable is not being populated. This is because the `master_sholuders.txt
` file can not be found. Check the path to the file for the running configuration under `[shoulders]` in `ezid.conf` .
