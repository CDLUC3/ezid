// Google Analytics (GA) does NOT capture all search parameters in URL
// https://www.en.advertisercommunity.com/t5/Reports/Multiple-search-category-parameters-on-the-same-URL/m-p/567891/highlight/true#M5801
// This script concatenates all values that have been assigned to an expected set of allQueryKeys. 
// This search query
//    keywords=&creator=Dejaco&title=NewHybrids&object_type=Image
// will look like this in GA:
//    keywords=,creator:Dejaco,title:NewHybrids&object_type=Image
// The category parameter (in this example 'object_type') is distinct from query parameters

var GA_SEARCHPARMS_LIB = GA_SEARCHPARMS_LIB || (function(){

  var _uri = '', _mainKey = '', _categoryKey = '', _allQueryKeys = []
  return {
    init : function(uri, mainKey, categoryKey, allQueryKeys) {
      _uri = uri                    // expecting url parameters 
                                    // eg: "keywords=&creator=Dejaco&title=NewHybrids"
      _mainKey = mainKey            // GA single query parameter
      _categoryKey = categoryKey    // GA single category parameter
      _allQueryKeys = allQueryKeys  // Array of all query parameters you want tracked in GA
    },
    concat_parms : function() { 
      var mainFieldUsed = false,
        params = [],
        mainKeyValue = '',
        out = _mainKey + '=',
        categoryOut = '';
      if (_uri && _uri.includes("=") && _mainKey && _allQueryKeys && _allQueryKeys.length > 0){
        var p = _uri.split('&');
        for (var i = 0; i < p.length; i++) {
          var pair = p[i].split('=')
          if (pair[1] !== '') {
            // remove any leading question mark
            k = pair[0].replace(/^\?/g, '')
            if (_categoryKey != '' && k === _categoryKey){
              categoryOut = "&" + _categoryKey + "=" + pair[1]
              continue
            } else if (_allQueryKeys.indexOf(k) < 0) {
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
        out += categoryOut 
      } else {
        console.log("Undefined argument passed to google_analytics_searchconcat.js:concat_parms()")
        out = ''
      }
      return out
    }  
  };
}());
