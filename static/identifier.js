var defaultTargetUrl;
var identifier;

function xmlEscape (s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* In the functions below, string and value arguments are assumed to
already be XML-escaped. */

function toEditForm (fieldName, s) {
  if ((fieldName == "_target" && s == "(this page)") ||
    (fieldName != "_target" && s == "(no value)")) {
    return "";
  } else {
    return s.replace(/< *[Bb][Rr] *\/?>/g, "\n");
  }
}

function toDisplayForm (fieldName, s) {
  if (s == "") {
    return (fieldName == "_target"? "(this page)" : "(no value)");
  } else {
    return s.replace(/\n/g, "<br/>");
  }
}

function openEditBox (div, fieldName) {
  clearMessages();
  var originalValue = toEditForm(fieldName, $.trim($(div).html()));
  var rows = originalValue.match(/\n/g);
  rows = (rows? rows.length+1 : 1);
  var textarea = $("<textarea rows='" + rows + "' cols='50'>" + originalValue +
    "</textarea>");
  var saveButton = $("<input type='submit' value='Save'/>");
  var cancelButton = $("<input type='submit' value='Cancel'/>");
  var table = $("<table class='editbox'>").append(
    $("<tr>").append(
      $("<td>").append(textarea))).append(
    $("<tr>").append(
      $("<td>").append(saveButton).append(cancelButton)));
  (fieldName == "_target"? $(div).parent() : $(div)).replaceWith(table);
  $(textarea).keydown(clearMessages);
  $(saveButton).click(function () {
    return saveEdit(table, fieldName);
  });
  $(cancelButton).click(function () {
    return cancelEdit(table, fieldName, originalValue);
  });
  $(textarea).focus();
}

function displayValue (table, fieldName, value) {
  var displayValue = toDisplayForm(fieldName, value);
  var div = $("<div class='value editable'>" + displayValue + "</div>");
  $(div).click(function (element) {
    return function () { openEditBox(element, fieldName); }
  }(div));
  if (fieldName == "_target") {
    var outerDiv = $("<div>");
    outerDiv.append(div);
    if (displayValue != "(this page)" && displayValue != "(no value)") {
      outerDiv.append($("<div class='visit'><a href='" +
        displayValue.replace(/\'/g, "&#39;") + "'>Visit now</a></div>"));
    }
    div = outerDiv;
  }
  $(table).replaceWith(div);
}

/* Extracted from the jQuery validation plugin,
<http://bassistance.de/jquery-plugins/jquery-plugin-validation/>. */
var urlRegex = /^(https?|ftp):\/\/(((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:)*@)?(((\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5]))|((([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.)+(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.?)(:\d*)?)(\/((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)+(\/(([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)*)*)?)?(\?((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)|[\uE000-\uF8FF]|\/|\?)*)?(\#((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)|\/|\?)*)?$/i;

function saveEdit (table, fieldName) {
  clearMessages();
  var value = $.trim($("textarea", table).val());
  var setValue = value;
  if (fieldName == "_target") {
    if (setValue == "") {
      setValue = defaultTargetUrl;
    } else {
      if (!urlRegex.test(setValue)) {
        addMessage("<span class='error'>Invalid URL.</span>");
        return false;
      }
    }
  }
  working(1);
  $.ajax({ type: "POST", cache: false, dataType: "text",
    data: { field: fieldName, value: setValue, profile: currentProfile },
    error: function () {
      working(-1);
      addMessage("<span class='error'>Internal server error.</span>");
    },
    success: function (response) {
      working(-1);
      if (response == "success") {
        displayValue(table, fieldName, xmlEscape(value));
        if (fieldName == "_target" && identifier.match(/^doi:/)) {
          $("#urlformnote").html(
            "(takes up to 30 minutes for link to be updated)");
        }
        addMessage("<span class='success'>Changes saved.</span>");
      } else {
        if (!response || response == "") response = "Internal server error.";
        addMessage("<span class='error'>" + xmlEscape(response) + "</span>");
      }
    }});
  return false;
}

function cancelEdit (table, fieldName, originalValue) {
  clearMessages();
  displayValue(table, fieldName, originalValue);
  return false;
}

var currentProfile;

function changeProfiles () {
  clearMessages();
  var newProfile = $("#profileselect").val();
  $(".profile_" + currentProfile).hide();
  $(".profile_" + newProfile).show();
  currentProfile = newProfile;
}

var moreDisplayed = false;

function showMoreOrLess () {
  clearMessages();
  if (moreDisplayed) {
    $("#less").show();
    $("#more").hide();
    $(".profile_internal").hide();
  } else {
    $("#less").hide();
    $("#more").show();
    $(".profile_internal").show();
  }
  moreDisplayed = !moreDisplayed;
  return false;
}

$(document).ready(function () {
  $("#profileselect").change(changeProfiles);
  $("#moreswitch").click(showMoreOrLess);
});
