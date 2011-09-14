function xmlEscape (s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/'/g, "&apos;");
}

var newGroupOpen = false;

function newGroup () {
  clearMessages();
  if (newGroupOpen) {
    $("#ng_section").hide();
    $("#ng_open").hide();
    $("#ng_close").show();
  } else {
    $("#ng_close").hide();
    $("#ng_open").show();
    $("#ng_section").show();
    $("#ng_gid").val("");
    $("#ng_gid").select();
  }
  newGroupOpen = !newGroupOpen;
  return false;
}

function makeGroup () {
  clearMessages();
  working(1);
  $.ajax({ type: "POST", dataType: "text", cache: false,
    data: { operation: "make_group", gid: $("#ng_gid").val() },
    error: function () {
      working(-1);
      addMessage("<span class='error'>Internal server error.</span>");
    },
    success: function (response) {
      working(-1);
      if (response.substr(0, 9) == "success: ") {
        if (newGroupOpen) newGroup();
        if (manageGroupOpen) manageGroup(null);
        manageGroup(response.substr(9));
        addMessage("<span class='success'>New group created.</span>");
      } else {
        if (typeof(response) != "string" || response == "") {
          response = "Internal server error.";
        }
        addMessage("<span class='error'>" + xmlEscape(response) + "</span>");
      }
    }
  });
  return false;
}

var manageGroupOpen = false;
var groups = null;

function setGroup (dn) {
  for (var i = 0; i < groups.length; ++i) {
    if (groups[i].dn == dn) {
      $("#mg_arkid").html("<a href='/ezid/id/" +
        xmlEscape(encodeURI(groups[i].arkId)) + "'>" +
        xmlEscape(groups[i].arkId) + "</a>");
      if (groups[i].users.length > 0) {
        $("#mg_users").html($.map(groups[i].users,
          function (u) { return xmlEscape(u.uid); }).join(", "));
      } else {
        $("#mg_users").html("(none)");
      }
      $("#mg_description").val(groups[i].description);
      $("#mg_agreement").attr("checked", groups[i].agreementOnFile);
      var s = $("#mg_shoulders");
      s.empty();
      if (groups[i].shoulderList[0] == "*") {
        /* Special case for the admin user. */
        s.append("<option value='*' selected='selected'>*</option>");
      }
      for (var j = 0; j < shoulders.length; ++j) {
        if ($.inArray(shoulders[j].label, groups[i].shoulderList) >= 0) {
          var o = "<option value='" + xmlEscape(shoulders[j].label) +
            "' selected='selected'>" + xmlEscape(shoulders[j].name);
          if (shoulders[j].name != "NONE") {
            o += " (" + xmlEscape(shoulders[j].prefix) + ")";
          }
          o += "</option>";
          s.append(o);
        }
      }
      s.append("<option value='-'></option>");
      for (var j = 0; j < shoulders.length; ++j) {
        if ($.inArray(shoulders[j].label, groups[i].shoulderList) < 0) {
          var o = "<option value='" + xmlEscape(shoulders[j].label) +
            "'>" + xmlEscape(shoulders[j].name);
          if (shoulders[j].name != "NONE") {
            o += " (" + xmlEscape(shoulders[j].prefix) + ")";
          }
          o += "</option>";
          s.append(o);
        }
      }
      break;
    }
  }
}

function manageGroup (newlyCreatedGroup) {
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
    $("#mg_arkid").empty();
    $("#mg_users").empty();
    $("#mg_description").val("");
    $("#mg_agreement").attr("checked", false);
    $("#mg_shoulders").empty();
    $.ajax({ url: "/ezid/admin/groups", dataType: "json", cache: false,
      error: function () {
        $("#mg_select").html(
          "<option selected='selected'>Loading groups... failed</option>");
        addMessage("<span class='error'>Internal server error.</span>");
      },
      success: function (selectedGroup) {
        return function (data) {
          if ($.isArray(data)) {
            groups = data;
            var s = $("#mg_select");
            s.empty();
            var j;
            for (var i = 0; i < data.length; ++i) {
              data[i].shoulderList = data[i].shoulderList.split(",");
              var o = "<option value='" + xmlEscape(data[i].dn) + "'";
              if ((selectedGroup != null && data[i].dn == selectedGroup) ||
                (selectedGroup == null && i == 0)) {
                o += " selected='selected'";
                j = i;
              }
              o += ">" + xmlEscape(data[i].gid) + "</option>";
              s.append(o);
            }
            setGroup(data[j].dn);
          } else {
            $("#mg_select").html(
              "<option selected='selected'>Loading groups... failed</option>");
            if (typeof(data) != "string" || data == "") {
              data = "Internal server error.";
            }
            addMessage("<span class='error'>" + xmlEscape(data) + "</span>");
          }
        }
      }(newlyCreatedGroup)
    });
  }
  manageGroupOpen = !manageGroupOpen;
  return false;
}

function selectGroup () {
  clearMessages();
  setGroup($("#mg_select").val());
}

function updateGroup () {
  clearMessages();
  var s = $("#mg_shoulders");
  var v = s.val();
  if (v == null) v = [];
  var i = $.inArray("-", v);
  if (i >= 0) {
    v = v.slice(0);
    v.splice(i, 1);
  }
  if (v.length == 0) {
    addMessage("<span class='error'>At least one shoulder must be " +
      "selected.</span>");
    return false;
  }
  if (s.children()[0].value == "*") {
    /* Special case for the admin user. */
    if (v.length != 1 || v[0] != "*") {
      addMessage("<span class='error'>The admin group's shoulders cannot be " +
        "modified.</span>");
      return false;
    }
  }
  if ($.inArray("NONE", v) >= 0 && v.length > 1) {
    addMessage("<span class='error'>Ambiguous shoulder choice.</span>");
    return false;
  }
  working(1);
  $.ajax({ type: "POST", dataType: "text", cache: false,
    data: { operation: "update_group", dn: $("#mg_select").val(),
      description: $("#mg_description").val(),
      agreementOnFile: $("#mg_agreement").attr("checked"),
      shoulderList: v.join(",") },
    error: function () {
      working(-1);
      addMessage("<span class='error'>Internal server error.</span>");
    },
    success: function (response) {
      working(-1);
      if (response == "success") {
        /* A successful update will not cause our internal data
        structures (namely, the 'groups' array) to be updated.  For
        now, to be safe, we simply close the section to force a reload
        when the user re-opens it. */
        if (manageGroupOpen) manageGroup(null);
        addMessage("<span class='success'>Group updated.</span>");
      } else {
        if (typeof(response) != "string" || response == "") {
          response = "Internal server error.";
        }
        addMessage("<span class='error'>" + xmlEscape(response) + "</span>");
      }
    }
  });
  return false;
}

var newUserOpen = false;
var groups2 = null;

function newUser () {
  clearMessages();
  if (newUserOpen) {
    groups2 = null;
    $("#nu_section").hide();
    $("#nu_open").hide();
    $("#nu_close").show();
  } else {
    $("#nu_close").hide();
    $("#nu_open").show();
    $("#nu_section").show();
    $("#nu_uid").val("");
    $("#nu_userselect").html(
      "<option selected='selected'>Loading LDAP users...</option>");
    $("#nu_groupselect").html(
      "<option selected='selected'>Loading groups...</option>");
    $("#nu_uid").select();
    $.ajax({ url: "/ezid/admin/entries?usersOnly=true&nonEzidUsersOnly=true",
      dataType: "json", cache: false,
      error: function () {
        $("#nu_userselect").html(
          "<option selected='selected'>Loading LDAP users... failed</option>");
        addMessage("<span class='error'>Internal server error.</span>");
      },
      success: function (data) {
        if ($.isArray(data)) {
          var s = $("#nu_userselect");
          s.empty();
          s.append("<option value='' selected='selected'></option>");
          for (var i = 0; i < data.length; ++i) {
            var o = "<option value='" + xmlEscape(data[i].dn) + "'>" +
              xmlEscape(data[i].uid) + "</option>";
            s.append(o);
          }
        } else {
          $("#nu_userselect").html(
            "<option selected='selected'>Loading LDAP users... " +
            "failed</option>");
          if (typeof(data) != "string" || data == "") {
            data = "Internal server error.";
          }
          addMessage("<span class='error'>" + xmlEscape(data) + "</span>");
        }
      }
    });
    $.ajax({ url: "/ezid/admin/groups", dataType: "json", cache: false,
      error: function () {
        $("#nu_groupselect").html(
          "<option selected='selected'>Loading groups... failed</option>");
        addMessage("<span class='error'>Internal server error.</span>");
      },
      success: function (data) {
        if ($.isArray(data)) {
          groups2 = data;
          var s = $("#nu_groupselect");
          s.empty();
          for (var i = 0; i < data.length; ++i) {
            var o = "<option value='" + xmlEscape(data[i].dn) + "'";
            if (i == 0) o += " selected='selected'";
            o += ">" + xmlEscape(data[i].gid) + "</option>";
            s.append(o);
          }
        } else {
          $("#nu_groupselect").html(
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

function makeUser () {
  clearMessages();
  if ($.trim($("#nu_uid").val()) != "" && $("#nu_userselect").val() != "") {
    addMessage("<span class='error'>Ambiguous choice.</span>");
    return false;
  }
  working(1);
  $.ajax({ type: "POST", dataType: "text", cache: false,
    data: { operation: "make_user", uid: $("#nu_uid").val(),
      existingUserDn: $("#nu_userselect").val(),
      groupDn: $("#nu_groupselect").val() },
    error: function () {
      working(-1);
      addMessage("<span class='error'>Internal server error.</span>");
    },
    success: function (response) {
      working(-1);
      if (response.substr(0, 9) == "success: ") {
        if (newUserOpen) newUser();
        if (manageUserOpen) manageUser(null);
        manageUser(response.substr(9));
        addMessage("<span class='success'>New user created.</span>");
      } else {
        if (typeof(response) != "string" || response == "") {
          response = "Internal server error.";
        }
        addMessage("<span class='error'>" + xmlEscape(response) + "</span>");
      }
    }
  });
  return false;
}

var manageUserOpen = false;
var users = null;

function setUser (dn) {
  for (var i = 0; i < users.length; ++i) {
    if (users[i].dn == dn) {
      $("#mu_uid").val(users[i].uid);
      $("#mu_currentlyEnabled").val(users[i].currentlyEnabled);
      $("#mu_arkid").html("<a href='/ezid/id/" +
        xmlEscape(encodeURI(users[i].arkId)) + "'>" +
        xmlEscape(users[i].arkId) + "</a>");
      $("#mu_gid").html(xmlEscape(users[i].groupGid));
      $("#mu_givenName").val(users[i].givenName);
      $("#mu_sn").val(users[i].sn);
      $("#mu_mail").val(users[i].mail);
      $("#mu_telephoneNumber").val(users[i].telephoneNumber);
      $("#mu_description").val(users[i].description);
      $("#mu_ezidCoOwners").val(users[i].ezidCoOwners);
      $("#mu_enabled").attr("checked", users[i].currentlyEnabled == "true");
      $("#mu_userPassword").val("");
      break;
    }
  }
}

function manageUser (newlyCreatedUser) {
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
    $("#mu_uid").val("");
    $("#mu_currentlyEnabled").val("");
    $("#mu_arkid").empty();
    $("#mu_gid").empty();
    $("#mu_givenName").val("");
    $("#mu_sn").val("");
    $("#mu_mail").val("");
    $("#mu_telephoneNumber").val("");
    $("#mu_description").val("");
    $("#mu_ezidCoOwners").val("");
    $("#mu_enabled").attr("checked", false);
    $("#mu_userPassword").val("");
    $.ajax({ url: "/ezid/admin/users", dataType: "json", cache: false,
      error: function () {
        $("#mu_select").html(
          "<option selected='selected'>Loading users... failed</option>");
        addMessage("<span class='error'>Internal server error.</span>");
      },
      success: function (selectedUser) {
        return function (data) {
          if ($.isArray(data)) {
            users = data;
            var s = $("#mu_select");
            s.empty();
            var j;
            for (var i = 0; i < data.length; ++i) {
              var o = "<option value='" + xmlEscape(data[i].dn) + "'";
              if ((selectedUser != null && data[i].dn == selectedUser) ||
                (selectedUser == null && i == 0)) {
                o += " selected='selected'";
                j = i;
              }
              o += ">" + xmlEscape(data[i].uid) + "</option>";
              s.append(o);
            }
            setUser(data[j].dn);
          } else {
            $("#mu_select").html(
              "<option selected='selected'>Loading users... failed</option>");
            if (typeof(data) != "string" || data == "") {
              data = "Internal server error.";
            }
            addMessage("<span class='error'>" + xmlEscape(data) + "</span>");
          }
        }
      }(newlyCreatedUser)
    });
  }
  manageUserOpen = !manageUserOpen;
  return false;
}

function selectUser () {
  clearMessages();
  setUser($("#mu_select").val());
}

/* Extracted from the jQuery validation plugin,
<http://bassistance.de/jquery-plugins/jquery-plugin-validation/>. */
var emailRegex = /^((([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+(\.([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+)*)|((\x22)((((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(([\x01-\x08\x0b\x0c\x0e-\x1f\x7f]|\x21|[\x23-\x5b]|[\x5d-\x7e]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(\\([\x01-\x09\x0b\x0c\x0d-\x7f]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]))))*(((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(\x22)))@((([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.)+(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.?$/i;

function updateUser () {
  clearMessages();
  if (!emailRegex.test($("#mu_mail").val())) {
    addMessage("<span class='error'>Invalid email address.</span>");
    return false;
  }
  var disable = false;
  if ($("#mu_enabled").attr("checked") !=
    ($("#mu_currentlyEnabled").val() == "true")) {
    if ($("#mu_enabled").attr("checked")) {
      if ($.trim($("#mu_userPassword").val()) == "") {
        addMessage("<span class='error'>New password required.</span>");
        return false;
      }
    } else {
      if ($.trim($("#mu_userPassword").val()) != "") {
        addMessage("<span class='error'>New password not allowed.</span>");
        return false;
      }
      disable = true;
    }
  }
  working(1);
  $.ajax({ type: "POST", dataType: "text", cache: false,
    data: { operation: "update_user", uid: $("#mu_uid").val(),
      givenName: $("#mu_givenName").val(), sn: $("#mu_sn").val(),
      mail: $("#mu_mail").val(),
      telephoneNumber: $("#mu_telephoneNumber").val(),
      description: $("#mu_description").val(),
      ezidCoOwners: $("#mu_ezidCoOwners").val(),
      disable: disable,
      userPassword: $("#mu_userPassword").val() },
    error: function () {
      working(-1);
      addMessage("<span class='error'>Internal server error.</span>");
    },
    success: function (response) {
      working(-1);
      if (response == "success") {
        /* A successful update will not cause our internal data
        structures (namely, the 'users' array) to be updated.  For
        now, to be safe, we simply close the section to force a reload
        when the user re-opens it. */
        if (manageUserOpen) manageUser(null);
        addMessage("<span class='success'>User updated.</span>");
      } else {
        if (typeof(response) != "string" || response == "") {
          response = "Internal server error.";
        }
        addMessage("<span class='error'>" + xmlEscape(response) + "</span>");
      }
    }
  });
  return false;
}

var systemStatusOpen = false;

function systemStatus () {
  clearMessages();
  if (systemStatusOpen) {
    $("#ss_section").hide();
    $("#ss_open").hide();
    $("#ss_close").show();
  } else {
    $("#ss_close").hide();
    $("#ss_open").show();
    $("#ss_section").show();
    $("#sstable").empty();
    $.ajax({ url: "/ezid/admin/systemstatus", dataType: "json", cache: false,
      error: function () {
        addMessage("<span class='error'>Internal server error.</span>");
      },
      success: function (data) {
        if ($.isArray(data)) {
          for (var i = 0; i < data.length; ++i) {
            $("#sstable").append("<tr><td id='status-" + data[i].id +
              "' class='status'></td><td>" +
              xmlEscape(data[i].name) + "</td></tr>");
          }
          for (var i = 0; i < data.length; ++i) {
            $.ajax({ url: "/ezid/admin/systemstatus?id=" + data[i].id,
              dataType: "text", cache: false,
              error: function () {
                addMessage("<span class='error'>Internal server " +
                  "error.</span>");
              },
              success: function (id) {
                return function (updown) {
                  if (updown == "up") {
                    $("#status-" + id).addClass("up");
                  } else {
                    $("#status-" + id).addClass("down");
                  }
                }
              }(data[i].id)
            });
          }
        } else {
          if (typeof(data) != "string" || data == "") {
            data = "Internal server error.";
          }
          addMessage("<span class='error'>" + xmlEscape(data) + "</span>");
        }
      }
    });
  }
  systemStatusOpen = !systemStatusOpen;
  return false;
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
  $("textarea").keydown(clearMessages);
  $("#ng_switch").click(newGroup);
  $("#ng_form").submit(makeGroup);
  $("#mg_switch").click(function () { return manageGroup(null); });
  $("#mg_select").change(selectGroup);
  $("#mg_agreement").change(clearMessages);
  $("#mg_shoulders").change(clearMessages);
  $("#mg_form").submit(updateGroup);
  $("#nu_switch").click(newUser);
  $("#nu_userselect").change(clearMessages);
  $("#nu_groupselect").change(clearMessages);
  $("#nu_form").submit(makeUser);
  $("#mu_switch").click(function () { return manageUser(null); });
  $("#mu_select").change(selectUser);
  $("#mu_enabled").click(function () {
    if($("#mu_enabled").attr("checked")) {
      $("#mu_userPassword").val("please supply")
      $("#mu_userPassword").select();
    } else {
      $("#mu_userPassword").val("")
    }
  });
  $("#mu_userPassword").keydown(function () {
    if (!$("#mu_enabled").attr("checked")) {
      $("#mu_enabled").attr("checked", true);
    }
  });
  $("#mu_form").submit(updateUser);
  $("#ss_switch").click(systemStatus);
  $("#sa_switch").click(setAlert);
  $("#rl_switch").click(reload);
});
