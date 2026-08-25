/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

//#status messages
$(document).ready(function() { showMessage(); });

function showMessage(top_window){
  //if close button is clicked, remove any existing first
  $('#ustatus .close').off('click').on('click', function (e) {
    //Cancel the link behavior
    e.preventDefault();
    $('#ustatus').hide();
    $.post('/ajax_hide_alert');
  });

  $(document).on('keyup', function(e) {
    if(e.keyCode == 27) { // escape key
    $('#ustatus').hide();
    $.post('/ajax_hide_alert');
  }
  });
}
