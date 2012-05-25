/*
 * This will allow expanding/contracting divs along with a link to expand/contract them.
 * 
 * Create a link to open the div like so:
 * <a href="#%div_id%" class="expanding_link">Open my section</a>
 * 
 * Create a div to contain your hidden information like below, %value% represents a value you substitute:
 * 
 * <div id="%div_id%" class="expanding_section">
 * 	 . . . contents . . .
 * </div>
 * 
 * Note the div_id around the contents and the div_id in the href for the link must match,
 * (though the div_id in the href has a # in front of it)
 * 
 */

$(document).ready(function() {
	//select all the a tag with name equal to help_link
  $('a.expanding_link').click(function(e) {

  	//Cancel the link behavior
    e.preventDefault();
    //Get the A tag
    var id = $(this).attr('href');
    var bl = $(id);
    
    if(bl.is(":visible")){
    	bl.fadeOut(50);
    }else{
    	bl.fadeIn(50);
    }
 
  }); 
});

