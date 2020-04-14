# Set up env vars for EZID app. Must be sourced.

unset PYTHONPATH
unset DJANGO_SETTINGS_MODULE

PYTHONPATH="$(realpath .):$(realpath code)${PYTHONPATH:+:${PYTHONPATH}}"; export PYTHONPATH;

export DJANGO_SETTINGS_MODULE='settings.localdev'

env | grep -P 'PYTHONPATH|DJANGO_SETTINGS_MODULE'
