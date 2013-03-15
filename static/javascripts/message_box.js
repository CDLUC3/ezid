//#status messages
$(document).ready(function() {
	if ($.trim($("#ustatus").html())){
		$('#ustatus').prepend('<div class="close_button"><a href="#close" class="close"><img src="/ezid/static/images/application-exit.png" width="16" height="16" alt="close button" title="close button"/></a></div>');

		var x = $(window).width() / 2 - $('#ustatus').width() / 2;
		var y = 20;
		
		$('#ustatus').css('position', 'absolute');
    $('#ustatus').css( 'top', y);
    $('#ustatus').css( 'left', x); 
    //transition effect
    $('#ustatus').fadeIn(100);
    
    if(autohide && $('#ustatus .error').length < 1){
    	window.setTimeout(function() {
 				$('#ustatus').fadeOut('slow');
			}, $('#ustatus').height() * 70);
		}
 
    //if close button is clicked
  	$('#ustatus .close').click(function (e) {
  		//Cancel the link behavior
    	e.preventDefault();
    	$('#ustatus').hide();
    	$.post('/ezid/ajax_hide_alert');
  	});
  	
		$(document).keyup(function(e) {
		  if(e.keyCode == 27) { // escape key
		    $('#ustatus').hide();
		    $.post('/ezid/ajax_hide_alert');
		  }
		});
	}// end if
});