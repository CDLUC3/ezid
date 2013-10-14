/*
Copyright or © or Copr. INRIA contributor(s) : Nicolas Debeissat

nicolas.debeissat@gmail.com (http://debeissat.nicolas.free.fr/)

This software is a computer program whose purpose is to generically
generate web forms from a XML specification and, with that form,
being able to generate the XML respecting that specification.

This software is governed by the CeCILL license under French law and
abiding by the rules of distribution of free software.  You can  use, 
modify and/ or redistribute the software under the terms of the CeCILL
license as circulated by CEA, CNRS and INRIA at the following URL
"http://www.cecill.info". 

As a counterpart to the access to the source code and  rights to copy,
modify and redistribute granted by the license, users are provided only
with a limited warranty  and the software's author,  the holder of the
economic rights,  and the successive licensors  have only  limited
liability. 

In this respect, the user's attention is drawn to the risks associated
with loading,  using,  modifying and/or developing or reproducing the
software by the user in light of its specific status of free software,
that may mean  that it is complicated to manipulate,  and  that  also
therefore means  that it is reserved for developers  and  experienced
professionals having in-depth computer knowledge. Users are therefore
encouraged to load and test the software's suitability as regards their
requirements in conditions enabling the security of their systems and/or 
data to be ensured and,  more generally, to use and operate it in the 
same conditions as regards security. 

The fact that you are presently reading this means that you have had
knowledge of the CeCILL license and that you accept its terms.

*/
/*
need to load XML as text and then parse it as xmlDoc.load does not work on FF 3.5
*/
function loadXMLDoc(fname) {
    var xmlDocAsText = loadFile(fname);
    return createDocumentFromText(xmlDocAsText);
}

function loadFile(fname) {
    var xmlhttp = null;
    if (window.XMLHttpRequest) {// code for Firefox, Opera, IE7, etc.
        xmlhttp = new XMLHttpRequest();
    } else if (window.ActiveXObject) {// code for IE6, IE5
        xmlhttp = new ActiveXObject("Microsoft.XMLHTTP");
    }
    if (xmlhttp != null) {
        xmlhttp.open("GET", fname, false);
        xmlhttp.send(null);
        if (xmlhttp.readyState == 4) {
            return xmlhttp.responseText;
        }
    } else {
        alert("Your browser does not support XMLHTTP.");
    }
}

function applyXslt(xml, xsl, asFragment, paramMap) {
    // code for IE 
    if (window.ActiveXObject) {
        var xslt = new ActiveXObject("Msxml2.XSLTemplate.3.0" );
        var xslDoc = new ActiveXObject("Msxml2.FreeThreadedDOMDocument.3.0" );
        xslDoc.async = false;
        xslDoc.load(xsl);
        xslt.stylesheet = xslDoc;
        var xslProc = xslt.createProcessor();
        xslProc.input = xml;
        if (paramMap) {
            for (var i in paramMap) {
                xsltProcessor.addParameter(i, paramMap[i]);
            }
        }
        xslProc.transform();
        return xslProc.output;
    }
    // code for Mozilla, Firefox, Opera, etc.
    else if (document.implementation && document.implementation.createDocument) {
        var xsl = loadXMLDoc(xsl);
        var xsltProcessor = new XSLTProcessor();
        xsltProcessor.importStylesheet(xsl);
        if (paramMap) {
            for (var i in paramMap) {
                xsltProcessor.setParameter(null, i, paramMap[i]);
            }
        }
        var resultDocument;
        if (asFragment) {
            resultDocument = xsltProcessor.transformToFragment(xml, document);
        } else {
            resultDocument = xsltProcessor.transformToDocument(xml, document);
        }
        return resultDocument;
    }
}

function applyXsltOnText(xml, xsl) {
    var xml = createDocumentFromText(xml);
    var result = applyXslt(xml, xsl);
    return innerXML(result);
}