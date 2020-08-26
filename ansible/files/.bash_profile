# .bash_profile
#
# This file is managed by ansible project ezid-ansible.
# If you wish to make additions, place profile snippets under ~/.profile.d/

# Source global definitions
if [ -f /etc/profile ]; then
  . /etc/profile
fi


PATH=$HOME/bin:$PATH

# Optional Paths
if [ -d $HOME/.local/bin ] ; then PATH=$HOME/.local/bin:$PATH ; fi
if [ -d $HOME/local/bin ] ; then PATH=$HOME/local/bin:$PATH ; fi
export PATH


# Gather profile snippets
if [ -d $HOME/.profile.d ]; then
  . $HOME/.profile.d/*
fi


# Skip configuration if not running interactively
case $- in
  *i*) ;;
    *) return;;
esac


# Get the aliases and functions
if [ -f ~/.bashrc ]; then
        . ~/.bashrc
fi

