# Berkeley DB minter migraiton notes

## Preparation steps

### 1. Check the minters

Run the shoulder-check-minters command to check the minters.
```
python manage.py shoulder-check-minters
```
Review the output and fix issues if needed.


### 2. Stop the EZID and background services

### 3. Backup the BDB minters folder

### 4. Backup the EZID RDS database

### 5. Update/Deploy EZID code

* Make sure the puppet deploy script does not start EZID and background jobs after code deployment
* Make sure EZID is on the preferred tag/branch

## Create the minter table in the EZID database

### 1. Modify the EZID settings to use the eziddba account for data model migration
### 2. Make sure the required data model and mingration files are in place
* data model: minter.py
* migration file: 0004_minter.py

### 3. Run the "migrate" migrate command to create the `minter` table:
```
python manage.py migrate
```

## Perform minter data migraiton

Run the minter data migration script to convert the BDB minters to JSON objects and load them to the minter table in MySQL.

Script: `migrate-minters-to-mysql.py`
Folder: /ezidapp/management/commands

The script takes two optional arguments:
* --dry-run/-r: dry run without updating the minter table in the EZID database
* --output-file/-o: save BDB datasets in an output file in JSON format

Sample command

```
$ python manage.py migrate-minters-to-mysql.py
```

## Disable the Berkeley minter database 

* Rename the Berkeley minter folder
* Modify the settings.py file to remove Berkeley minter related entries

## Perform post-migration steps
Perform post-migraiton steps:
* Review minter data migration results
* Modify the EZID settings to use the ezidrw account
* Restart EZID and back ground jobs
 
 
