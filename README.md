# EZID dev setup

Keeping setup instructions separate from the [original README](README.orig.md) for now.

## Packaged dependencies

```shell script

sudo bash -c '
    apt update
    apt -fy dist-upgrade
    apt install -y \
        \    
        build-essential \
        llvm \
        make \
        \
        python2-dev \
        python-openssl \
        python-setuptools \
        \
        bash \
        curl \
        wget \
        git \
        xz-utils \
        \
        libbz2-dev \
        libc6-dev \
        libdb-dev \
        libedit-dev \
        libffi-dev \
        libgdbm-dev \
        liblzma-dev \
        libmariadbclient-dev
        libncurses5-dev \
        libncursesw5-dev \
        libreadline-dev \
        libsqlite3-dev \
        libssl-dev \
        libz-dev \
        tk-dev \
        zlib1g \
        zlib1g-dev \
        \
        sqlite3 \
'
```

## Python 2.7

```shell script
curl https://pyenv.run | bash
```

- Install and activate the env vars printed at the end of the pyenv setup.  

```shell script
bash -c '
    pyver=2.7.17
    venv=ezid_${pyver}
    export CONFIGURE_OPTS=--enable-shared
    export CFLAGS=-O2
    pyenv install ${pyver}
    pyenv virtualenv ${pyver} ${venv}
    pyenv global ${venv}
    pip install --upgrade pip
'
```

## EZID

```shell script
bash -c '
    export ez=$HOME/ezid
    mkdir -p $ez
    cd $ez
    
    git clone https://github.com/CDLUC3/ezid.git
    git clone https://github.com/CDLUC3/ezid-info-pages.git ezid/templates/info
    
    cd $ez/ezid && git checkout initial-setup
    cd $ez/ezid/templates/info && git checkout initial-setup 

    cd $ez/ezid
    pip install -r requirements.txt

    ./dev_prep_env.sh

    django-admin migrate
    django-admin migrate --database=search
'

. ./dev_env_vars.sourceme.sh 

django-admin runserver
```
