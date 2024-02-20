/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

// Record a Matomo Event
// See https://developers.google.com/analytics/devguides/collection/analyticsjs/events

var MATOMO_EVENT_LIB = MATOMO_EVENT_LIB || (function(){

  var _args = {};
  return {
    init : function(Args) {
      // expecting just one argument string of tags separated by spaces
      // eg: "Forms Submit Login"
      _args = Args;
    },
    record_matomo_event : function() {
      var m = _args.split(" ");
      if (m.length >= 3) {
        _paq.push(['trackEvent', m[0], m[1], m[2]]);
      } else {
        console.log("Looking for three arguments in event. Got " + m.length);
      }
    }
  };
}());
