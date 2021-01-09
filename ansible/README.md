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
ansible-galaxy install -r ${install_dir}/ezid-ansible/roles/requirements.yaml
ansible-playbook -i hosts site.yaml
```

What Puppet does
----------------

- Set up application directory layout
- Install system package prerequisites
- Install ansible as $app_user
- Clone ansible project repo into $install_dir
- Install required additional ansible (Galaxy) roles.  These are used to set up pyenv.
- Run ansible-playbook to deploy application.
- Manage ezid service with systemd (calls etc/init.d/apache for now)


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
- Install python packages needed by EZID (Requirements.txt)
- Do preliminary application setup:

  - symlink httpd modules
  - symlink ezid logs
  - symlink httpd magic
  - symlink download dir
  - httpd.conf
  - httpd/conf.d/*
  - httpd/conf.modules.d/*
  - etc/init.d/*
  - ezid_env.sh
  - robots.txt
  - ezid_env.sh


