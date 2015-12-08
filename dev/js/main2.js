// ##### Main JavaScript ##### //

$(document).ready(function(){
  
  // ***** Show/hide mobile menu via mobile menu icon ***** //

  // Before toggling menu, change default header menu class to non-selected state and change default aria attribute:

  $('#js-header__nav').attr('class', 'header__nav');
  $('#js-header__nav').attr('aria-hidden', 'true');

  // Toggle classes and attributes:
  $('#js-header__nav-button').click(function(){
    
    $('#js-header__nav').toggleClass('header__nav header__nav--selected', 300, 'easeInOutCubic');

    if($('#js-header__nav').attr('aria-hidden') == 'true') {
      $('#js-header__nav').attr('aria-hidden', 'false');
    } else {
      $('#js-header__nav').attr('aria-hidden', 'true');
    }

  });

  // ***** Accordion ***** //

  // Pre-open an accordion section by retrieving the referring URL hash (up to 2 digits), removing the hash tag, and adding the hash value to the jQuery selector:

  var urlhash = window.location.hash.substr(1,3);
  
  $('#accordion__section-'+urlhash).attr('open', '');

  // Initialize via jquery.details.min.js

  $('details').details();

}); // Close $(document).ready(function()
