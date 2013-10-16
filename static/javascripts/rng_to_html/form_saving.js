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
eval(function(p,a,c,k,e,r){e=function(c){return(c<a?'':e(parseInt(c/a)))+((c=c%a)>35?String.fromCharCode(c+29):c.toString(36))};if(!''.replace(/^/,String)){while(c--)r[e(c)]=k[c]||e(c);k=[function(e){return r[e]}];e=function(){return'\\w+'};c=1};while(c--)if(k[c])p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c]);return p}('8 14(a,b){2 c=K.L(a);4(c.C.D()!="M"){c=15(c,"M")}2 d=N(c);2 e=O(c,d);4(b){2 f=K.L(b);f.5=16(e);f.5=f.5.x(/></g,">\\n<")}6{v e}};8 N(a){2 b=17(a);2 c=P Q();9(2 i=0;i<b.7;i++){2 d=b[i];4(18(d)){4((d.C.D()==\'19\')&&(d.R[d.S].5!=\'\')){s(d.t,d.R[d.S].5,c)}6 4((d.5)&&(d.5!=\'\')){4(d.C.D()==\'1a\'){s(d.t,d.5,c)}6 4(d.u("y")=="T"){s(d.t,d.5,c)}6 4(d.u("y")=="1b"){s(d.t,d.5,c)}6 4(d.u("y")=="1c"&&d.U==V){s(d.t,d.5,c)}6 4(d.u("y")=="1d"&&d.U==V){s(d.t,d.5,c)}}}}v c};8 s(a,b,c){a=a.x(/@(.*)\\[.*\\]/,"@$1");4(!c[a]){c[a]=b}6{c[a]+=" "+b}}8 W(a){2 b=a.1e("1f");2 c=P Q();9(2 i=0;i<b.7;i++){c[b[i].u("1g")]=b[i].u("1h")}v c};8 O(a,b){2 c=1i();2 d=W(a);9(2 e 1j b){X(e,b[e],c,d)}E(c.F);v c};8 X(a,b,c,d){2 e=z;2 f=z;2 g=a.1k("/");9(2 i=1;i<g.7;i++){2 h=g[i];4(h=="T()"){f=G(e,b)}6 4(h.H("@")){h=h.x(/^@/,"");4(h.H(/:/)){2 k=Y(h,d);f=c.1l(k,h);e.1m(f)}6{f=c.1n(h);e.1o(f)}f.5=b}6{h=h.x(\'[]\',\'\');2 k=Y(h,d);2 l=Z(h);4(!e){4(!c.F){2 m=c.I(k,h);c.A(m)}e=c.F}6 4(h.H(/\\[/)){2 n=h.10("[");2 o=h.10("]");2 p=1p(h.11(n+1,o));h=h.11(0,n);l=Z(h);2 q=e.B(k,l).7;9(2 j=q;j<p;j++){2 r=c.I(k,h);e.A(r)}e=e.B(k,l).w(p-1)}6{4(e.B(k,l).7==0){2 r=c.I(k,h);e.A(r)}e=e.B(k,l).w(0)}}}4(f==z&&e!=z){f=G(e,b)}};8 G(a,b){2 c=a.J;9(2 i=0;i<c.7;i++){4(c.w(i).12==3){a.13(c.w(i))}}2 d=a.1q.1r(b);a.A(d);v d};8 E(a){2 b=a.J;9(2 i=0;i<b.7;i++){2 c=b.w(i);4(c.12==1s){4(c.J.7!=0){E(c)}6 4(c.1t.7==0){a.13(c);i--}}}};',62,92,'||var||if|value|else|length|function|for|||||||||||||||||||addValueToFormArray|name|getAttribute|return|item|replace|type|null|appendChild|getElementsByTagNameNS|tagName|toLowerCase|eraseEmptyElements|documentElement|replaceTextNodesDirectlyUnder|match|createElementNS|childNodes|document|getElementById|form|createFormDataArray|createXml|new|Array|options|selectedIndex|text|checked|true|getNamespaces|addFormElm|getNamespaceURIFromNodeName|removePrefix|indexOf|substring|nodeType|removeChild|saveChanges|getFirstChildElement|innerXML|getInputs|isDisplayed|select|textarea|file|radio|checkbox|getElementsByTagName|namespace|prefix|uri|createDocument|in|split|createAttributeNS|setAttributeNodeNS|createAttribute|setAttributeNode|parseInt|ownerDocument|createTextNode|ELEMENT_NODE|attributes'.split('|'),0,{}))