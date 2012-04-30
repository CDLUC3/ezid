/*
 * This will allow modal dialog boxes.
 * 
 * Create a div to contain your dialog box like this, %value% represents a value you substitute:
 * 
 * <div id="%div_id%" class="dialog_window">
 * 	 . . . contents . . .
 *   <a href="#close" class="close">Cancel</a>
 * </div>
 * 
 * Create a link to open the dialog like so:
 * <a href="#%div_id%" name="modal">Open my dialog</a>
 * 
 */

$(document).ready(function() {
	
	$('body').append('<div class="mask" id="mask"></div>');
	
	//select all the a tag with name equal to modal
  $('a[name=modal]').click(function(e) {

  	//Cancel the link behavior
    e.preventDefault();
    //Get the A tag
    var id = $(this).attr('href');
    var bl = $(id);
    
    // var x = e.pageX + 20;
    //var y = e.pageY + 20;
    var y = e.pageY - bl.height() / 2;
    var x = ($(window).width() - bl.width()) / 2;
    //var y = ($(window).height() - bl.height()) / 2;

    //transition effect   
    $('#mask').fadeIn(500);   
    $('#mask').fadeTo("fast",0.8); 

    
    bl.css('position', 'absolute');
    bl.css( 'top', y);
    bl.css( 'left', x); 
    //transition effect
    $(id).fadeIn(200);
 
    });
     
    //if close button is clicked
    $('.dialog_window .close').click(function (e) {
    	//Cancel the link behavior
      e.preventDefault();
      $('#mask').hide();
      $('.dialog_window').hide();
    });    
     
    //if mask is clicked
    $('#mask').click(function () {
      $(this).hide();
      $('.dialog_window').hide();
    });
        
});

$(document).keyup(function(e) {
  if(e.keyCode == 27) { // escape key
    $('#mask').hide();
    $('.dialog_window').hide();
  }
});

