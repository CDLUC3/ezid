/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

/*
 * This will allow help boxes.
 * Uses bootstrap's popover.js
 *
 * Create a div to contain your help box like this, %value% represents a value you substitute:
 *
 * <div id="%div_id%" class="help_window">
 * 	 . . . contents . . .
 * </div>
 *
 * Create a link to open the help like so:
 * <a id="%div_id%" role="button" data-toggle="popover" data-trigger="hover"><img ...></a>
 *
 * Note the div_id around the contents and the div_id in the href for the link must match
 *
 */

$(document).ready(function() {
  // Hide all help content until elements are called upon (brought in via ezid-info-pages / popup_help.html)
  $('.help_window').hide();

  const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
  const popoverList = [...popoverTriggerList].map(popoverTriggerEl => {
    new bootstrap.Popover(popoverTriggerEl, {
        html: true,
        content: getPopContent(popoverTriggerEl.getAttribute("id"))
    });
  });

  // For each popover element, insert the corresponding content
  /*
  $('[data-toggle="popover"]').each(function() {
    const exampleEl = $(this)[ 0 ]; // make javascript instead of jQuery object);
    const popover = new bootstrap.Popover(exampleEl, {
      html: true,
      container: 'body',
      content: getPopContent(exampleEl.getAttribute("id"))
    });

    // This prevents page from scrolling to top when you click
    exampleEl.onclick = function(e) {e.popover(); return true; }
  });
   */


  function getPopContent(target) {
    return $("#" + target + "_content").html();
  };

  // User able to dismiss/close help window by hitting escape key
  $(document).keyup(function (e) {
    if (e.which === 27) {
      $('[data-toggle="popover"]').each(function () {
        $(this).popover('hide');
      });
    }
  });
  // ... and by clicking outside popover
  $('body').on('click', function (e) {
    $('[data-toggle="popover"]').each(function () {
      //the 'is' for buttons that trigger popups
      //the 'has' for icons within a button that triggers a popup
      if (!$(this).is(e.target) && $(this).has(e.target).length === 0 && $('.popover').has(e.target).length === 0) {
        $(this).popover('hide');
      }
    });
  });

  // Record a Google Analytics event when user clicks "Tooltip" Bootstrap Popover
  // $('.help_window').on('show.bs.popover', function () {
  $('.button__icon-help').on('click', function () {
    MATOMO_EVENT_LIB.init("Documentation Open Tooltip");
    MATOMO_EVENT_LIB.record_matomo_event();
  });
});
