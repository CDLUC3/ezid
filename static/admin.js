var sectionIsOpen = new Array();

function openOrCloseSection (evt) {
  clearMessages();
  var section = "section_" + evt.target.id.substr(7); /* strip off "switch_" */
  if (section in sectionIsOpen && sectionIsOpen[section]) {
    $("#" + section).css("display", "none");
    sectionIsOpen[section] = false;
  } else {
    $("#" + section).css("display", "block");
    $("#" + section + " .firsttext").focus();
    sectionIsOpen[section] = true;
  }
  return false;
}

$(document).ready(function () {
  $(".switch").click(openOrCloseSection);
  $("#message").keypress(clearMessages);
});
