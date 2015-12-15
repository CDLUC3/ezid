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

  $('.accordion__section').click(function(){

    // If an accordion section is clicked, close all the other ones if they are open and set their aria-expanded attributes to false:
    if ($('.accordion__section').not(this).attr('open', '')) {
      $('.accordion__section').not(this).removeAttr('open');
      $('.accordion__section').attr('aria-expanded', 'false');
    }

    // If an accordion section is clicked, set its aria-expanded attribute to true:
    $(this).attr('aria-expanded', 'true');

    // If an opened accordion section is clicked closed, set it's aria-expanded attribute to false:
    if ($(this).attr('open')) {
      $(this).attr('aria-expanded', 'false');
    }

  });

}); // Close $(document).ready(function()
