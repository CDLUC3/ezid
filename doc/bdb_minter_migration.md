# Berkeley DB minter migraiton notes

0. Preparation steps

a. Stop the EZID and background services
b. Backup the BDB minter folder (optional)

1. Create the minter table in the EZID database

Required files:
* data model: minter.py
* migration file: 0004_minter.py

Run the "migrate" command to create the `minter` table:

python manage.py migrate

2. Perform data migraiton

Run the data migration script to convert the BDB minters to JSON objects and load them to the minter table in MySQL.

Script: `migrate-minters-to-mysql.py`
Folder: /ezidapp/management/commands

The script takes two optional arguments:
* --dry-run/-r: dry run without updating the minter table in the EZID database
* --output-file/-o: save BDB datasets in an output file in JSON format

Sample command

```
$ python manage.py migrate-minters-to-mysql.py
```

3. Disable the Berkeley minter database 

a. Rename the Berkeley minter folder
b. Modify the settings.py file to remove Berkeley minter related entries


 
 
