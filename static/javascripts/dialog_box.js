/*
 * This will allow modal dialog boxes.
 * 
 * Create a link to open the dialog with the following properties:
 * name="modal"   href="#<id_of_div_to_show>"
 * 
 * The dialog div should be like so:
 * <div class="dialog_window" id="<id_of_div_as_in_above>">
 *   
 *   Closing link inside the dialog:
 *   <a class="close">close me</a>
 * 
 * </div>
 * 
 */

$(document).ready(function() {
	
	//select all the a tag with name equal to modal
  $('a[name=modal]').click(function(e) {

  	//Cancel the link behavior
    e.preventDefault();
    //Get the A tag
    var id = $(this).attr('href');
    
    var x = e.pageX + 20;
    var y = e.pageY + 20;

    //transition effect   
    $('#mask').fadeIn(500);   
    $('#mask').fadeTo("fast",0.8); 

    bl = $(id);
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
    
    $('body').append('<div class="mask" id="mask"></div>');    
});

$(document).keyup(function(e) {
  if(e.keyCode == 27) { // escape key
    $('#mask').hide();
    $('.dialog_window').hide();
  }
});

