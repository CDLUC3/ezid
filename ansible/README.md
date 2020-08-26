-bash-4.2$ which ansible-playbook
~/.local/bin/ansible-playbook
-bash-4.2$ ansible-playbook playbooks/main.yaml
[WARNING]: No inventory was parsed, only implicit localhost is available
[WARNING]: provided hosts list is empty, only localhost is available. Note that the implicit localhost does not match 'all'

PLAY [localhost] ****************************************************************************************************************************************************

TASK [Gathering Facts] **********************************************************************************************************************************************
ok: [localhost]

TASK [test connection] **********************************************************************************************************************************************
ok: [localhost]

PLAY RECAP **********************************************************************************************************************************************************
localhost                  : ok=2    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0


