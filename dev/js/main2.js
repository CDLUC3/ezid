// ##### Main JavaScript ##### //

$(document).ready(function(){
  
  // ***** Show/hide mobile menu via mobile menu icon ***** //

  // Before toggling menu, change initial 'header__nav--selected' class to 'header__nav' and add aria-expanded attribute:
  $('#js-header__mobile-menu').attr({'class': 'header__nav', 'aria-expanded': 'false'});

  // Toggle classes and attribute:
  $('#js-header__mobile-menu-icon').click(function(){
    
    $('#js-header__mobile-menu').toggleClass('header__nav header__nav--selected', 300, 'easeInOutCubic');

    if($('#js-header__mobile-menu').attr('aria-expanded') == 'false') {
      $('#js-header__mobile-menu').attr('aria-expanded', 'true');
    } else {
      $('#js-header__mobile-menu').attr('aria-expanded', 'false');
    }

  });
});
