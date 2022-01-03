# Starting EZID from scratch

1. Checkout
2. Create virtual environment
3. Activate virtual environment 
4. Install dependencies 
5. Create database
   ``` 
   create database ezid00;
   grant all privileges on ezid00.* to 'eziddba'@'localhost';
   ```
6. Make work folders:
   ```
   mkdir -p ../var/minters ../logs ../download/public 
   ```
7. Edit configuration
8. Create migrations: `./manage.py makemigrations`
9. Apply migrations: `./manage.py migrate`
10. Update admin account `./manage.py diag-update-admin`
11. Add at least one Datacenter:
    ```
    insert into ezidapp_datacenter (symbol, name) values ('CDL.CDL', 'California Digital Library');`
    ```
12. Create user shoulder, used as the shoulder for identifiers of groups etc
    ```
    ./manage.py shoulder-create-ark ark:/99166/p9 CDL
    ```
13. Create administrative shoulders
    ```
    # Test ARK
    ./manage.py shoulder-create-ark ark:/99999/fk4 CDL
    # Test Datacite DOI
    ./manage.py shoulder-create-doi --datacite  CDL.CDL 'doi:10.5072/FK2' EZID
    # Crossref DOI
    ./manage.py shoulder-create-doi --crossref  doi:10.15697/ ezidtestgroup
    ```
