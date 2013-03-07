isString = function(/*anything*/ it) {
    // summary:	Return true if it is a String.
    return (typeof it == "string" || it instanceof String);
};

toArray = function (arrayLike, startOffset) {
    var array = [];
    for(var i = startOffset||0; i < arrayLike.length; i++){
        array.push(arrayLike[i]);
    }
    return array; // Array
};


substituteParams = function (template, hash) {
    var map = (typeof hash == "object") ? hash : toArray(arguments, 1);
    return template.replace(/\%\{(\w+)\}/g, function (match, key) {
        if (typeof(map[key]) != "undefined" && map[key] != null) {
            return map[key];
        }
    });
};
capitalize = function (str) {
    if (!isString(str)) {
        return "";
    }
    if (arguments.length == 0) {
        str = this;
    }
    var words = str.split(" ");
    for (var i = 0; i < words.length; i++) {
        words[i] = words[i].charAt(0).toUpperCase() + words[i].substring(1);
    }
    return words.join(" ");
};
isBlank = function (str) {
    if (!isString(str)) {
        return true;
    }
    return (trim(str).length == 0);
};
encodeAscii = function (str) {
    var ret = "";
    var value = escape(str);
    var match, re = /%u([0-9A-F]{4})/i;
    while ((match = value.match(re))) {
        var num = Number("0x" + match[1]);
        var newVal = escape("&#" + num + ";");
        ret += value.substring(0, match.index) + newVal;
        value = value.substring(match.index + match[0].length);
    }
    ret += value.replace(/\+/g, "%2B");
    return ret;
};
dojoescape = function (type, str) {
    var args = toArray(arguments, 1);
    switch (type.toLowerCase()) {
        case "xml":
        case "html":
        case "xhtml":
            return escapeXml.apply(this, args);
        case "sql":
            return escapeSql.apply(this, args);
        case "regexp":
        case "regex":
            return escapeRegExp.apply(this, args);
        case "javascript":
        case "jscript":
        case "js":
            return escapeJavaScript.apply(this, args);
        case "ascii":
            return encodeAscii.apply(this, args);
        default:
            return str;
    }
};
escapeXml = function (str, noSingleQuotes) {
    str = str.replace(/&/gm, "&amp;").replace(/</gm, "&lt;").replace(/>/gm, "&gt;").replace(/"/gm, "&quot;");
    if (!noSingleQuotes) {
        str = str.replace(/'/gm, "&#39;");
    }
    return str;
};
escapeSql = function (str) {
    return str.replace(/'/gm, "''");
};
escapeRegExp = function (str) {
    return str.replace(/\\/gm, "\\\\").replace(/([\f\b\n\t\r[\^$|?*+(){}])/gm, "\\$1");
};
escapeJavaScript = function (str) {
    return str.replace(/(["'\f\b\n\t\r])/gm, "\\$1");
};
escapeString = function (str) {
    return ("\"" + str.replace(/(["\\])/g, "\\$1") + "\"").replace(/[\f]/g, "\\f").replace(/[\b]/g, "\\b").replace(/[\n]/g, "\\n").replace(/[\t]/g, "\\t").replace(/[\r]/g, "\\r");
};
summary = function (str, len) {
    if (!len || str.length <= len) {
        return str;
    }
    return str.substring(0, len).replace(/\.+$/, "") + "...";
};
endsWith = function (str, end, ignoreCase) {
    if (ignoreCase) {
        str = str.toLowerCase();
        end = end.toLowerCase();
    }
    if ((str.length - end.length) < 0) {
        return false;
    }
    return str.lastIndexOf(end) == str.length - end.length;
};
endsWithAny = function (str) {
    for (var i = 1; i < arguments.length; i++) {
        if (endsWith(str, arguments[i])) {
            return true;
        }
    }
    return false;
};
startsWith = function (str, start, ignoreCase) {
    if (ignoreCase) {
        str = str.toLowerCase();
        start = start.toLowerCase();
    }
    return str.indexOf(start) == 0;
};
startsWithAny = function (str) {
    for (var i = 1; i < arguments.length; i++) {
        if (startsWith(str, arguments[i])) {
            return true;
        }
    }
    return false;
};
has = function (str) {
    for (var i = 1; i < arguments.length; i++) {
        if (str.indexOf(arguments[i]) > -1) {
            return true;
        }
    }
    return false;
};
normalizeNewlines = function (text, newlineChar) {
    if (newlineChar == "\n") {
        text = text.replace(/\r\n/g, "\n");
        text = text.replace(/\r/g, "\n");
    } else {
        if (newlineChar == "\r") {
            text = text.replace(/\r\n/g, "\r");
            text = text.replace(/\n/g, "\r");
        } else {
            text = text.replace(/([^\r])\n/g, "$1\r\n").replace(/\r([^\n])/g, "\r\n$1");
        }
    }
    return text;
};
splitEscaped = function (str, charac) {
    var components = [];
    for (var i = 0, prevcomma = 0; i < str.length; i++) {
        if (str.charAt(i) == "\\") {
            i++;
            continue;
        }
        if (str.charAt(i) == charac) {
            components.push(str.substring(prevcomma, i));
            prevcomma = i + 1;
        }
    }
    components.push(str.substr(prevcomma));
    return components;
};

