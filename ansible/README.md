Ansible project for building out the EZID UI application
========================================================


Integration with Puppet
-----------------------


This is the copy of the uc3_ezid_ui puppet `config` manifest as of
Wed Oct 21 10:56:51 PDT 2020

```
agould@uc3-ezidui01x2-prd:~/puppet/uc3/modules/uc3_ezid_ui> cat manifests/config.pp
define uc3_ezid_ui::config (
    $service_ensure  = "running",
    $package_ensure  = "installed",
    $user            = lookup('app_user',),
    $group           = lookup('app_group'),
    $home_dir        = lookup('app_home'),
    $install_dir     = "$home_dir/install",
    $localbin_dir    = "$home_dir/local/bin",
    $git_repo        = undef,
    $revision        = undef,
){

    # kludge for testing on uc3ops-dev
    if $home_dir != "/ezid" {
        file {"/apps/ezid":
            ensure => present,
            target => "/apps/uc3adm",
        }
    }

    # Set up application directory layout
    #
    file {[
        "$install_dir",
    ]:
        ensure => directory,
        owner  => $user,
        group  => $group,
        mode   => "0755",
    }


    $package_list = [
        httpd-devel,
        mariadb,
        mariadb-devel,
        openssl-devel,
        python2-pip,
        bzip2-devel,
        readline-devel,
        sqlite-devel,
        xz-devel,
    ]
    ensure_packages($package_list, {ensure => $package_ensure})


    # install ansible as app_user
    exec { "/usr/bin/pip install --user ansible":
        user     => $user,
        group    => $group,
        unless   => "/usr/bin/pip show ansible"
    }

    # clone ansible project repo into install_dir
    vcsrepo { "ezid-ansible":
        ensure   => present,
        path     => "${install_dir}/ezid-ansible",
        provider => git,
        source   => $git_repo,
        revision => $revision,
        owner    => $user,
        user     => $user,
        group    => $group,
        require  => File[$install_dir],
    }
   # install required galaxy roles
    exec { "ansible-galaxy install":
        command     => "ansible-galaxy install -r ${install_dir}/ezid-ansible/roles/requirements.yml",
        user        => $user,
        group       => $group,
        path        => "${home_dir}/.local/bin",
        subscribe   => Vcsrepo["ezid-ansible"],
        refreshonly => true,
    }

    # deploy ansible project
    exec { "ansible-playbook -i hosts site.yaml":
        command     => "/usr/bin/su - $user -c \"cd $install_dir/ezid-ansible && ${home_dir}/.local/bin/ansible-playbook -i hosts site.yaml\"",
        subscribe   => Vcsrepo["ezid-ansible"],
        refreshonly => true,
        require     => Exec["ansible-galaxy install"],
    }

    systemd::unit_file { 'ezid.service':
     source => "puppet:///modules/uc3_ezid_ui/ezid.service",
    }
    ~> service {'ezid':
      ensure => 'running',
    }


}
```
