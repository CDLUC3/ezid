#
# Script: update_pyproject.sh
# Update pyproject.toml pacakges to the latest version with command poetry add ${package}@latest. 
# This has the added benefit of updating poetry.lock as well. 

# for now we omit `django-matomo-api-tracking` because of how it is sourced.
# Do not update Python and Django
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
pytest-django
pytest-mock
"
for package in $DEPS; do
  poetry add ${package}@latest
done