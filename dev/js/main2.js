// ##### Main JavaScript ##### //

// Show/hide mobile menu via mobile menu icon:

$(document).ready(function(){
  // Change initial 'header__nav--selected' class to 'header__nav' (set to 'display: none') before toggling below
  $('#js-header__mobile-menu').attr('class', 'header__nav');
  $('#js-header__mobile-menu-icon').click(function(){
    $('#js-header__mobile-menu').toggleClass('header__nav header__nav--selected', 300, 'easeInOutCubic');
  });
});
