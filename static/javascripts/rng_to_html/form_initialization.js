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
eval(function(p,a,c,k,e,r){e=function(c){return(c<a?'':e(parseInt(c/a)))+((c=c%a)>35?String.fromCharCode(c+29):c.toString(36))};if(!''.replace(/^/,String)){while(c--)r[e(c)]=k[c]||e(c);k=[function(e){return r[e]}];e=function(){return'\\w+'};c=1};while(c--)if(k[c])p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c]);return p}('9 1n(a,b){W(b);3 c=1o(a);4(c.X){c.X()}6 4(c.Y.Z){c.Y.Z()}3 d=1p(c);4(d.q=="1q"){3 e=10.11("r");e.K=12(d);13(e,b)}6{3 f="/"+d.D;L(d,f,b)}};9 W(a){3 b=14(a);t(3 i=0;i<b.8;i++){3 c=b[i];4(c.q.u()=="M"){4(c.5("s")=="1r"){4(c.5("v")=="+"){N(c,1)}}6 4(c.5("s")=="E"||c.5("s")=="15"){c.v=""}}6 4(c.q.u()=="F"){O(c,"")}}};9 L(a,b,c){4(a.A&&a.A.8>0){t(3 i=0;i<a.A.8;i++){3 d=a.A[i].z;3 e=a.A[i].v;G(b+"/@"+d,e,c)}}t(3 i=0;i<a.x.8;i++){4(a.x[i].16==1s){3 f=a.x[i];3 g=f.D;3 h=17(f,b,c);4(h!=0){3 j=h;3 k=B(f);18(k){4(k.q.u()!=f.q.u()){3 l=P(f,k,b,c);4(!l){19}}j++;k=B(k)}3 m=1a(b,g,c);N(m,j);g+="["+h+"]"}L(a.x[i],b+"/"+g,c)}6 4(a.x[i].16==1t){4(!1u(a.x[i])){3 n=12(a.x[i]);G(b,n,c);G(b+"/E()",n,c)}}}};9 G(a,b,c){3 d=Q(a,c);4(b.H(" ")&&d.8>1){3 e=b.1v(" ");3 j=0;t(3 i=0;i<d.8&&j<e.8;i++){4(d[i].5("s")=="1b"){C(d[i],b)}6 4(C(d[i],e[j])){j++}}}6{t(3 i=0;i<d.8;i++){C(d[i],b)}}};9 I(a){3 b=1w(a);b=b.1x(/(\\w)\\//g,"$1(\\\\[1\\\\])?/");7 b};9 Q(a,b){3 c=I(a);4(!a.H("E\\(\\)")&&!a.H("@")){c=c+"(\\\\[1\\\\])?"}c=1y 1z("^"+c+"$");3 d=14(b,c);7 d};9 C(a,b){4(!1c(a)){R(a)}4(a.q.u()=="F"){7 O(a,b)}6 4(a.q.u()=="15"){a.v=b;7 y}6 4(a.5("s")=="E"){a.v=b;7 y}6 4(a.5("s")=="1d"){3 c="<i>!1A 1B 1C 1D 1e 1E 1F 1G v 1H 1I M s=1d 1e : <1J />"+b+"</i>";4(a.S&&a.S.5("1f")=="1g"){a.S.K=c}6{3 d=10.11("r");d.C("1f","1g");d.K=c;13(d,a)}7 y}6 4(a.5("s")=="1K"&&a.5("v")==b){a.1h=y;7 y}6 4(a.5("s")=="1b"&&b.H(a.5("v"))){a.1h=y;7 y}7 1i};9 R(a){3 b=T(a,"r","U");3 c=b.5("z");3 d=J(b,"F");O(d,c);4(!1c(d)){R(a)}1L(d)};9 17(a,b,c){3 d=0;3 e=a.q;3 f=J(a);18(f){4(f.q.u()!=a.q.u()){3 g=P(a,f,b,c);4(!g){19}}d++;f=J(f)}4(d!=0){d++}6 4(B(a,e)){d++}7 d};9 P(a,b,c,d){3 e=I(c+"/"+a.D+"[1]");3 f=I(c+"/"+b.D+"[1]");3 g=V(d,"r","z",e);3 h=V(d,"r","z",f);4(g.8>0&&h.8>0){3 i=g[0];3 j=h[0];4(i&&j){3 k=T(i,"r","U");3 l=T(j,"r","U");4(k&&l){3 m=k.1j;3 n=l.1j;4(m.1M(n)){3 o=J(k,"F");3 p=o.5("z");7/\\[\\]$/.1N(p)}}}}7 1i};9 1a(a,b,c){3 d=Q(a,c);4(d.8==2){7 d[0]}6{t(3 i=0;i<d.8;i+=2){3 e=B(d[i],"r");4(V(e,"r","z",a+"/"+b+"\\\\[.*\\\\]").8>0){7 d[i]}}}};9 N(a,b){3 c=1k(a.5("1l"));t(3 i=c;i<b;i++){1O(a)}c=1k(a.5("1l"));t(3 i=c;i>b&&i>1;i--){1m=B(a,"M");1P(1m)}};',62,114,'|||var|if|getAttribute|else|return|length|function|||||||||||||||||tagName|div|type|for|toLowerCase|value||childNodes|true|name|attributes|getNextSiblingElement|setAttribute|nodeName|text|select|setData|match|getNameRegExp|getPreviousSiblingElement|innerHTML|addData|input|addMultipleElements|setSelected|areConcurrentMarkups|getInputFields|setOptionDisplayed|nextSibling|getFirstAncestorByTagAndClass|choice_content|getElementsByAttribute|eraseFormValues|normalizeDocument|documentElement|normalize|document|createElement|textContent|insertAfter|getInputs|textarea|nodeType|getIndexAmongMultiple|while|break|getCorrespondingAddButton|checkbox|isDisplayed|file|to|id|warningtext|checked|false|parentNode|parseInt|nbelmtsadded|removeButton|initInputElements|loadXMLDoc|getFirstChildElement|parsererror|button|ELEMENT_NODE|TEXT_NODE|is_all_ws|split|escapeRegExp|replace|new|RegExp|it|is|not|allowed|programmatically|set|the|of|that|br|radio|showOptionContent|isSameNode|test|addOne|removeOne'.split('|'),0,{}))