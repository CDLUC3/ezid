// Record a Google Analytics Event
// See https://developers.google.com/analytics/devguides/collection/analyticsjs/events

var GA_EVENT_LIB = GA_EVENT_LIB || (function(){

  var _args = {};
  return {
    init : function(Args) {
      // expecting just one argument string of tags separated by spaces 
      // eg: "Forms Submit Login"
      _args = Args;
    },
    record_ga_event : function() { 
      var m = _args.split(" ");
      if (m.length >= 3) {
        ga('send', {
          hitType: 'event',
          eventCategory: m[0],
          eventAction: m[1],
          eventLabel: m[2]
        });
      } else {
        console.log("Looking for three arguments in ga_event. Got " + m.length);
      }
    }  
  };
}());
