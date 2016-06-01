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

  // For each popover element, insert the corresponding content
  $('[data-toggle="popover"]').each(function() {
    var $pElem= $(this);
    $pElem.popover(
        {
          html: true,
          content: getPopContent($pElem.attr("id"))
        }
    );
  });
  function getPopContent(target) {
    return $("#" + target + "_content").html();
  };

  // User able to dismiss/close help window by clicking outside
  $('body').on('click', function (e) {
    $('[data-toggle="popover"]').each(function () {
      //the 'is' for buttons that trigger popups
      //the 'has' for icons within a button that triggers a popup
      if (!$(this).is(e.target) && $(this).has(e.target).length === 0 && $('.popover').has(e.target).length === 0) {
        $(this).popover('hide');
      }
  });
});
});
