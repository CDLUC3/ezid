Ansible project for building out the EZID UI application
========================================================

This project performs initial setup and installation of the UC3 EZID UI application.
It does not attempt to configure the application for service.

It is designed to work in conjunction with the uc3_ezid_ui puppet module.
But it could be used with docker also.

In general, the tasks in this project run as the application user 'ezid'.  It does
not touch any root owned resources.  This is left to puppet.


Usage
-----

```
# install ansible plugins
ansible-galaxy install -r ${install_dir}/ezid-ansible/roles/requirements.yaml

# dry-run
ansible-playbook -i hosts site.yaml --check --diff

# make it so
ansible-playbook -i hosts site.yaml

# with extra args as json string
ansible-playbook -i hosts site.yaml -e '{"repo_branch": "2.0.0", "pyver": "3.8.5"}
```

What Puppet does
----------------

- Set up application directory layout
- Set shell envronment var SSM_ROOT_PATH in `~/.profile.d/aws_profile`
- Install system package prerequisites
- Install ansible as $app_user
- Clone ansible project repo into $install_dir
- Install required additional ansible (Galaxy) roles.  These are used to set up pyenv.
- Run ansible-playbook to deploy application.
- Manage ezid service with systemd. 


What ezid-ansible does
----------------------

- Create application directory layout
- Configure bash shell environment for application user

  - ~/.bash_profile
  - ~/.bashrc
  - ~/.alias
  - ~/.profile.d/pyenv

- Setup python virtual environment with `pyenv`
- Install python packages on the virtualenv (`mod_wsgi`)
- Clone ezid repo (See: https://github.com/CDLUC3/ezid)
- Clone ezid-info-pages repo
- Install python packages needed by EZID (`Requirements.txt`)
- Configure ezid application using values retrived from SSM ParameterStore

  - ezid configuration:

    - ~/ezid/settings/ezid.conf.shadow

  - httpd configuration:

    - symlink httpd modules
    - symlink ezid logs
    - symlink httpd magic
    - symlink download dir
    - httpd.conf
    - httpd/conf.d/
    - httpd/conf.modules.d/
    - robots.txt

  - manage helper scripts for systemd

    - etc/init.d/pause_ezid.sh
    - etc/init.d/exercise_ezid.sh



Ansible Vars and SSM ParameterStore
-----------------------------------

We are now using AWS SSM ParameterStore to stage configuration data and service
credentials.  These are applied to EZID config files using ansible templates
(jinga2).  Configuration parameter values differ depending on the
`DEPLOYMENT_LEVEL` of the service, e.g. remotedev, stage, production.

Ansible accesses SSM parameters using the `aws-ssm` lookup plugin
(https://docs.ansible.com/ansible/latest/collections/amazon/aws/aws_ssm_lookup.html).

This lookup is defined within `group_vars/all.yaml`.  The lookup depends upon
the `SSM_ROOT_PATH` shell environemt var which is pre-configured by puppet in
`~/.profile.d/aws_profile`:

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
`uc3-aws-ops.cdlib.org` which has write access to all SSM params under path
`/uc3/`.

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
aws ssm delete-parameter --name /uc3/ezid/dev/binder_passwork
```

Reviewing parameter values

```
PARAMPATH=/uc3/ezid/dev/
aws ssm get-parameters-by-path --path $PARAMPATH --recursive --region us-west-2
```
