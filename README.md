# EZID dev setup

Keeping setup instructions separate from the [original README](README.orig.md) for now.

## Packaged dependencies

```shell script

sudo bash -c '
    apt update
    apt dist-upgrade -fy
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

Prepare pyenv

```shell script
curl https://pyenv.run | bash
```

- Follow the instructions printed at the end of the pyenv setup.  

Install Python 2.7

```shell script
bash -c '
    pyver=2.7.18
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
    export ez=$HOME/dev
    mkdir -p $ez
    cd $ez
    
    git clone https://github.com/CDLUC3/ezid.git
    git clone https://github.com/CDLUC3/ezid-info-pages.git ezid/templates/info
    
    cd $ez/ezid && git checkout initial-setup
    cd $ez/ezid/templates/info && git checkout initial-setup 

    cd $ez/ezid
    pip install -r requirements.txt

    ./dev_prep_env.sh
'
```

DB Init or reinit

```shell script
bash -c '
    rm -f ./db/*.sqlite3
    ./manage.py migrate
    ./manage.py migrate --database=search
    ./manage.py loaddata store-init
    ./manage.py loaddata search-init --database=search
'
```

Optionally, load more complete test database

```shell script
bash -c '
    yes 'yes' | ./manage.py flush
    ./manage.py loaddata store-test -e auth -e contenttypes -e sessions
'
```

```shell
# TODO: Outline setup via setup.py
# Dev env with: ./setup.py develop
# pyenv rehash
# Tools now available as ez-* (use tab to get a list) 
```

Start

```shell script
$ export ez=$HOME/dev
$ cd $ez/ezid
$ ./manage.py runserver
```

## Git

Set Git to ignore bulk edits in `git blame`:

```shell script
$ cd <ezid root>
$ git config blame.ignoreRevsFile .git-blame-ignore-revs
```


