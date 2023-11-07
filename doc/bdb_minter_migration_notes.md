# Berkeley DB minter migration notes

## Pre-migration - Perform health checks
Perform health checks at least two weeks before the prodcution migration to give you some time to resolve technical issues.

### 1. Perform instance health check
- Perform a Disk Space check and make sure `/apps/ezid` has enough disk space for the migration
  - requires 8MB disk space to store a bakup of the minters in `.tar.gz` format
- Review EC2 metrics
- Review RDS metrics

### 2. Perform EZID health check
- Review EZID erros in log files (App, ELB, WAF)
  - anything blocks the minter migraiton?
- Verify EZID and background jobs are up and running
  
### 3. Perform minter health check

* 1.1 Run the `shoulder-check-minters` command to check the minters.
```
python manage.py shoulder-check-minters
```

```
python manage.py shoulder-check-minters | grep "OK: Preview of next ID" | wc -l
```

Review the output and fix issues if needed.
- If there are "Next identifier to be minted is already in the database (outdated minter)" errors
  - a. backup the minters directory
  - b. identifer the outdated minter 
  - c. run the `shoulder-mint` command to move the minter one count forward
  - d. re-run the `shoulder-check-minters` command and review the output
  - e. repeat step c-d until there are no more errors

Sample output:
```
ezidapp.management.commands.shoulder-check-minters INFO     shoulder-check-minters - Checking minter BerkeleyDB (BDB) databases...
ezidapp.management.commands.shoulder-check-minters INFO     shoulder-check-minters - ark:/10945/          Skipped: No minter registered
ezidapp.management.commands.shoulder-check-minters INFO     shoulder-check-minters - ark:/10945/t4        OK: Preview of next ID: ark:/10945/t4tc9x
ezidapp.management.commands.shoulder-check-minters INFO     shoulder-check-minters - ark:/12345/          OK: Preview of next ID: ark:/12345/gw86
ezidapp.management.commands.shoulder-check-minters INFO     shoulder-check-minters - ark:/12345/jj1       OK: Preview of next ID: ark:/12345/jj14w2j
...
ezidapp.management.commands.shoulder-check-minters ERROR    shoulder-check-minters - doi:10.48321/D1      Check failed: Next identifier to be minted is already in the database (outdated minter): Existing identifier: "doi:10.48321/D1X31R" "is in Store and is in Search" (active=yes, supershoulder=no, test=no)
...
ezidapp.management.commands.shoulder-check-minters INFO     shoulder-check-minters - --------------------------------------------------
ezidapp.management.commands.shoulder-check-minters INFO     shoulder-check-minters - Check completed
ezidapp.management.commands.shoulder-check-minters INFO     shoulder-check-minters - Total shoulders checked: 583
ezidapp.management.commands.shoulder-check-minters ERROR    shoulder-check-minters - Errors:
ezidapp.management.commands.shoulder-check-minters ERROR    shoulder-check-minters -    1 shoulders have error: Next identifier to be minted is already in the database (outdated minter) (active=yes, supershoulder=no, test=no)

```

* 1.2 Run the `diag-create-missing-minters-tmp-fix` command to create missing minters.

Note: 
- backup the minters directory
- use this temporary fix as the original command `diag-create-missing-minters.py` does not work as expected. The original command will be replaced with a newer version after the BDB to MySQL minter migration.

```
python manage.py diag-create-missing-minters-tmp-fix
```

* 1.3 Re-run the `shoulder-check-minters` command to check the minters
```
python manage.py shoulder-check-minters | grep "Skipped" | wc -l
```

## Communicate EZID service downtime to EZID users
Communicate EZID service downtime to internal and external users.

## Migration preparation steps
### 1. Verify EZID and background jobs are up and running

### 2. Bring up the EZID-Down server
Bring up the EZID-Down server to cutoff access to EZID and let user know about the system downtime.

TODO: Add link to downserver docs

### 3. Stop the EZID service and background jobs
CDL note:
* Disable Nagios alerts
* Deploy the current release tag with settings to disable the EZID service and background jobs
  * Make sure the EZID code base is deployed on the specified tag
  * Make sure the EZID service and background jobs are not started

- Note: Make sure service stays down. (TODO: confirm with Ashley that there are no puppet scripts that brings up the service).

Puppet configuration `uc3-ezid-ui-<dev|stg|prd>.yaml` options:
```
ensure_service: stopped
project_revision: <current_release_tag>
background_jobs_active: false
```
### 4. Backup the BDB minters folder
Back up the BDB minters folder and save an extra copy of the backup file on a different device.
```
tar cvfz minters.<dev/stg/prd>.<timestamp>.tar.gz minters

scp minters.<dev/stg/prd>.<timestamp>.tar.gz <target_source/target_dir>
```
### 5. Backup the EZID RDS database
Stop, backup, restart the EZID RDS database.

## Migration steps

### 1. Update/Deploy the new version of EZID code
CDL note:
* Deploy the new release tag with settings to disable the EZID service and background jobs
  * Make sure the EZID code base is deployed on the specified tag
  * Make sure the EZID service and background jobs are not started

Puppet configuration `uc3-ezid-ui-<dev|stg|prd>.yaml` options:
```
ensure_service: stopped
project_revision: <new_release_tag>
background_jobs_active: false
```

### 2. Create the minter table in the EZID database

#### 2.1 Make sure the required data model and migration files are in place
* data model: minter.py
* migration file: 0004_minter.py

#### 2.2 Modify the EZID settings
Modify the EZID settings in the file `settings/settings.py`:
* a. back up the current `settings.py` file 
* b. to use the dba account for data model migration
* c. to enable the `MINTERS_PATH` setting (remove the comment sign '#')

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': hostname,
        'NAME': 'ezid',
        'USER': 'eziddba_account',
        'PASSWORD': 'eziddba_password',

MINTERS_PATH = HOME_DIR / 'var' / 'minters'  # /apps/ezid/var/minters
```

#### 2.3 Run the "migrate" command to create the `minter` table
```
python manage.py migrate
```

#### 2.4 Verify the minter table in MySQL database
Verify that the `minter` table has been created in the `ezid` database with the desired table schema.
```
CREATE TABLE `ezidapp_minter` (
  `id` int NOT NULL AUTO_INCREMENT,
  `prefix` varchar(255) NOT NULL,
  `minterState` json NOT NULL,
  `createTime` int NOT NULL,
  `updateTime` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `prefix` (`prefix`),
  KEY `ezidapp_minter_createTime_dfbbf01f` (`createTime`),
  KEY `ezidapp_minter_updateTime_a91cebee` (`updateTime`)
)
```

### 3. Perform BDB minters data migration

Run the minter data migration script to convert the BDB minters to JSON objects and load them to the minter table in MySQL.

* Script: `migrate-minters-to-mysql.py`
* Folder: /ezidapp/management/commands

The script takes two optional arguments:
* --dry-run/-r: dry run without updating the minter table in the EZID database
* --output-file/-o: save BDB datasets in an output file in JSON format

#### 3.1 Dry run and output minters file for review
```
$ python manage.py migrate-minters-to-mysql --dry-run --output-file bdb_minters_<timestamp>.json
```
Review the output and address issues if needed.
```
ezidapp.management.commands.migrate-minters-to-mysql INFO     migrate-minters-to-mysql - Total number of shoulders: 566
ezidapp.management.commands.migrate-minters-to-mysql INFO     migrate-minters-to-mysql - Shoulders with unspecified minters: 36
ezidapp.management.commands.migrate-minters-to-mysql INFO     migrate-minters-to-mysql - Minters with BDB file: 430
ezidapp.management.commands.migrate-minters-to-mysql INFO     migrate-minters-to-mysql - Minters missing BDB file: 100
ezidapp.management.commands.migrate-minters-to-mysql INFO     migrate-minters-to-mysql - Minters with missing required keys: 0
ezidapp.management.commands.migrate-minters-to-mysql INFO     migrate-minters-to-mysql - Minter validation errors: 0
ezidapp.management.commands.migrate-minters-to-mysql INFO     migrate-minters-to-mysql - Dry run without updating MySQL: yes
ezidapp.management.commands.migrate-minters-to-mysql INFO     migrate-minters-to-mysql - JSON minters file: None
ezidapp.management.commands.migrate-minters-to-mysql INFO     migrate-minters-to-mysql - Completed successfully
```

#### 3.2 Perform BDB minters data migration
```
$ python manage.py migrate-minters-to-mysql
```

#### 3.3 Check data migration results
The `minter` table in the MySQL `ezid` database should have been populated with the BDB minter datasets.
* Check the total entries: should match BDB minters count
* Check the minter.state field for each entry: they should be in JSON format with minter required data fields
* Fix issues or move to the **Rollback Steps**
* TODO: link the rollback procedure here

#### 3.4 Disable the Berkeley Minter database 

* Rename the Berkeley minter folder
```
mv minters minters.bdb_sql_migration.<timestamp>
```

#### 3.5 Verify minter migration results
Run the `diag-minter` command to see if minters can produce identifiers and move to the next state

* Test on a specified minter
```
python manage.py diag-minter mint ark:/99999/fk4

python manage.py diag-minter mint ark:/99999/fk4 --count 3

python manage.py diag-minter mint ark:/99999/fk4 --count 2 --update

python manage.py diag-minter mint ark:/99999/fk4 --count 2
```

* Test on all minters:
```
python manage.py diag-minter forward 

python manage.py diag-minter forward --count 2

# perform on all minters if needed
python manage.py diag-minter forward --update  
```

#### Run EZID regression tests
* start the EZID service (only EZID but not background jobs) 
* run regression tests `python manage.py check-ezid --test-level 3`
* Review test results

## Rollback steps
Review minter migration results. Any unresolvable issues?
* Yes: stop here and proceed to rollback procedures
* No: proceed to the next step

## Re-start EZID and background jobs
1. Re-deploy the new release tag with the EZID and background jobs enabled
  * remove or comment out the `ensure_service: stopped` and `background_jobs_active: false` statements

```
#ensure_service: stopped
project_revision: <new_release_tag>
#background_jobs_active: false
```
2. Check the EZID settings.py file
  * The database configuration should be using the `ezid_readwrite` account and password now
  * The `MINTERS_PATH` entry should have been commented out
  * Delete the `settings.py` backup file

## Perform post-migration checks
1. Run the `verify_ezid_after_patching.py` script
2. Run the regression tests
   * On EZID-Dev and EZID-Stg run the full test set
     `python manage.py check-ezid --test-level 3`
   * On EZID-Prd run the small test set
     `python manage.py check-ezid --test-level 1`

## Shutdown the EZID-DOWN server
Shutdown the EZID-DWON server to redirect requests to the ezid service.

## Communicate completion of migration
Post completion message to the following Slack channels:
* EZID-dev
* uc3-maint
  
