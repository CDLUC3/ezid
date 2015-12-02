// ##### Main JavaScript ##### //

$(document).ready(function(){
  
  // ***** Show/hide mobile menu via mobile menu icon ***** //

  // Before toggling menu, change default header menu class to non-selected state and change default aria attributes:

  $('#js-header__mobile-menu').attr('class', 'header__nav');
  $('#js-header__mobile-menu').attr('aria-expanded', 'false');
  $('#js-header__mobile-menu-icon').attr('aria-pressed', 'false');

  // Toggle classes and attributes:
  $('#js-header__mobile-menu-icon').click(function(){
    
    $('#js-header__mobile-menu').toggleClass('header__nav header__nav--selected', 300, 'easeInOutCubic');

    if($('#js-header__mobile-menu').attr('aria-expanded') == 'false') {
      $('#js-header__mobile-menu').attr('aria-expanded', 'true');
    } else {
      $('#js-header__mobile-menu').attr('aria-expanded', 'false');
    }

    if($('#js-header__mobile-menu-icon').attr('aria-pressed') == 'false') {
      $('#js-header__mobile-menu-icon').attr('aria-pressed', 'true');
    } else {
      $('#js-header__mobile-menu-icon').attr('aria-pressed', 'false');
    }

  });
});
