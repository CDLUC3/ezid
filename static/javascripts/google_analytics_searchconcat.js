// Google Analytics does NOT capture all search parameters in URL
// https://www.en.advertisercommunity.com/t5/Reports/Multiple-search-category-parameters-on-the-same-URL/m-p/567891/highlight/true#M5801
// This script concatenates all values that have been assigned to an expected set of possibleKeys. 
// Concatenated result of this search
//    keywords=&creator=Dejaco&title=NewHybrids
// will look like this:
//    " ",creator:Dejaco,title:NewHybrids

var GA_SEARCHPARMS_LIB = GA_SEARCHPARMS_LIB || (function(){

  var _args = {};
  return {
    init : function(Args) {
      // expecting url parameters 
      // eg: "keywords=&creator=Dejaco&title=NewHybrids"
      _args = Args;
    },
    concat_parms : function() { 
      var keywordsFieldUsed = false,
        possibleKeys = ['keywords', 'title', 'creator', 'publisher'],
        params = [],
        keywordValue = '',
        out = 'keywords=';
      if(typeof _args !== "undefined" && _args.includes("=")){
        var p = _args.split('&');
        for (var i = 0; i < p.length; i++) {
          var pair = p[i].split('=')
          if (pair[1] !== '') {
            // remove any leading question mark
            k = pair[0].replace(/^\?/g, '')
            if (possibleKeys.indexOf(k) < 0) {
              continue
            }
            if (k == 'keywords' && !keywordsFieldUsed) {
              keywordsFieldUsed = true
              keywordValue = pair[1] 
            } else {
              params.push(pair[0] + ':' + pair[1])
            }
          }
        }
        out += keywordValue + "," + params.join(',');
      } else {
        console.log("Undefined argument passed to google_analytics_searchconcat.js:concat_parms()");
        out = '';
      }
      return out;
    }  
  };
}());
