# ~/.bashrc

# Creaed by ansible project: ezid-ansible.  But you can make local changes.
# Content extracted from .bash_profile on uc3-ezidx2-dev


# Color
#
# Colored GCC warnings and errors.
export TERM=xterm-256color
export COLORTERM=truecolor
export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'
# Magic that causes output to stderr to be colored red
stderred="$HOME/bin/_stderred/libstderred.so"
if [ -f "$stderred" ]; then
  export LD_PRELOAD="$stderred${LD_PRELOAD:+:$LD_PRELOAD}"
fi
# Aliases to turn stderr coloring on and off (it's on by default)
alias red-off='LD_PRELOAD_RED_OFF=$LD_PRELOAD; unset LD_PRELOAD'
alias red-on='LD_PRELOAD=$LD_PRELOAD_RED_OFF; unset LD_PRELOAD_RED_OFF'
eval "$(dircolors)"


# Prompt
#
PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;33m\]\t\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '


# History
#
# The default HISTCONTROL setting normally includes "ignoreboth", which causes lines
# starting with one or more spaces not to be added to the history. Since leading spaces
# are often included accidentally when copy/pasting commands into the shell, it's
# removed here.
HISTCONTROL=erasedups
# Append to the history file, don't overwrite it.
shopt -s histappend
# History length
HISTSIZE=1000
HISTFILESIZE=2000
# Include timestamps
HISTTIMEFORMAT='%Y-%m-%d %H:%M:%s  '


# Check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# The pattern "**" used in a pathname expansion context will match all files and zero or
# more directories and subdirectories.
shopt -s globstar

# Make less more friendly for non-text input files.
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# Make 'less' scroll lines just before a match into view (shows context)
export LESS="${LESS}j5 -R"

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h \w\a\]$PS1"
    ;;
*)
    ;;
esac


# Local aliases
if [ -f $HOME/.alias ]; then
  . $HOME/.alias
fi

# Source local
if [ -f "\$HOME"/.bashrc_local ]; then
  . "\$HOME"/.bashrc_local
fi



