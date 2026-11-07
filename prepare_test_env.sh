# This environment variable is used to be sure the correct database (the test one) is used inside this script.
# This will not interfere with external settings for it because it is not exported from this script.
DJANGO_SETTINGS_MODULE=settings.tests

# Keep the informational pages checkout available for local/test runs.
INFO_PAGES_DIR="templates/info"
INFO_PAGES_REPO="https://github.com/CDLUC3/ezid-info-pages.git"
echo "Updating informational pages checkout: $INFO_PAGES_DIR..."

if [ -d "$INFO_PAGES_DIR/.git" ]; then
  git -C "$INFO_PAGES_DIR" fetch || exit 1
else
  rm -rf "$INFO_PAGES_DIR"
  mkdir -p "$INFO_PAGES_DIR"
  git clone "$INFO_PAGES_REPO" "$INFO_PAGES_DIR" || exit 1
fi

git -C "$INFO_PAGES_DIR" pull --ff-only || exit 1

echo "Creating test database..."
mysql -h127.0.0.1 -uroot -p << EOF
  drop database if exists ezid_test_db;
  create database ezid_test_db;
  use ezid_test_db;
  drop user if exists 'ezid_test_user'@'%';
  create user 'ezid_test_user'@'%' identified by 'ezid_test_pw';
  grant all privileges on ezid_test_db.* to 'ezid_test_user'@'%';
EOF

echo "Running database migrations..."
python ./manage.py migrate

echo "Collecting static files..."
python ./manage.py collectstatic --no-input

echo "Loading test data..."
python ./manage.py loaddata db
