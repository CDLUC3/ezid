#!/usr/bin/env bash

# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD

# Format the output of `./manage diffsettings` for readability.
#
# '###', which is added to diffsettings to denote settings that are custom or modified from the
# Django defaults, is not accurate, and not that helpful anyway, so we strip it out.

split_sections() {
  # language=perl
  perl -ne '
    BEGIN {
      $last = "";
    };
    m/^(.*?)_/;
    $this=$1;
    if ($this ne $last) {
      print "\n";
    };
    print $_;
    $last=$this;
  '
}

cat \
  <(printf '# Env: DJANGO_SETTINGS_MODULE: %s\n' "${DJANGO_SETTINGS_MODULE:-<unset>}") \
  <(./manage.py diffsettings) \
  | perl -pe 's/ *### *$//g' \
  | split_sections \
  | black - --quiet \
  | bat --language=python --pager less
