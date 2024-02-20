# This environment variable is used to be sure the correct database (the test one) is used inside this script.
# This will not interfere with external settings for it because it is not exported from this script.
DJANGO_SETTINGS_MODULE=settings.tests

mysql -h127.0.0.1 -uroot -p << EOF
  drop database if exists ezid_test_db;
  create database ezid_test_db;
  use ezid_test_db;
  drop user if exists 'ezid_test_user'@'%';
  create user 'ezid_test_user'@'%' identified by 'ezid_test_pw';
  grant all privileges on ezid_test_db.* to 'ezid_test_user'@'%';
EOF


python ./manage.py migrate

python ./manage.py loaddata db
