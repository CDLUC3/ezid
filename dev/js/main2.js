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
    // Also handle labels with different DOM to accomodate help icon
    $(this).siblings('.fcontrol__label-wrapper-stacked').children('.fcontrol__text-label-stacked').addClass('fcontrol__label-required');
  });

  $('.fcontrol__text-field-inline[required]').map(function() {
    $(this).siblings('.fcontrol__text-label-inline').addClass('fcontrol__label-required');
  });

  $('.fcontrol__select--fullwidth[required]').map(function() {
    $(this).siblings('.fcontrol__select-label-inline').addClass('fcontrol__label-required');
  });

  // ***** Modal Login ***** //

  // Toggle open and closed from login button

  $('#js-header__loginout-button').click(function(){
    $('#js-login-modal').fadeToggle(200);
  });

  $('#js-login-modal').on('shown', function () {
    $("#js-login-modal #username").focus();
  });

  // Close when close icon is clicked

  $('#js-login-modal__close').click(function(){
    $('#js-login-modal').fadeToggle(200);
  });

  // Close when form is submitted

  $('#js-login-modal__form').submit(function(){
    $('#js-login-modal').fadeToggle(200);
  });

  // ***** Loading Indicator ***** //

  $('.search__action').click(function(){
    setTimeout(function() { loadingIndicator(); }, 4000);
  });

}); // Close $(document).ready(function()

// ***** Loading Indicator ***** //

var LoadingImage = "/static/images/loading_100x100.gif", loadingTag = "<div id=\"LoadingDivLayer\">";
loadingTag += "<div class=\"loading__container\" role=\"document\">";
loadingTag += "<img class=\"loading__image\" src=\"" + LoadingImage + "\" alt=\"Loading...\" />";
loadingTag += "<div class=\"loading__text\">Loading Results ...</div>";
loadingTag += "</div></div>";

function loadingIndicator(){
  if (document.getElementById("LoadingDivLayer") === null) {
    $("body").prepend(loadingTag);
    $("#LoadingDivLayer").fadeIn(350);
  }
}


// ***** Close Learn menu when user clicks somewhere else ***** //

$(document).click(function(event) { 
  if(!$(event.target).closest('#header__nav-details-learn').length) {
    if($('#header__nav-details-learn').attr("open")) {
      $("#header__nav-details-learn").attr("open", false);
    }
  }        
});

// ***** Somehow the Learn menu is cached in an open state when user clicks back button
//      from the Learn page (BFCache aka back-forward cache) so close it on pageshow as well   ****** //

window.onpageshow = function(event) {
  $("#header__nav-details-learn").attr("open", false);
};

