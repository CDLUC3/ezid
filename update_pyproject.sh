#
# Script: update_pyproject.sh
# Update pyproject.toml pacakges to the latest version with command poetry add ${package}@latest. 
# This has the added benefit of updating poetry.lock as well. 
# Run `poetry update` afterwards to update package dependencies that were missed from the above `poetry add` command.

# for now we omit `django-matomo-api-tracking` because of how it is sourced.
# Do not update Python or Django in this script.
# Manually run the `poetry add {package}@version` command to update Python and Django to a desired version.
DEPS="
aiomysql
mysqlclient
boto3
mysql
myloginpath
jinja2
pygments
fasteners
feedparser
filelock
freezegun
hjson
lxml
python-dateutil
requests
toml
simplegist
xmltodict
pymysql
configparser
ecs-logging
celery
sqlalchemy
"
for package in $DEPS; do
  poetry add ${package}@latest
done

# update package dependencies
poetry update
