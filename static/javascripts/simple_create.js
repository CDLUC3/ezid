/* Include file to attach javascript actions to simple creation form 
   Determines value of 'current_profile' based on shoulder that is selected   */

$(document).ready(function() {
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
});
