/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

/* JavaScript actions for advanced ID creation form */
$(document).ready(function() {

// ***** Navigational Tabs Simple <-> Advanced ***** //

  /* Redirect to Simple ID create: Handle tab clicking for keyboard users */
  function actTab1() {
    document.getElementById('tab-1').checked = false;
    document.getElementById('tab-2').checked = true;
    var action = location.pathname.split("/")[1];  // Handle create or demo pages
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


// ***** Shoulder Selection ***** //

  /* Determine value of 'current_profile' based on shoulder that is selected  */
  var orig_scheme = $('input[name=shoulder]:checked', '#create_form').val();

  // submit form when shoulder changes
  $("input[name=shoulder]").change(function(e) {
      var new_scheme = e.target.value.split(':')[0];
      if(orig_scheme.split(':')[0] != new_scheme){
        // changing scheme
          if(new_scheme == 'doi'){
              $('#current_profile').val('datacite');
          }else{
              $('#current_profile').val('erc');
          }
          do_get();
      }
      orig_scheme = e.target.value;
  });


// ***** Publish/Reserved Selection ***** //

  // When publish button is selected, hide or reveal harvesting selector
  $("[name='publish']").bind("change", function(){
      setHarvestingHidden();
  });
  setHarvestingHidden();

  function setHarvestingHidden(){
      if ($('#publish_true').is(':checked')) {
          // public
          $("#harv_index").show();
      }else{
          // reserved
          $("#harv_index").hide();
      }
  }

// ***** Profile Selection ***** //

  // submit form when profile changes
  $("#current_profile").bind("change", function(event){
      var includeAnchor = true;
      do_get(includeAnchor);
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


// ***** Submit form when profile or shoulder changes ******* //

  // If triggered by profile, then, after submission, scroll page down to specified anchor
  function do_get(includeAnchor){
      var frm = $('#create_form');
      frm.attr('action', location.pathname + '?publish=' +
        $("[name='publish']").val() + '&remainder=' + $("#remainder").val());
      if (includeAnchor) {
        var input = $("<input>", { type: "hidden", name: "anchor", value: "current_profile" });
        frm.append($(input));
      }
      frm.unbind('submit');
      frm.attr('method', 'get');
      frm.submit();
  }

});
