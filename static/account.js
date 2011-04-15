function xmlEscape (s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function updateAccountProfile () {
  clearMessages();
  working(1);
  $.ajax({ type: "POST", cache: false, dataType: "text",
    data: { form: "profile", ezidCoOwners: $("#ezidCoOwners").val() },
    error: function () {
      working(-1);
      addMessage("<span class='error'>Internal server error.</span>");
    },
    success: function (response) {
      working(-1);
      if (response == "success") {
        addMessage("<span class='success'>Account profile updated.</span>");
      } else {
        if (!response || response == "") response = "Internal server error.";
        addMessage("<span class='error'>" + xmlEscape(response) + "</span>");
      }
    }
  });
  return false;
}

/* Extracted from the jQuery validation plugin,
<http://bassistance.de/jquery-plugins/jquery-plugin-validation/>. */
var emailRegex = /^((([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+(\.([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+)*)|((\x22)((((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(([\x01-\x08\x0b\x0c\x0e-\x1f\x7f]|\x21|[\x23-\x5b]|[\x5d-\x7e]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(\\([\x01-\x09\x0b\x0c\x0d-\x7f]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]))))*(((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(\x22)))@((([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.)+(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.?$/i;

function updateContactInfo () {
  clearMessages();
  if (!emailRegex.test($("#mail").val())) {
    addMessage("<span class='error'>Invalid email address.</span>");
    return false;
  }
  working(1);
  $.ajax({ type: "POST", cache: false, dataType: "text",
    data: { form: "contact", givenName: $("#givenName").val(),
      sn: $("#sn").val(), mail: $("#mail").val(),
      telephoneNumber: $("#telephoneNumber").val() },
    error: function () {
      working(-1);
      addMessage("<span class='error'>Internal server error.</span>");
    },
    success: function (response) {
      working(-1);
      if (response == "success") {
        addMessage("<span class='success'>Contact information " +
          "updated.</span>");
      } else {
        if (!response || response == "") response = "Internal server error.";
        addMessage("<span class='error'>" + xmlEscape(response) + "</span>");
      }
    }
  });
  return false;
}

function changePassword () {
  clearMessages();
  if ($("#pwnew").val() != $("#pwconfirm").val()) {
    addMessage("<span class='error'>New password and confirmation do not " +
      "match.</span>");
    return false;
  }
  working(1);
  $.ajax({ type: "POST", cache: false, dataType: "text",
    data: { form: "password", pwcurrent: $("#pwcurrent").val(),
      pwnew: $("#pwnew").val() },
    error: function () {
      working(-1);
      addMessage("<span class='error'>Internal server error.</span>");
    },
    success: function (response) {
      working(-1);
      if (response == "success") {
        addMessage("<span class='success'>Password changed.</span>");
        $("#pwcurrent").blur().val("");
        $("#pwnew").blur().val("");
        $("#pwconfirm").blur().val("");
      } else {
        if (!response || response == "") response = "Internal server error.";
        addMessage("<span class='error'>" + xmlEscape(response) + "</span>");
      }
    }
  });
  return false;
}

$(document).ready(function () {
  $("input[type='text']").keydown(clearMessages);
  $("input[type='password']").keydown(clearMessages);
  $("#profileform").submit(updateAccountProfile);
  $("#contactform").submit(updateContactInfo);
  $("#passwordform").submit(changePassword);
});
