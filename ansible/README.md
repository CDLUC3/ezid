Ansible project for building out the EZID UI application
========================================================

This project performs initial setup and installation of the UC3 EZID UI application.
It does not attempt to configure the application for service.

It is designed to work in conjunction with the uc3_ezid_ui puppet module.
But it could be used with docker also.

In general, the tasks in this project run as the application user.  It does
not touch any root owned resources.  This is left to puppet.


What Puppet does
----------------

- Configure bash shell environment for application user (SSM_ROOT_PATH, AWS_REGION)
- Install system package prerequisites
- Install ansible as $app_user
- Clone ansible project repo into $install_dir
- Install required additional ansible (Galaxy) roles.  These are used to set up pyenv.
- Manage `ansible_extra_vars.yaml` file.
- Run ansible-playbook to deploy application.
- Manage ezid service with systemd. 


What ezid-ansible does
----------------------

- Create application directory layout
- Setup python virtual environments with `pyenv`
- Install python packages on the virtualenv (`mod_wsgi`)
- Sets global pyenv (variable `pyenv_global`)
- Clone ezid repo (See: https://github.com/CDLUC3/ezid)
- Clone ezid-info-pages repo
- Install python packages needed by EZID (`Requirements.txt`)
- Configure ezid application using values retrived from SSM ParameterStore
- Configure httpd
- Manage helper scripts for systemd


Installation
------------

Puppet takes care of this part for you, but to be thorough:

1. Clone this repo onto your target host as the application user.

```
cd ${install_dir}
git clone https://github.com/CDLUC3/ezid-ansible
```

2. Install ansible galaxy pluggins for `pyenv`:

  ```
  # install ansible plugins
  ansible-galaxy install -r ${install_dir}/ezid-ansible/roles/requirements.yaml
  ```


Usage
-----

```
# Default deployment (see `group_vars/all`)
#
# dry-run 
ansible-playbook -i hosts site.yaml --check --diff
#
# for reals
ansible-playbook -i hosts site.yaml


# Supply varibles with --extra-vars flag to override defaults
ansible-playbook -i hosts site.yaml -e '{"project_branch": "2.0.1", "pyver_global": "ezid-py38"}


# Supply extra-args as yaml file.  This is the preferred method (what puppet does).
#
# dry-run
ansible-playbook -i hosts site.yaml -e @ansible_extra_vars.yaml -C -D
#
# for reals
ansible-playbook -i hosts site.yaml -e @ansible_extra_vars.yaml


# Test variable interpolation for extra vars file
ansible-playbook -i hosts test_vars.yaml -e @ansible_extra_vars.yaml
```


#### Using tags to limit which tasks get run

Tasks can be run selectively based on ansible tags.  These are set in `roles/ezid/tasks/main.yaml`

```
ezid-ansible> grep tags roles/ezid/tasks/main.yaml
  tags: setup_base_dirs
  tags: setup_pyenv
  tags: install_mod_wsgi
  tags: install_ezid
  tags: configure_ezid
  tags: configure_httpd
  tags: setup_scripts

# Use flag `--tags` to only run pyenv setup play
ansible-playbook -i hosts site.yaml -e @ansible_extra_vars.yaml --tags 'setup_pyenv'

# Use flag `--skip-tags` to opt out of application re-deployment
ansible-playbook -i hosts site.yaml -e @ansible_extra_vars.yaml --skip-tags 'install_ezid,configure_ezid'
```


Ansible Extra Vars File
-----------------------

We use the file `ansible_extra_vars.yaml` to set deployment specific variables.
This file is manage by puppet and lives in `${install_dir}/ezid-ansible`.  It is
ignored by git.  Varialbles set here have the highest scope of all ansible 
variables, overiding vars set in `group_vars/all` and those retrived from SSM
ParamterStore.

Here we define values for python virtual environments and what
version of the EZID project to deploy.

```
ezid-ansible$ cat ansible_extra_vars.yaml
---
user: ezid
group: ezid
app_dir: /ezid
ezid_branch: 3.0.0-0.0.0
pyenv_global: ezid-py38
virtual_environments:
- python_version: 2.7.18
  pyenv_name: ezid-py27
- python_version: 3.8.5
  pyenv_name: ezid-py38
```

From this example we see 2 pyenv are available, but that `ezid-py38` is
currently active as the `global pyenv`.



Ansible Vars and SSM ParameterStore
-----------------------------------

We are now using AWS SSM ParameterStore to stage configuration data and service
credentials.  These are applied to EZID config files using ansible templates
(jinga2).  Configuration parameter values differ depending on the
`DEPLOYMENT_LEVEL` of the service, e.g. remotedev, stage, production.

Ansible accesses SSM parameters using the `aws-ssm` lookup plugin
(https://docs.ansible.com/ansible/latest/collections/amazon/aws/aws_ssm_lookup.html).

This lookup is defined within `group_vars/all`.  The lookup depends upon
the `SSM_ROOT_PATH` shell environemt var which is pre-configured by puppet.

```
ssm_root_path: "{{ lookup('env', 'SSM_ROOT_PATH') | default('/no/path/') }}"
aws_region: "{{ lookup('env', 'AWS_REGION') | default('us-west-2') }}"

ssm_params: "{{ lookup(
    'aws_ssm',
    ssm_root_path,
    region=aws_region,
    bypath=true,
    recursive=true,
    shortnames=true,
    errors='ignore'
) | default( default_ssm_params, true ) }}"
```

This lookup slurps up all SSM params under the given path into a dictionary.
If the SSM lookup fails, such as when working on a local development
environment or in travis, the `ssm_params` dictionay inherits safe default values.

```
default_ssm_params:
  deployment_level: localdev
  admin_password: ''
  db_host: docker.for.mac.host.internal
  db_port: '4306'
  db_password: ''
```

Individual ansible vars are then extracted from the `ssm_params` dictionary for
use by ansible tasks and templates:

```
deployment_level:           "{{ ssm_params['deployment_level'] }}"
admin_password:             "{{ ssm_params['admin_password'] }}"
db_host:                    "{{ ssm_params['db_host'] }}"
db_port:                    "{{ ssm_params['db_port'] }}"
db_password:                "{{ ssm_params['db_password'] }}"
binder_password:            "{{ ssm_params['binder_password'] | default('') }}"
allocator_cdl_password:     "{{ ssm_params['allocator_cdl_password'] | default('') }}"
allocator_purdue_password:  "{{ ssm_params['allocator_purdue_password'] | default('') }}"
crossref_password:          "{{ ssm_params['crossref_password'] | default('') }}"
```



#### Setting and Checking Values in SSM ParameterStore

Our EZID ec2 servers are set up with read access to SSM ParameterStore values
under a path relevent to service environment.  This permission is specified 
within the ec2 instance profile applied to the server by our IAS team at build time. 

SSM ParameterStore values are set from our AWS operations host
which has write access to all SSM params under path `/uc3/`.

Setting a parameter:

```
aws ssm put-parameter --name /uc3/ezid/dev/allocator_cdl --value "xxxxxxxx" --type String
```

Updating a paramter value

```
aws ssm put-parameter --name /uc3/ezid/dev/allocator_cdl --value "yyyyyyyy" --type String --overwrite
```

Deleting a parameter

```
aws ssm delete-parameter --name /uc3/ezid/dev/binder_password
```

Reviewing parameter values

```
PARAMPATH=/uc3/ezid/dev/
aws ssm get-parameters-by-path --path $PARAMPATH --recursive --region us-west-2
```
