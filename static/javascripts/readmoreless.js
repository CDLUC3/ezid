// Read More Hide/Show Toggle

// Hide the extra content initially, using JS so that if JS is disabled, no problemo:
$('.read-more-content').addClass('hide')
$('.read-more-show, .read-more-hide').removeClass('hide')

// Set up the toggle effect:
$('.read-more-show').on('click', function(e) {
  $('.read-more-content').removeClass('hide');
  $(this).addClass('hide');
  e.preventDefault();
});

$('.read-more-hide').on('click', function(e) {
  $('.read-more-content').addClass('hide');
  $('.read-more-show').removeClass('hide'); // Hide only the preceding "Read More"
  e.preventDefault();
});
