echo "Start minter migration steps ..."
echo "1. Check minters"

read -p "Have you run the shoulder-check-minters command to check the minters? [yes/no]: " yn
if [[ "$yn" == "yes" ]]; then
  read -p "Do you wish to continue to next step? [yes/no]: " next_step
  if [[ "$next_step" != "yes" ]]; then
    echo "Minter migration aborted."
    exit
  fi
elif [[ "$yn" == "no" ]]; then
  cat <<EOF
Please finish checking minters before proceeding to the next step:
  a. Run the shoulder-check-minters:
     python manage.py shoulder-check-minters"
  b. Review the output
  c. Fix issues if needed
  d. Rerun this minter migration script
EOF
  exit
else
  echo "Please answer yes or no."
  exit
fi

echo "2. Shutdown EZID servies"
sudo cdlsysctl stop ezid
sudo cdlsysctl stop ezid-proc-*

echo "3. Update/Deploy EZID code"
read -p "Is EZID on the right tag/branch? [yes/no]: " yn
if [[ "$yn" != "yes" ]]; then
  echo "Please update/deploy EZID code to the preferred tag/branch."
  echo "On EZID  Stg/Prd  server, run the Puppet apply script to deploy EZID code:"
  echo "uc3_pupapply.sh --exec --no-services"
  exit
fi

echo "4. Modify EZID settings to use the eziddba account for data model migration."
read -p "Is EZID on the right tag/branch? [yes/no]: " yn
if [[ "$yn" != "yes" ]]; then
  echo "Please update the database user to eziddba in the settings.py file."
  exit
fi

echo "5. Backup minter files"
timestamp=`date '+%Y%m%d%H%M%S'`
minters_bk="minters.${timestamp}"

cp -r ~/var/minters ~/var/${minters_bk}

echo "Minter files are backed up to: ${minters_bk}"

echo "6. Apply EZID migration files to the database"
python manage.py migrate

echo "7. Run the minter data migration script"
python manage.py migrate-minters-to-mysql

echo "8. Rename var/minters to disable BDB version minters" 
mv ~/var/minters ~/var/minters.sql_migration

echo "BDB minters has been renamed to ~/var/minters.sql_migration"

echo "Perform post-migration steps:"
echo "9. Review minter data migration results"
echo "10. Modify EZID settings to use the ezidrw account"
echo "11. Restart EZID services"



