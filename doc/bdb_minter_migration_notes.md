# Berkeley DB minter migraiton notes

## Preparation steps

### 1. Perform minter health check

1.1 Run the `shoulder-check-minters` command to check the minters.
```
python manage.py shoulder-check-minters
```
Review the output and fix issues if needed.

1.2 Run the `diag-create-missing-minters.py` command to create missing minters.
```
python manage.py diag-create-missing-minters.py
```

### 2. Stop the EZID service and background jobs
CDL note:
* Disable Nagios alerts
* Deploy current release tag with the "disable the EZID service and background jobs option"
  * Make sure EZID is deployed on the specified tag
  * Make sure EZID and background jobs are not started
```
ensure_service: stopped
project_revision: <current_release_tag>
background_jobs_active: false
```
### 3. Backup the BDB minters folder
```
tar -cvfz minters.<dev/stg/prd>.<timestamp>.tar.gz minters
```
### 4. Backup the EZID RDS database

## Migration steps

### 1. Update/Deploy new version of EZID code
CDL note:
* Deploy the new release tag with settings to disable the EZID service and background jobs
  * Make sure EZID is deployed on the specified tag
  * Make sure EZID and background jobs are not started

Puppet setting options:
```
ensure_service: stopped
project_revision: <new_release_tag>
background_jobs_active: false
```

### 2. Create the minter table in the EZID database

#### 2.1 Make sure the required data model and migration files are in place
* data model: minter.py
* migration file: 0004_minter.py

#### 2.2 Modify the EZID settings `settings/settings.py` to use the `eziddba` account for data model migration
  
```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': hostname,
        'NAME': 'ezid',
        'USER': 'eziddba',
        'PASSWORD': 'eziddba_password',
```

#### 2.3 Run the "migrate" migrate command to create the `minter` table
```
python manage.py migrate
```

#### 2.4 Verify the minter table in MySQL database
Verify that the `minter` table has been created in the `ezid` database with the desired table schema.

### 3. Perform BDB minters data migration

Run the minter data migration script to convert the BDB minters to JSON objects and load them to the minter table in MySQL.

* Script: `migrate-minters-to-mysql.py`
* Folder: /ezidapp/management/commands

The script takes two optional arguments:
* --dry-run/-r: dry run without updating the minter table in the EZID database
* --output-file/-o: save BDB datasets in an output file in JSON format

#### 3.1 Dry run and output minters file for review
```
$ python manage.py migrate-minters-to-mysql.py --dry-run --output-file bdb_minters_<timestamp>.json
```

#### 3.2 Perform BDB minters data migration
```
$ python manage.py migrate-minters-to-mysql.py --dry-run --output-file bdb_minters_<timestamp>.json
```

#### 3.4 Check data migration results
The `minter` table in the MySQL `ezid` database should have been populated with BDB minter datasets.
* check the total entries: should match BDB minters count
* the minter.state field for each entry should be in JSON format with minter required data fields

#### 3.5 Disable the Berkeley minter database 

* Rename the Berkeley minter folder
```
mv minters minters.bdb_sql_migration.<timestamp>
```

#### 3.6 Verify minter
run the `shoulder-mint` command to verify minter works as expected.

## Re-start EZID and background jobs
Steps:
* Review minter data migration results
* Any need to rollback migration work?
  * Yes: perform rollback steps
  * No: proceed to next step
* Modify the EZID settings to use the ezidrw account
* Re-deploy the new release tag with the EZID and background jobs enabled
  * remove or comment out the `ensure_service: stopped` and `background_jobs_active: false` statements

```
#ensure_service: stopped
project_revision: <new_release_tag>
#background_jobs_active: false
```
## Perform post-migration steps
* Modify the settings.py file to remove Berkeley minter related entries in a future release
 
 
