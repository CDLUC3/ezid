//#status messages
$(document).ready(showMessage());

function showMessage(top_window){
	top_window = typeof top_window !== 'undefined' ? top_window : false;
	// if top_windows is true, set at top of window, otherwise, top of page
	if ($.trim($("#ustatus").html())){
		if($('#ustatus .close').length<1){ 
			$('#ustatus').prepend('<div class="close_button"><a href="#close" class="close"><img src="/ezid/static/images/application-exit.png" width="16" height="16" alt="close button" title="close button"/></a></div>');
		}
		var x = $(window).width() / 2 - $('#ustatus').width() / 2;

		
		$('#ustatus').css('position', 'absolute');
		if(top_window){
			var y = $(document).scrollTop() + 20;
			$(window).scroll(function(e){
				var y = $(document).scrollTop() + 20;
				$('#ustatus').css( 'top', y);
			});
		}else{
			var y = 20;
		}
    $('#ustatus').css( 'top', y);
    $('#ustatus').css( 'left', x); 
    //transition effect
    $('#ustatus').fadeIn(100);
    
    if(autohide && $('#ustatus .error').length < 1){
    	window.setTimeout(function() {
 				$('#ustatus').fadeOut('slow');
			}, $('#ustatus').height() * 70);
		}
 
    //if close button is clicked, remove any existing first
    $('#ustatus .close').unbind('click');
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
}

 var entityMap = {
    "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': '&quot;',
  "'": '&#39;',
  "/": '&#x2F;'
};

/* Good for use with AJAX where it might not be escaped */
function escapeHtml(string) {
  return String(string).replace(/[&<>"'\/]/g, function (s) {
    return entityMap[s];
  });
}
