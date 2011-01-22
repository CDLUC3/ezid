function xmlEscape (s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/'/g, "&apos;");
}

var newGroupOpen = false;

function newGroup () {
  clearMessages();
  if (newGroupOpen) {
    $("#ng_entry").flushCache();
    $("#ng_section").hide();
    $("#ng_open").hide();
    $("#ng_close").show();
  } else {
    $("#ng_close").hide();
    $("#ng_open").show();
    $("#ng_section").show();
    $("#ng_entry").val("Loading entries...");
    $("#ng_gid").val("");
    $("#ng_agreement").attr("checked", false);
    $("#ng_shoulderlist").val(defaultShoulders);
    $.ajax({ url: "/ezid/admin/entries", dataType: "json", cache: false,
      error: function () {
        $("#ng_entry").val("Loading entries... failed");
        addMessage("<span class='error'>Internal server error.</span>");
      },
      success: function (data) {
        if ($.isArray(data)) {
          $("#ng_entry").autocomplete(data, { matchContains: true });
          $("#ng_entry").val("Type any substring of the entry's DN");
          $("#ng_entry").select();
        } else {
          $("#ng_entry").val("Loading entries... failed");
          if (typeof(data) != "string" || data == "") {
            data = "Internal server error.";
          }
          addMessage("<span class='error'>" + xmlEscape(data) + "</span>");
        }
      }
    });
  }
  newGroupOpen = !newGroupOpen;
  return false;
}

var manageGroupOpen = false;
var groups = null;

function setGroup (dn) {
  for (var i = 0; i < groups.length; ++i) {
    if (groups[i].dn == dn) {
      $("#mg_entry").html(xmlEscape(groups[i].dn));
      $("#mg_arkid").html("<a href='/ezid/id/" +
        xmlEscape(encodeURI(groups[i].arkId)) + "'>" +
        xmlEscape(groups[i].arkId) + "</a>");
      $("#mg_users").html($.map(groups[i].users,
        function (u) { return xmlEscape(u.uid); }).join(", "));
      $("#mg_agreement").attr("checked", groups[i].agreementOnFile);
      $("#mg_shoulderlist").val(groups[i].shoulderList);
    }
  }
}

function manageGroup () {
  clearMessages();
  if (manageGroupOpen) {
    groups = null;
    $("#mg_section").hide();
    $("#mg_open").hide();
    $("#mg_close").show();
  } else {
    $("#mg_close").hide();
    $("#mg_open").show();
    $("#mg_section").show();
    $("#mg_select").html(
      "<option selected='selected'>Loading groups...</option>");
    $("#mg_entry").empty();
    $("#mg_arkid").empty();
    $("#mg_users").empty();
    $("#mg_agreement").attr("checked", false);
    $("#mg_shoulderlist").val("");
    $.ajax({ url: "/ezid/admin/groups", dataType: "json", cache: false,
      error: function () {
        $("#mg_select").html(
          "<option selected='selected'>Loading groups... failed</option>");
        addMessage("<span class='error'>Internal server error.</span>");
      },
      success: function (data) {
        if ($.isArray(data)) {
          groups = data;
          var s = $("#mg_select");
          s.empty();
          for (var i = 0; i < data.length; ++i) {
            var o = "<option value='" + xmlEscape(data[i].dn) + "'";
            if (i == 0) o += " selected='selected'";
            o += ">" + xmlEscape(data[i].gid) + "</option>";
            s.append(o);
          }
          setGroup(data[0].dn);
        } else {
          $("#mg_select").html(
            "<option selected='selected'>Loading groups... failed</option>");
          if (typeof(data) != "string" || data == "") {
            data = "Internal server error.";
          }
          addMessage("<span class='error'>" + xmlEscape(data) + "</span>");
        }
      }
    });
  }
  manageGroupOpen = !manageGroupOpen;
  return false;
}

function selectGroup () {
  clearMessages();
  setGroup($("#mg_select").val());
}

var newUserOpen = false;
var groups2 = null;

function newUser () {
  clearMessages();
  if (newUserOpen) {
    groups2 = null;
    $("#nu_entry").flushCache();
    $("#nu_section").hide();
    $("#nu_open").hide();
    $("#nu_close").show();
  } else {
    $("#nu_close").hide();
    $("#nu_open").show();
    $("#nu_section").show();
    $("#nu_entry").val("Loading entries...");
    $("#nu_select").html(
      "<option selected='selected'>Loading groups...</option>");
    $.ajax({ url: "/ezid/admin/entries?usersOnly=true", dataType: "json",
      cache: false,
      error: function () {
        $("#nu_entry").val("Loading entries... failed");
        addMessage("<span class='error'>Internal server error.</span>");
      },
      success: function (data) {
        if ($.isArray(data)) {
          $("#nu_entry").autocomplete(data, { matchContains: true });
          $("#nu_entry").val("Type any substring of the entry's DN");
          $("#nu_entry").select();
        } else {
          $("#nu_entry").val("Loading entries... failed");
          if (typeof(data) != "string" || data == "") {
            data = "Internal server error.";
          }
          addMessage("<span class='error'>" + xmlEscape(data) + "</span>");
        }
      }
    });
    $.ajax({ url: "/ezid/admin/groups", dataType: "json", cache: false,
      error: function () {
        $("#nu_select").html(
          "<option selected='selected'>Loading groups... failed</option>");
        addMessage("<span class='error'>Internal server error.</span>");
      },
      success: function (data) {
        if ($.isArray(data)) {
          groups2 = data;
          var s = $("#nu_select");
          s.empty();
          for (var i = 0; i < data.length; ++i) {
            var o = "<option value='" + xmlEscape(data[i].dn) + "'";
            if (i == 0) o += " selected='selected'";
            o += ">" + xmlEscape(data[i].gid) + "</option>";
            s.append(o);
          }
        } else {
          $("#nu_select").html(
            "<option selected='selected'>Loading groups... failed</option>");
          if (typeof(data) != "string" || data == "") {
            data = "Internal server error.";
          }
          addMessage("<span class='error'>" + xmlEscape(data) + "</span>");
        }
      }
    });
  }
  newUserOpen = !newUserOpen;
  return false;
}

var manageUserOpen = false;
var users = null;

function setUser (dn) {
  for (var i = 0; i < users.length; ++i) {
    if (users[i].dn == dn) {
      $("#mu_entry").html(xmlEscape(users[i].dn));
      $("#mu_arkid").html("<a href='/ezid/id/" +
        xmlEscape(encodeURI(users[i].arkId)) + "'>" +
        xmlEscape(users[i].arkId) + "</a>");
      $("#mu_gid").html(xmlEscape(users[i].groupGid));
    }
  }
}

function manageUser () {
  clearMessages();
  if (manageUserOpen) {
    users = null;
    $("#mu_section").hide();
    $("#mu_open").hide();
    $("#mu_close").show();
  } else {
    $("#mu_close").hide();
    $("#mu_open").show();
    $("#mu_section").show();
    $("#mu_select").html(
      "<option selected='selected'>Loading users...</option>");
    $("#mu_entry").empty();
    $("#mu_arkid").empty();
    $("#mu_gid").empty();
    $.ajax({ url: "/ezid/admin/users", dataType: "json", cache: false,
      error: function () {
        $("#mu_select").html(
          "<option selected='selected'>Loading users... failed</option>");
        addMessage("<span class='error'>Internal server error.</span>");
      },
      success: function (data) {
        if ($.isArray(data)) {
          users = data;
          var s = $("#mu_select");
          s.empty();
          for (var i = 0; i < data.length; ++i) {
            var o = "<option value='" + xmlEscape(data[i].dn) + "'";
            if (i == 0) o += " selected='selected'";
            o += ">" + xmlEscape(data[i].uid) + "</option>";
            s.append(o);
          }
          setUser(data[0].dn);
        } else {
          $("#mu_select").html(
            "<option selected='selected'>Loading users... failed</option>");
          if (typeof(data) != "string" || data == "") {
            data = "Internal server error.";
          }
          addMessage("<span class='error'>" + xmlEscape(data) + "</span>");
        }
      }
    });
  }
  manageUserOpen = !manageUserOpen;
  return false;
}

function selectUser () {
  clearMessages();
  setUser($("#mu_select").val());
}

var setAlertOpen = false;

function setAlert () {
  clearMessages();
  if (setAlertOpen) {
    $("#sa_section").hide();
    $("#sa_open").hide();
    $("#sa_close").show();
  } else {
    $("#sa_close").hide();
    $("#sa_open").show();
    $("#sa_section").show();
    $("#sa_message").focus();
  }
  setAlertOpen = !setAlertOpen;
  return false;
}

var reloadOpen = false;

function reload () {
  clearMessages();
  if (reloadOpen) {
    $("#rl_section").hide();
    $("#rl_open").hide();
    $("#rl_close").show();
  } else {
    $("#rl_close").hide();
    $("#rl_open").show();
    $("#rl_section").show();
  }
  reloadOpen = !reloadOpen;
  return false;
}

$(document).ready(function () {
  $("input").keydown(clearMessages);
  $("#ng_switch").click(newGroup);
  $("#ng_agreement").change(clearMessages);
  $("#mg_switch").click(manageGroup);
  $("#mg_select").change(selectGroup);
  $("#mg_agreement").change(clearMessages);
  $("#nu_switch").click(newUser);
  $("#nu_select").change(clearMessages);
  $("#mu_switch").click(manageUser);
  $("#mu_select").change(selectUser);
  $("#sa_switch").click(setAlert);
  $("#rl_switch").click(reload);
});
