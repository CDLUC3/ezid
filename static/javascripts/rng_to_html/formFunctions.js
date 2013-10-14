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
eval(function(p,a,c,k,e,r){e=function(c){return(c<a?'':e(parseInt(c/a)))+((c=c%a)>35?String.fromCharCode(c+29):c.toString(36))};if(!''.replace(/^/,String)){while(c--)r[e(c)]=k[c]||e(c);k=[function(e){return r[e]}];e=function(){return'\\w+'};c=1};while(c--)if(k[c])p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c]);return p}('7 1b(a,b){3 c=1c(a);3 d=S(c);5(1d(a,".1e")){d=u(d,"v/m/1f.m")}3 e=d.1g("1h://1i.1j/1k/1l/1.0","1m").1n(0);5(e){3 f=e.1o;6(3 i=0;i<f.p;i++){5(f[i].1p.1q("T")){3 g=d.1r("1s","1t:1u");3 h=f[i].1v.1w(/^T$/,"");g.n("1x",h);g.n("1y",f[i].1z);e.w(g)}}5(b){3 j=F G();j["1A"]=b;3 k=u(d,"v/m/H.m",o,j)}9{3 k=u(d,"v/m/H.m",o)}3 l=U.V("W");1B(l);l.w(k);I(U.V("W"))}};7 1C(a){3 b=S(a);x u(b,"v/m/H.m",o)};7 I(a){3 b=a.y("t");6(3 i=0;i<b.p;i++){5(1D(b[i])){J(b[i])}}};7 1E(a){3 b=X(a.K,"q","z","Y");3 c=Z(a.4("A"));3 d=c+1;5(c==0){b.r.s=""}9{3 e=b.L(o);1F(e,b);M(e,a,d);3 f=e.y("t");3 g=b.y("t");6(3 i=0;i<f.p;i++){1G(f[i],g[i].10[g[i].11].12)}3 h=N(e,"B","13","14");3 j=N(b,"B","13","14");6(3 i=0;i<h.p;i++){5(h[i].C){j[i].C=o}9 5(j[i].C){h[i].C=o}}}a.n("A",d)};7 1H(a){3 b=1I(a,"B");3 c=Z(b.4("A"));3 d=c-1;5(c==0){x}3 e=a.K;3 f=X(e,"q","z","Y");5(c==1){f.r.s="15"}9{e.1J(f)}b.n("A",d)};7 1K(a){3 b=a.4("1L");3 c=a.4("16");3 d=1M(a,"q","1N",b);3 e=d.L(o);3 f=1O(d,"q","16",c);d.r.s="";f.r.s="";I(d);O(e,a.4("8"));17(e);f.w(a);f.w(e)};7 P(a,b){3 c=a.4("8");5(!c){c=a.4("6")}3 d=b.4("8");3 e=c.18("[",d.p);3 f=F G(2);5(e!=-1){3 g=c.18("]",d.p);f[0]=c.1P(0,e);f[1]=c.1Q(g+1)}9{f[0]=c;f[1]=""}x f};7 J(a){3 b=a.10[a.11].12;3 c=D(a,"q");1R(c&&c.19.1a()=="q"&&c.4("z")=="1S"){5(c.4("8")==b){c.r.s="";3 d=c.y("t");6(3 i=0;i<d.p;i++){J(d[i])}}9{c.r.s="15"}c=1T(c)}};7 M(a,b,c){6(3 d=Q(a);d;d=D(d)){5(d.4("8")&&d.4("8").E(0)=="/"){3 e=P(d,b);d.n("8",e[0]+"["+c+"]"+e[1])}9 5(d.4("6")&&d.4("6").E(0)=="/"){3 e=P(d,b);d.n("6",e[0]+"["+c+"]"+e[1])}M(d,b,c)}};7 O(a,b){6(3 c=Q(a);c;c=D(c)){5(c.4("8")&&c.4("8").E(0)=="/"){c.n("8",b+c.4("8"))}9 5(c.4("6")&&c.4("6").E(0)=="/"){c.n("6",b+c.4("6"))}O(c,b)}};7 17(a){3 b=N(a,"1U","z","1V");6(3 i 1W b){3 c=b[i];c.K.1X(c.L(o),c)}};7 1Y(a,b){3 c=F G();R(a,b,c);x c};7 R(a,b,c){6(3 d=Q(a);d;d=D(d)){3 e=d.19.1a();5(e=="1Z"||e=="B"||(e=="t"&&d.4("20")=="21")){5(!b||b.22(d.4("8"))){c.23(d)}}9{R(d,b,c)}}};',62,128,'|||var|getAttribute|if|for|function|name|else|||||||||||||xsl|setAttribute|true|length|div|style|display|select|applyXslt|forms|appendChild|return|getElementsByTagName|class|nbelmtsadded|input|checked|getNextSiblingElement|charAt|new|Array|RNGtoHTMLform_standalone|initSelectElements|showOptionContent|parentNode|cloneNode|setNewIndexUnder|getElementsByAttribute|setNewCyclicXpathUnder|splitAroundFirstBrackets|getFirstChildElement|getInputsUnder|createDocumentFromText|xmlns|document|getElementById|form|getLastChildElementByTagAndAtt|multiple|parseInt|options|selectedIndex|text|type|radio|none|cyclic_place|duplicateIndentUnder|indexOf|tagName|toLowerCase|getForm|loadFile|endsWith|xsd|XSDtoRNG|getElementsByTagNameNS|http|relaxng|org|ns|structure|grammar|item|attributes|nodeName|match|createElementNS|namespace_declaration|nsp|namespace|localName|replace|prefix|uri|value|maxRefs|removeChildren|returnForm|isDisplayed|addOne|insertAfter|setSelected|removeOne|getPreviousSiblingElement|removeChild|addCyclic|cyclic|getNextSiblingElementByTagAndAtt|refs|getElementByTagClassRefs|substr|substring|while|choice_content|node_after|span|indent|in|insertBefore|getInputs|textarea|sendselect|yes|test|push'.split('|'),0,{}))