/* include file to attach javascript actions to simple creation form */

$(document).ready(function() {
  var orig_val = $('input[name=shoulder]:checked', '#create_form').val();
	
  $("input[name=shoulder]").change(function(e) {
      var new_scheme = e.target.value.split(':')[0];
      if(orig_val.split(':')[0] != new_scheme){
        // changing scheme
          if(new_scheme == 'doi'){
              $('#current_profile').val('datacite');
          }else{
              $('#current_profile').val('erc');
          }
          var frm = $('#create_form');
          frm.attr('action', location.pathname);
          frm.unbind('submit');
          frm.attr('method', 'get');
          frm.submit();
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

  // submit form when profile changed
  $("#current_profile").bind("change", function(event){
      var frm = $('#create_form');
      frm.attr('action', location.pathname);
      frm.unbind('submit');
      frm.attr('method', 'get');
      frm.submit();
  });

  // If ID is submitted as reserved (publish=="False")
  // populate any empty required form fields with '(:tba)'
  $('#create__button').click(function() {
      if ($("input:radio[name=publish]:checked").val() == "False") {
          $('.create__form-element-group').find('input').each(function() {
              reqd_label = $(this).parents('.create__form-element-group').find('.fcontrol__label-required');
              if ((reqd_label.length > 0) && ($.trim( $(this).val() ) == '')) { 
                  if (reqd_label.attr('for') == 'dc.date') {
                      $(this).val('0000');
                  } else {
                      $(this).val('(:tba)');
                  }
              }
          });
      }
      $('#create_form').submit();
  });
});
