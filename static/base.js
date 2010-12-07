function viewRecentIdentifier () {
  if ($("#history").attr("selectedIndex") == 0) return;
  var url = $("#history").val();
  $("#history").attr("selectedIndex", 0);
  if (url == "clear") {
    clearMessages();
    $.ajax({ url: "/ezid/clearhistory", dataType: "text", cache: false,
      error: function () {
        addMessage("<span class='error'>Internal server error.</span>");
      },
      success: function (data) {
        if (data == "success") {
          $("#history .historyentry").remove();
          addMessage("<span class='success'>History cleared.</span>");
        } else {
          addMessage("<span class='error'>Internal server error.</span>");
        }
      }});
  } else {
    location.href = url;
  }
}

$(document).ready(function () {
  $("#history").change(viewRecentIdentifier);
});

var numAjaxThreads = 0;

function working (delta) {
  numAjaxThreads += delta;
  var s = "";
  for (var i = 0; i < numAjaxThreads; ++i) {
    s += "<span class='info'>Working...</span> "
  }
  $("#workings").html(s);
}

var areMessages;

function clearMessages () {
  if (areMessages) $("#messages").html("&nbsp;");
  areMessages = false;
}

function addMessage (m) {
  if (areMessages) {
    $("#messages").html($("#messages").html() + " " + m);
  } else {
    $("#messages").html(m);
  }
  areMessages = true;
}

window.onpageshow = function (event) {
  if (event.persisted) clearMessages();
};
