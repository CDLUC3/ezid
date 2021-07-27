#!/bin/bash

if [ ${1} == "dev" ]; then
  cp ui_library/css/main2.min.css static/stylesheets/
  echo -e "Copied ui_library/css/main2.min.css to static/stylesheets"
  cp ui_library/js/main2.min.js static/javascripts/
  echo -e "Copied ui_library/js/main2.min.js to static/javascripts\n"
elif [ ${1} == "css" ]; then
  cleancss -o ui_library/css/main2.min.css dev/css/main2.css
  echo -e "Minified ui_library/css/main2.min.css"
else 
  echo "Usage: bash buildStyles.bash [dev|css]."
  echo "Please recheck the variable."
  exit 1
fi
