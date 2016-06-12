/* include file to attach javascript actions to simple creation form */

$(document).ready(function() {
  /* Determine value of 'current_profile' based on shoulder that is selected  */
  var orig_val = $('input[name=shoulder]:checked', '#create_form').val();
	
  function do_get(){
      var frm = $('#create_form');
      frm.attr('action', location.pathname + '?publish=' + $("[name='publish']").val());
      frm.unbind('submit');
      frm.attr('method', 'get');
      frm.submit();
  }

  // submit form when shoulder changes 
  $("input[name=shoulder]").change(function(e) {
      var new_scheme = e.target.value.split(':')[0];
      if(orig_val.split(':')[0] != new_scheme){
        // changing scheme
          if(new_scheme == 'doi'){
              $('#current_profile').val('datacite');
          }else{
              $('#current_profile').val('erc');
          }
          do_get();
      }
      orig_val = e.target.value;
  });

  function setHarvestingHidden(){
      if ($('#publish_true').is(':checked')) {
          // public
          $("#harv_index").show();
      }else{
          // reserved
          $("#harv_index").hide();
      }
  }

  // When publish button is selected, hide or reveal harvesting selector
  $("[name='publish']").bind("change", function(){
      setHarvestingHidden();
  });
  setHarvestingHidden();

  // submit form when profile changes
  $("#current_profile").bind("change", function(event){
      do_get();
  });

  // When user submits: 
  // If ID is submitted as reserved (publish=="False")
  // populate any empty required form fields with '(:tba)'
  $('#create__button').click(function() {
      if ($("input:radio[name=publish]:checked").val() == "False") {
          $('.create__form-element-group').find('input').each(function() {
              reqd_label = $(this).parents('.create__form-element-group').find('.fcontrol__label-required');
              if ((reqd_label.length > 0) && ($.trim( $(this).val() ) == '')) { 
                  if ((reqd_label.attr('for') == 'dc.date') || 
                    (reqd_label.attr('for') == 'publicationYear')) {
                      $(this).val('0000');
                  } else {
                      $(this).val('(:tba)');
                  }
              }
          });
      }
      $('#create_form').submit();
  });

  /* Redirect to Simple ID create: Handle tab clicking for keyboard users */
  function actTab1() {
    document.getElementById('tab-1').checked = false;
    document.getElementById('tab-2').checked = true;
    action = location.pathname.split("/")[1];  // Handle create or demo pages
    window.location.href = "/" + action + "/simple";
  }
  // Act on keyboard enter or spacebar
  $("#tab-1-label").keyup(function(e){
    var code = e.which;
    if(code==13)e.preventDefault();
    if(code==32||code==13||code==188||code==186){
      actTab1();
    }
  });
/* ToDo: Bring in both simple and advanced content onto the same page
   Then this JavaScript will be unnecessary since tabs will swap quickly
   btwn simple/advanced content */
  $('#tab-1:not(:checked)').on('change', function() {
    actTab1();
  });

});
