// Google Analytics (GA) does NOT capture all search parameters in URL
// https://www.en.advertisercommunity.com/t5/Reports/Multiple-search-category-parameters-on-the-same-URL/m-p/567891/highlight/true#M5801
// This script concatenates all values that have been assigned to an expected set of possibleKeys. 
// Concatenated result of this search
//    keywords=&creator=Dejaco&title=NewHybrids
// will look like this:
//    " ",creator:Dejaco,title:NewHybrids

var GA_SEARCHPARMS_LIB = GA_SEARCHPARMS_LIB || (function(){

  var _uri = '', _mainKey = '', _allKeys = []
  return {
    init : function(uri, mainKey, allKeys) {
      _uri = uri           // expecting url parameters 
                           // eg: "keywords=&creator=Dejaco&title=NewHybrids"
      _mainKey = mainKey   // GA single query parameter
      _allKeys = allKeys   // Array of all query parameters you want tracked in GA
    },
    concat_parms : function() { 
      var mainFieldUsed = false,
        params = [],
        mainKeyValue = '',
        out = _mainKey + '=';
      if (_uri && _uri.includes("=") && _mainKey && _allKeys && _allKeys.length > 0){
        var p = _uri.split('&');
        for (var i = 0; i < p.length; i++) {
          var pair = p[i].split('=')
          if (pair[1] !== '') {
            // remove any leading question mark
            k = pair[0].replace(/^\?/g, '')
            if (_allKeys.indexOf(k) < 0) {
              continue
            }
            if (k == _mainKey && !mainFieldUsed) {
              mainFieldUsed = true
              mainKeyValue = pair[1] 
            } else {
              params.push(pair[0] + ':' + pair[1])
            }
          }
        }
        out += mainKeyValue
        if (params.length > 0) {
          out += "," + params.join(',')
        }
      } else {
        console.log("Undefined argument passed to google_analytics_searchconcat.js:concat_parms()")
        out = ''
      }
      return out
    }  
  };
}());
