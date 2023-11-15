# Berkeley DB minter migration notes

## Pre-migration health checks
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

3.1 Run the `shoulder-check-minters` command to check the minters.
```
python manage.py shoulder-check-minters

python manage.py shoulder-check-minters | grep "OK: Preview of next ID" | wc -l

python manage.py shoulder-check-minters | grep "Skipped" | wc -l
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

3.2 Run the `diag-create-missing-minters-tmp-fix` command to create missing minters.

Note: 
- backup the minters directory
- use this temporary fix as the original command `diag-create-missing-minters.py` does not work as expected. The original command will be replaced with a newer version after the BDB to MySQL minter migration.

```
python manage.py diag-create-missing-minters-tmp-fix
```

3.3 Re-run the `shoulder-check-minters` command to check the minters
```
python manage.py shoulder-check-minters
```

## Prepare for software release
1. Create release tags for the deployment
- pre-release tag: created on a commit with the latest code
- release tag: created on a newer commit after the pre-release tag (make minor changes to a documentation or comments if there is no code change)

2. Create release note

## Communicate EZID service downtime to EZID users
Communicate EZID service downtime to internal and external users.

## Migration preparation steps

### 1. Disable Nagios alerts

### 2. Stop the EZID service and background jobs
 
```
sudo cdlsysctl stop ezid

sudo cdlsysctl stop ezid-proc-*
```
### 3. Bring up the EZID-is-down server
Bring up the EZID-is-down server to cutoff access to EZID and let user know about the system downtime.
```
screen ~/ezid/tools/downserver.py $(hostname) 18880 3600
```
Reference: [How to bring up the EZID-is-down server](https://github.com/CDLUC3/ezid-docs-internal/blob/main/docs/ezid_is_down_server.md)

### 4. Backup the BDB minters folder
Back up the BDB minters folder and save an extra copy of the backup file on a different device.
```
tar cvfz minters.<dev/stg/prd>.<timestamp>.tar.gz minters

scp minters.<dev/stg/prd>.<timestamp>.tar.gz <target_source/target_dir>
```
### 5. Backup the EZID RDS database
Take a snapshot of the EZID RDS database.

## Migration steps

### 1. Deploy the new version of EZID code
CDL note:
* Deploy the pre-release tag with settings to disable the EZID service and background jobs
  * Make sure the EZID code base is deployed on the specified tag
  * Make sure the EZID service and background jobs are not started

Puppet configuration `uc3-ezid-ui-<dev|stg|prd>.yaml` options:
```
ensure_service: stopped
project_revision: <pre_release_tag>
background_jobs_active: false
```
Puppet deployment command:
```
uc3_pupapply.sh # preview mode
uc3_pupapply.sh --exec 
```
### 2. Create the minter table in the EZID database

#### 2.1 Make sure the required data model and migration files are in place
* data model: minter.py
* 4 migration files:
  * 0001_initial.py
  * 0002_auto_20221026_1139.py
  * 0003_auto_20230809_1154.py
  * 0004_minter.py
**Note**: make sure these are the only migration files in the `ezid/ezidapp/migrations` folder. Delete other `.py` files if there are any in the migrations folder. 

#### 2.2 Modify the EZID settings
Modify the EZID settings in the file `settings/settings.py`:
* a. back up the current `settings.py` file 
* b. use the dba account for data model migration

```
cp settings.py settings.py.bk

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': hostname,
        'NAME': 'ezid',
        'USER': 'eziddba_account',
        'PASSWORD': 'eziddba_password',
```

#### 2.3 Run the "migrate" command to create the `minter` table
In the ezid project folder run the `migrate` command:
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
ezidapp.management.commands.migrate-minters-to-mysql INFO     migrate-minters-to-mysql - JSON minters file: bdb_minters_<timestamp>.json
ezidapp.management.commands.migrate-minters-to-mysql INFO     migrate-minters-to-mysql - Completed successfully
```

#### 3.2 Perform BDB minters data migration
Run the `migrate-minters-to-mysql` command without the `--dry-run` option. Save the BDB datasets in a JSON file if needed. 
```
$ python manage.py migrate-minters-to-mysql --output-file bdb_minters_<timestamp>.json
```

#### 3.3 Check data migration results
The `minter` table in the MySQL `ezid` database should have been populated with the BDB minter datasets.
* Check the total entries: should match BDB minters count
* Check the minter.state field for each entry: they should be in JSON format with minter required data fields, such as:
  * mask
  * oatop
  * total
  * original_template
  * c0/top
  * c0/value
* If there are issues:
  * Fix issues and proceed to the next step, or
  * move to the **Rollback Steps**
* TODO: link the rollback procedure here

#### 3.4 Disable the Berkeley Minter database 

* Rename the Berkeley minter folder
```
mv minters minters.bdb_sql_migration.<timestamp>
```

#### 3.5 Verify minter migration results
Run the `diag-minter` command to see if minters can produce identifiers and move to the next state

* Test on a specified minter `ark:/99999/fk4` - test on Dev, Stg and Prd:
```
python manage.py diag-minter mint ark:/99999/fk4

python manage.py diag-minter mint ark:/99999/fk4 --count 3

python manage.py diag-minter mint ark:/99999/fk4 --count 2 --update

python manage.py diag-minter mint ark:/99999/fk4 --count 2
```

* Test on all minters - **Do Not Test on PRD**; Only test on Dev and Stg:
```
python manage.py diag-minter forward 

python manage.py diag-minter forward --count 2

# perform on all minters if needed
#python manage.py diag-minter forward --update  
```

#### Run EZID regression tests
**Do Not Test on PRD;** Only test on Dev and Stg:
* start the EZID service (only EZID but not background jobs) 
* run the regression tests and review test results
```
sudo cdlsysctl start ezid

python manage.py check-ezid --test-level 3
```

## Rollback steps
Review minter migration results. Are there any unresolvable issues?
* Yes: stop here and proceed to rollback procedures
* No: proceed to the next step

## Shutdown the EZID-is-down server
Shutdown the "EZID-is-down" server:
*  Resume the screen session
*  Type [Ctrl-c] to teminate the session

## Re-start EZID and background jobs
1. Re-deploy EZID using the new release tag with the EZID and background jobs enabled
  * update the `ensure_service` entry to `running`
  * comment out or remove the `background_jobs_active: false` statement
  * run `uc3_pupapply.sh` command to deploy the new release

Puppet configuration `uc3-ezid-ui-<dev|stg|prd>.yaml` options:
```
ensure_service: 'running'
project_revision: <new_release_tag>
#background_jobs_active: false
```
Puppet deployment command:
```
uc3_pupapply.sh # preview mode
uc3_pupapply.sh --exec 
```

2. Check the EZID settings.py file
  * The database configuration should be using the `ezid_readwrite` account and password now
  * The `MINTERS_PATH` entry should have been commented out ore removed

3. Delete the backup setting file `settings.py.bk`

## Perform post-migration checks
Run the `verify_ezid_after_patching.py` script to verify services:
```
cd ~/ezid-ops-scripts/scripts

verify_ezid_after_patching.py -e <dev|stg|prd> -u apitest -p apitest
```

## Communicate completion of migration
Post completion message to the following Slack channels:
* EZID-dev
* uc3-maint
  
