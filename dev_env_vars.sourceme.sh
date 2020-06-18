# Set up env vars for EZID app. Must be sourced from dir holding this file.

PYTHONPATH="$(realpath .):$(realpath ..):$(realpath impl)"; export PYTHONPATH
export DJANGO_SETTINGS_MODULE='settings.localdev'
env | grep -P 'PYTHONPATH|DJANGO_SETTINGS_MODULE'

