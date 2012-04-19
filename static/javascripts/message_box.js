//#status messages
$(document).ready(function() {
	//alert($("#status:not(:empty)").length);
	//alert($('status').innerHtml());
	if ($.trim($("#status").html())){
		$('#status').prepend('<div class="close_button"><a href="#close" class="close"><img src="/ezid/static/images/close_it.png" alt="close button" title="close button"/></a></div>');
		var x = $(window).width() / 2 - $('#status').width() / 2;
		$('#status').css('position', 'absolute');
    $('#status').css( 'top', 20);
    $('#status').css( 'left', x); 
    //transition effect
    $('#status').fadeIn(100);
    
    //if close button is clicked
  	$('#status .close').click(function (e) {
  		//Cancel the link behavior
    	e.preventDefault();
    	$('#status').hide();
  	});
  	
		$(document).keyup(function(e) {
		  if(e.keyCode == 27) { // escape key
		    $('#status').hide();
		  }
		});
	}// end if
});