# run shoulder-check-minters command to check minters before running deployment
python manager.py shoulder-check-minters

# fix minter issues if needed

#
## update/deploy EZID code
# set DB user to eziddba

echo "shutdown EZID servies"
sudo cdlsysctl stop ezid
sudo cdlsysctl stop ezid-proc-*

echo "backup minter files"
timestamp=`date '+%Y%m%d%H%M%S'`
minters_bk="minters.${timestamp}"

cp -r ~/var/minters ~/var/${minters_bk}

echo "backed up minter files to ${minters_bk}"

echo "Generate a data migration files"
python manage.py makemigrations

echo "Apply the migration file to the database"
python manage.py migrate

echo "run minter data migration script"
python manage.py migrate-minters-to-mysql

echo "rename var/minters to disable BDB minter" 
mv ~/var/minters ~/var/minters.sql_migration

echo "renamed to ~/var/minters.sql_migration"

echo "restart EZID services"
sudo cdlsysctl start ezid

