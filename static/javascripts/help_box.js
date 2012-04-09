/*
 * This will allow help boxes.
 * 
 * Create a div to contain your help box like this, %value% represents a value you substitute:
 * 
 * <div id="%div_id%" class="help_window">
 * 	<a href="#close" class="close">Cancel</a>
 * 	 . . . contents . . .
 *   
 * </div>
 * 
 * Create a link to open the help dialog like so:
 * <a href="#%div_id%" name="help_dialog">Open my help</a>
 * 
 */

$(document).ready(function() {
	
	//select all the a tag with name equal to modal
  $('a[name=help_dialog]').click(function(e) {

  	//Cancel the link behavior
    e.preventDefault();
    //Get the A tag
    var id = $(this).attr('href');
    var bl = $(id);
    
    var x = e.pageX;
    // var y = e.pageY + 20;
    // var y = e.pageY - bl.height() / 2;
    var y = e.pageY + 20;
    // var y = e.pageY - bl.height() - 30;
    // var x = ($(window).width() - bl.width()) / 2;
    //var y = ($(window).height() - bl.height()) / 2;

    
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
        
});

$(document).keyup(function(e) {
  if(e.keyCode == 27) { // escape key
    $('.help_window').hide();
  }
});

