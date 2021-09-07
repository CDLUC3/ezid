/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

/* Include file to attach javascript action to ID creation and edit forms
   Prepends 'http://' to target URL if it doesn't have one.   */

$( "#create_form,#edit_form" ).submit(function( event ) {
  var url = $('#target').val().trim();
  var slashes = '//';

  if (!url.match(/^[\s\t]*?$/) && !url.match(/^[a-zA-Z]+:\/\//))
  {
    if (url.match(/^\/\//)) {
      slashes = '';
    }
    url = 'http:' + slashes + url;
  }
  $('#target').val(url);
  return true;
});
