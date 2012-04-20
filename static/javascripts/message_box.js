//#status messages
$(document).ready(function() {
	//alert($("#status:not(:empty)").length);
	//alert($('status').innerHtml());
	if ($.trim($("#status").html())){
		//$('#status').prepend('<div class="close_button"><a href="#close" class="close"><img src="/ezid/static/images/close_it.png" alt="close button" title="close button"/></a></div>');
		$('#status').prepend('<div class="close_button"><a href="#close" class="close">hide message</a></div>');
		/*var h = 0;
		if($(window).height() < $(document).height()){
			h = $(window).height();
		}else{
			h = $(document).height();
			var y = h / 2 - $('#status').height() / 2 - 100;
		}
		 */
		var x = $(window).width() / 2 - $('#status').width() / 2;
		var y = 20;
		
		$('#status').css('position', 'absolute');
    $('#status').css( 'top', y);
    $('#status').css( 'left', x); 
    //transition effect
    $('#status').fadeIn(100);
    
    if(autohide){
    	window.setTimeout(function() {
 				$('#status').fadeOut('slow');
			}, $('#status').height() * 50);
		}

    
    //if close button is clicked
  	$('#status .close').click(function (e) {
  		//Cancel the link behavior
    	e.preventDefault();
    	$('#status').hide();
    	$.post('/ezid/account/ajax_hide_alert');
  	});
  	
		$(document).keyup(function(e) {
		  if(e.keyCode == 27) { // escape key
		    $('#status').hide();
		    $.post('/ezid/account/ajax_hide_alert');
		  }
		});
	}// end if
});