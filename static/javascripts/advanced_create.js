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
	
	// submit form when profile changed
  $("#current_profile").bind("change", function(event){
  	var frm = $('#create_form');
		frm.attr('action', location.pathname);
		frm.unbind('submit');
  	frm.attr('method', 'get');
    frm.submit();
  });
});