#Sourced by etc/init.d/httpd for WSGI config
#Source me for local server running
export PATH="/apps/ezid/.pyenv/bin:${PATH}"
export venv=ezid
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
# uc3-ezidx2-dev.cdlib.org
export HOSTNAME=$(hostname -f)
export DJANGO_SETTINGS_MODULE=settings.remotedev
EZID_DEV="/apps/ezid/ezid"
export PYTHONPATH="${EZID_DEV}:${EZID_DEV}/impl:$PYTHONPATH"
