/*
 * This will allow help boxes.
 * 
 * Create a div to contain your help box like this, %value% represents a value you substitute:
 * 
 * <div id="%div_id%" class="help_window">
 * 	 . . . contents . . .
 * </div>
 * 
 * Create a link to open the help like so:
 * <a href="#%div_id%" name="help_link">Open my help</a>
 * 
 * Note the div_id around the contents and the div_id in the href for the link must match,
 * (though the div_id in the href has a # in front of it)
 * 
 */

$(document).ready(function() {
	
	//add close buttons to all help_window classes
	$('.help_window').prepend('<div class="close_button"><a href="#close" class="close"><img src="/ezid/static/images/close_it.png" alt="close button" title="close button"/></a></div>');
	//select all the a tag with name equal to help_link and add click functions
  $('a[name=help_link]').click(function(e) {

  	//Cancel the link behavior
    e.preventDefault();
    //Get the A tag
    var id = $(this).attr('href');
    var bl = $(id);
    
    var pos = $(e.target).offset();
    
    // option for putting above and centered on clicked link
    var x = pos.left - bl.width() / 2;
    var y = pos.top - bl.height() - 25;
    if (y < 1){
    	// option for putting below and right of clicked link
    	var x = pos.left; // left/right
    	var y = pos.top + 20; // up/down
    }
    
    bl.css('position', 'absolute');
    bl.css( 'top', y);
    bl.css( 'left', x); 
    //transition effect
    $(id).fadeIn(100);
 
  });
     
  //if close button is clicked
  $('.help_window .close').click(function (e) {
  	//Cancel the link behavior
    e.preventDefault();
    $('.help_window').hide();
  });
  
	//select all the a tag with name equal to code_insert_link and add click functions
  $('a[name=code_insert_link]').click(function(e) {

  	//Cancel the link behavior
    e.preventDefault();
    
    var parts = $(this).attr('href').replace('#', '').split("_");
    var code = "(:" + parts[0] + ")";
    var field = document.getElementById(parts[1]);
    
    field.value = code;
    
    $('.help_window').hide();
  });
        
});

$(document).keyup(function(e) {
  if(e.keyCode == 27) { // escape key
    $('.help_window').hide();
  }
});

