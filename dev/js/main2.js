// ##### Main JavaScript ##### //

$(document).ready(function(){
  
  // ***** Show/hide mobile menu via mobile menu icon ***** //

  // Before toggling menu, change default header menu class to non-selected state and change default aria attribute:

  // According to ChatGPT using aria-hidden for visual appearance isn't recommended and items should not be hidden from
  // screen readers. Instead, use aria-expanded to indicate the state of the menu.
  $('#js-header__nav').attr('class', 'header__nav');
  $('#js-header__nav').attr('aria-expanded', 'false');

  // Toggle classes and attributes:
  $('#js-header__nav-button').click(function(){
    
    $('#js-header__nav').toggleClass('header__nav header__nav--selected', 300, 'easeInOutCubic');

    if($('#js-header__nav').attr('aria-expanded') == 'false') {
      $('#js-header__nav').attr('aria-expanded', 'true');
    } else {
      $('#js-header__nav').attr('aria-expanded', 'false');
    }

  });

  // ***** Accordion ***** //

  // Pre-open an accordion section by retrieving the referring URL hash (up to 2 digits), removing the hash tag, and adding the hash value to the jQuery selector:

  var urlhash = window.location.hash.substr(1,3);
  
  $('#accordion__section-'+urlhash).attr('open', '');

  $('.accordion__title').click(function(){

    // If an accordion title is clicked, close all the other sections if they are open and set their aria-expanded attributes to false:
    if ($(this).parent().siblings().attr('open', '')) {
      $(this).parent().siblings().removeAttr('open');
      $('.accordion__section').attr('aria-expanded', 'false');
    }

    // If an accordion title is clicked, set its section aria-expanded attribute to true:
    if ($(this).parent().attr('aria-expanded') == 'false') {
      $(this).parent().attr('aria-expanded', 'true');
    }

  });

  // ***** HTML Form Validation ***** //

  // If 'required' attribute exists on a text input, add 'required' class to its label:

  $('.fcontrol__text-field-stacked[required]').map(function() {
    $(this).siblings('.fcontrol__text-label-stacked').addClass('fcontrol__label-required');
  });

  $('.fcontrol__text-field-inline[required]').map(function() {
    $(this).siblings('.fcontrol__text-label-inline').addClass('fcontrol__label-required');
  });

  // ***** Modal Login ***** //

  // Toggle open and closed from login button

  $('#js-header__loginout-button').click(function(){
    if ($('#js-login-modal').attr('aria-hidden') == 'true') {
      $('#js-login-modal').attr('aria-hidden', 'false');
    }else {
      $('#js-login-modal').attr('aria-hidden', 'true');
    }
    $('#js-login-modal').fadeToggle(200);
  });

  // Close when close icon is clicked

  $('#js-login-modal__close').click(function(){
    $('#js-login-modal').attr('aria-hidden', 'true');
    $('#js-login-modal').fadeToggle(200);
  });

  // Close when form is submitted

  $('#js-login-modal__form').submit(function(){
    $('#js-login-modal').attr('aria-hidden', 'true');
    $('#js-login-modal').fadeToggle(200);
  });

}); // Close $(document).ready(function()
