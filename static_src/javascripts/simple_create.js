/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

/* Include file to attach javascript actions to simple creation form */

$(document).ready(function() {
  /* Determine value of 'current_profile' based on shoulder that is selected  */
  var orig_val = $('input[name=shoulder]:checked', '#create_form').val();

  $("input[name=shoulder]").change(function(e) {
    var new_scheme = e.target.value.split(':')[0];
    if(orig_val.split(':')[0] != new_scheme){
    // changing scheme
      if(new_scheme == 'doi'){
        $('#current_profile').attr('value', 'datacite');
      }else{
        $('#current_profile').attr('value', 'erc');
      }
      $('#create_form').attr('method', 'get');
      $('#create_form').submit();
    }
    orig_val = e.target.value;
  });

  /* Redirect to Advanced ID create: Handle tab clicking for keyboard users */
  function actTab2() {
    document.getElementById('tab-2').checked = false;
    document.getElementById('tab-1').checked = true;
    action = location.pathname.split("/")[1];  // Handle create or demo pages
    window.location.href = "/" + action + "/advanced";
  }
  // Act on keyboard enter or spacebar
  $("#tab-2-label").keyup(function(e){
    var code = e.which;
    if(code==13)e.preventDefault();
    if(code==32||code==13||code==188||code==186){
      actTab2();
    }
  });

  $('#tab-2:not(:checked)').on('change', function() {
    actTab2();
  });

});
