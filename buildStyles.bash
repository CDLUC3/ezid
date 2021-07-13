#!/bin/bash

if [ ${1} == "dev" ]; then
  cp ~/SITE/PROJECT/ui_library/css/main2.min.css ~/SITE/PROJECT/static/stylesheets/
  echo -e "Copied ui_library/css/main2.min.css to static/stylesheets"
  cp ~/SITE/PROJECT/ui_library/js/main2.min.js ~/SITE/PROJECT/static/javascripts/
  echo -e "Copied ui_library/js/main2.min.js to static/javascripts\n"
elif [ ${1} == "css" ]; then
  cleancss -o ~/SITE/PROJECT/ui_library/css/main2.min.css ~/SITE/PROJECT/static/dev/css/
  echo -e "Minified ui_library/css/main2.min.css"
else 
  echo "Usage: bash buildStyles.bash [dev|css]."
  echo "Please recheck the variable."
  exit 1
fi