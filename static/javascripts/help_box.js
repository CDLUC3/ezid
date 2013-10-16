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
    var helpbox = $(id);
    
    var icon = $(e.target);
    
    var icon_pos = icon.offset();
    
    var scrolltop = $(document).scrollTop();
    var scrollbottom = scrolltop + $(window).height();
    var offset_from_icon = 12;
    
    var icon_center_top = icon_pos.top + icon.outerHeight() / 2;
    		
   	var helpbox_full_height = helpbox.outerHeight();	
    
    if(icon_center_top - helpbox_full_height > scrolltop ){
    	// display above icon
    	var top = icon_center_top - helpbox_full_height - offset_from_icon;
    }else if(icon_center_top + helpbox_full_height < scrolltop + $(window).height()){
    	// display below icon
    	var top = icon_center_top + offset_from_icon;
    }else{
    	// display above icon
    	var top = icon_center_top - helpbox_full_height - offset_from_icon;
    }
    if(top < 1) top = 1;
    
    var helpbox_full_width = helpbox.outerWidth();
    
    var icon_center_left = icon_pos.left + icon.outerWidth()/2;

    var left = icon_center_left - helpbox_full_width / 2;

    if(left + helpbox_full_width > $(window).scrollLeft() + $(window).width() ){
    	left = $(window).scrollLeft() + $(window).width() - helpbox_full_width;
    }
    if(left<1) left = 1;
    
    helpbox.css('position', 'absolute');
    helpbox.css( 'top', top);
    helpbox.css( 'left', left); 
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

