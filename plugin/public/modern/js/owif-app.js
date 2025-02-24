/*! For license information please see owif-app.js.LICENSE.txt */
!function(){var e={353:function(e,t,r){"use strict";r.r(t);var n=r(916),o=r.n(n);function i(e,t,r){return t in e?Object.defineProperty(e,t,{value:r,enumerable:!0,configurable:!0,writable:!0}):e[t]=r,e}const a=e=>{console.info("%cOWIF","color: #fff; font-weight: bold; background-color: #333; padding: 2px 4px 1px; border-radius: 2px;",e)};class c{constructor(){i(this,"debugLog",((...e)=>console.debug(...e))),i(this,"regexDateFormat",new RegExp(/\d{4}-\d{2}-\d{2}/)),i(this,"toUnixDate",(e=>Date.parse(`${e}Z`)/1e3)),i(this,"isBouquet",(e=>!e.startsWith("1:134:1")&&e.includes("FROM BOUQUET"))),i(this,"fetchData",(async(e,t={method:"get"})=>{try{const r=await fetch(e,t);if(r.ok){const e=r.headers.get("content-type");if(self.debugLog(e),e&&e.includes("application/json"))return await r.json();{const e=await r.text();return xml2json(e)}}throw new Error(r.statusText||r.status)}catch(e){throw new Error(e)}})),self=this}getStrftime(e=new Date){const t=new Date(1e3*Math.round(e));let r=strftime("%X",t);return r=r.match(/\d{2}:\d{2}|[^:\d]+/g).join(" "),strftime("%a %x",t)+" "+r}getToTimeText(e,t){const r=t-e,n=Math.floor(r/864e5),o=new Date(1e3*Math.round(e)).getDay(),i=new Date(1e3*Math.round(t)).getDay();let a="";if(0===r)a="-";else{let e=strftime("%X",new Date(1e3*Math.round(t)));e=e.match(/\d{2}:\d{2}|[^:\d]+/g).join(" "),a=n<1&&i-o==0?"same day - "+e:n<2&&i-o==1?"next day - "+e:this.getStrftime(t)}return a}}class s{constructor(){}async instantRecord(){let e=await fetch("/api/recordnow?infinite=true");if(e.ok){const t=await e.json();return await t}throw new Error(`HTTP error! status: ${e.status}`)}}class u{constructor(){}async getStatusInfo(){let e=await fetch("/api/statusinfo");if(e.ok){const t=await e.json();return await t}throw new Error(`HTTP error! status: ${e.status}`)}async getTags(){let e=await fetch("/api/gettags");if(e.ok){const t=await e.json();return await t.tags}throw new Error(`HTTP error! status: ${e.status}`)}async getAllServices(e,t){let r=1==e?"&noiptv=1":"",n=await fetch("/api/getallservices?nolastscanned=1"+r);if(n.ok){const e=await n.json();let r=[];const o=e.services.map((e=>{const n=e.subservices.map((r=>{const n=r.servicename;let o=r.servicereference;const i=o.indexOf("1:64:")>-1;if(t){const e=o.lastIndexOf("::");e>0&&(o=o.substring(0,e-1))}return{name:n,sRef:o,bouquetName:e.servicename,extendedName:n+"<small>"+e.servicename+"</small>",disabled:i}}));return r=r.concat(n),{name:e.servicename,sRef:e.servicereference,channels:n}}));return await{channels:r,bouquets:o}}throw new Error(`HTTP error! status: ${n.status}`)}async sendKeyboardText(e){const t=void 0===e?{ok:!1,status:"Empty request"}:await fetch(`/api/remotecontrol?text=${e}`);if(t.ok){const e=await t.json();return callScreenShot(),e}throw new Error(`HTTP error! status: ${t.status}`)}}class l{constructor(){i(this,"choicesConfig",{removeItemButton:!0,duplicateItemsAllowed:!1,resetScrollPosition:!1,shouldSort:!1,searchResultLimit:100,placeholder:!0,itemSelectText:""}),this.initEventHandlers()}initEventHandlers(){const e=this,t=new RegExp(/#\/?(.*)\??(.*)/gi);window.onhashchange=function(e){const r=e.target.location.hash.replace("#/","#").split("/")[0],n=r.replace(t,"/ajax/$1");r&&load_maincontent_spin(n)},document.querySelectorAll('input[name="skinpref"]').forEach((t=>{t.onchange=()=>{e.skinPref=event.target.value}}))}fullscreen(e,t){!0===e?o().request(t).then((()=>{a("GUI:fullscreen activated")})):!1===e?o().exit().then((()=>{a("GUI:fullscreen deactivated")})):o().toggle(t).then((()=>{a("GUI:fullscreen toggled")}))}get skinPref(){return document.body.dataset.skinpref||""}set skinPref(e){const t="skin--",r=this.skinPref;fetch(`/api/setskincolor?skincolor=${e}`),document.body.classList.replace(`${t}${r}`,`${t}${e}`),document.body.dataset.skinpref=e}preparedChoices(){const e={},t="data-choices-select";return document.querySelectorAll(`[${t}]`).forEach((r=>{let n=r.dataset.choicesConfig||"{}";n=n?JSON.parse(n):{},n=Object.assign({},this.choicesConfig,n),e[r.getAttribute(`${t}`)]=new Choices(r,n)})),e}}window.owif=new class{constructor(){this.utils=new c,this.stb=new s,this.api=new u,this.gui=new l}}},452:function(e){var t=function(e){"use strict";var t,r=Object.prototype,n=r.hasOwnProperty,o="function"==typeof Symbol?Symbol:{},i=o.iterator||"@@iterator",a=o.asyncIterator||"@@asyncIterator",c=o.toStringTag||"@@toStringTag";function s(e,t,r){return Object.defineProperty(e,t,{value:r,enumerable:!0,configurable:!0,writable:!0}),e[t]}try{s({},"")}catch(e){s=function(e,t,r){return e[t]=r}}function u(e,t,r,n){var o=t&&t.prototype instanceof w?t:w,i=Object.create(o.prototype),a=new T(n||[]);return i._invoke=function(e,t,r){var n=f;return function(o,i){if(n===d)throw new Error("Generator is already running");if(n===p){if("throw"===o)throw i;return P()}for(r.method=o,r.arg=i;;){var a=r.delegate;if(a){var c=L(a,r);if(c){if(c===g)continue;return c}}if("next"===r.method)r.sent=r._sent=r.arg;else if("throw"===r.method){if(n===f)throw n=p,r.arg;r.dispatchException(r.arg)}else"return"===r.method&&r.abrupt("return",r.arg);n=d;var s=l(e,t,r);if("normal"===s.type){if(n=r.done?p:h,s.arg===g)continue;return{value:s.arg,done:r.done}}"throw"===s.type&&(n=p,r.method="throw",r.arg=s.arg)}}}(e,r,a),i}function l(e,t,r){try{return{type:"normal",arg:e.call(t,r)}}catch(e){return{type:"throw",arg:e}}}e.wrap=u;var f="suspendedStart",h="suspendedYield",d="executing",p="completed",g={};function w(){}function m(){}function y(){}var v={};s(v,i,(function(){return this}));var b=Object.getPrototypeOf,x=b&&b(b(O([])));x&&x!==r&&n.call(x,i)&&(v=x);var E=y.prototype=w.prototype=Object.create(v);function k(e){["next","throw","return"].forEach((function(t){s(e,t,(function(e){return this._invoke(t,e)}))}))}function F(e,t){function r(o,i,a,c){var s=l(e[o],e,i);if("throw"!==s.type){var u=s.arg,f=u.value;return f&&"object"==typeof f&&n.call(f,"__await")?t.resolve(f.__await).then((function(e){r("next",e,a,c)}),(function(e){r("throw",e,a,c)})):t.resolve(f).then((function(e){u.value=e,a(u)}),(function(e){return r("throw",e,a,c)}))}c(s.arg)}var o;this._invoke=function(e,n){function i(){return new t((function(t,o){r(e,n,t,o)}))}return o=o?o.then(i,i):i()}}function L(e,r){var n=e.iterator[r.method];if(n===t){if(r.delegate=null,"throw"===r.method){if(e.iterator.return&&(r.method="return",r.arg=t,L(e,r),"throw"===r.method))return g;r.method="throw",r.arg=new TypeError("The iterator does not provide a 'throw' method")}return g}var o=l(n,e.iterator,r.arg);if("throw"===o.type)return r.method="throw",r.arg=o.arg,r.delegate=null,g;var i=o.arg;return i?i.done?(r[e.resultName]=i.value,r.next=e.nextLoc,"return"!==r.method&&(r.method="next",r.arg=t),r.delegate=null,g):i:(r.method="throw",r.arg=new TypeError("iterator result is not an object"),r.delegate=null,g)}function S(e){var t={tryLoc:e[0]};1 in e&&(t.catchLoc=e[1]),2 in e&&(t.finallyLoc=e[2],t.afterLoc=e[3]),this.tryEntries.push(t)}function j(e){var t=e.completion||{};t.type="normal",delete t.arg,e.completion=t}function T(e){this.tryEntries=[{tryLoc:"root"}],e.forEach(S,this),this.reset(!0)}function O(e){if(e){var r=e[i];if(r)return r.call(e);if("function"==typeof e.next)return e;if(!isNaN(e.length)){var o=-1,a=function r(){for(;++o<e.length;)if(n.call(e,o))return r.value=e[o],r.done=!1,r;return r.value=t,r.done=!0,r};return a.next=a}}return{next:P}}function P(){return{value:t,done:!0}}return m.prototype=y,s(E,"constructor",y),s(y,"constructor",m),m.displayName=s(y,c,"GeneratorFunction"),e.isGeneratorFunction=function(e){var t="function"==typeof e&&e.constructor;return!!t&&(t===m||"GeneratorFunction"===(t.displayName||t.name))},e.mark=function(e){return Object.setPrototypeOf?Object.setPrototypeOf(e,y):(e.__proto__=y,s(e,c,"GeneratorFunction")),e.prototype=Object.create(E),e},e.awrap=function(e){return{__await:e}},k(F.prototype),s(F.prototype,a,(function(){return this})),e.AsyncIterator=F,e.async=function(t,r,n,o,i){void 0===i&&(i=Promise);var a=new F(u(t,r,n,o),i);return e.isGeneratorFunction(r)?a:a.next().then((function(e){return e.done?e.value:a.next()}))},k(E),s(E,c,"Generator"),s(E,i,(function(){return this})),s(E,"toString",(function(){return"[object Generator]"})),e.keys=function(e){var t=[];for(var r in e)t.push(r);return t.reverse(),function r(){for(;t.length;){var n=t.pop();if(n in e)return r.value=n,r.done=!1,r}return r.done=!0,r}},e.values=O,T.prototype={constructor:T,reset:function(e){if(this.prev=0,this.next=0,this.sent=this._sent=t,this.done=!1,this.delegate=null,this.method="next",this.arg=t,this.tryEntries.forEach(j),!e)for(var r in this)"t"===r.charAt(0)&&n.call(this,r)&&!isNaN(+r.slice(1))&&(this[r]=t)},stop:function(){this.done=!0;var e=this.tryEntries[0].completion;if("throw"===e.type)throw e.arg;return this.rval},dispatchException:function(e){if(this.done)throw e;var r=this;function o(n,o){return c.type="throw",c.arg=e,r.next=n,o&&(r.method="next",r.arg=t),!!o}for(var i=this.tryEntries.length-1;i>=0;--i){var a=this.tryEntries[i],c=a.completion;if("root"===a.tryLoc)return o("end");if(a.tryLoc<=this.prev){var s=n.call(a,"catchLoc"),u=n.call(a,"finallyLoc");if(s&&u){if(this.prev<a.catchLoc)return o(a.catchLoc,!0);if(this.prev<a.finallyLoc)return o(a.finallyLoc)}else if(s){if(this.prev<a.catchLoc)return o(a.catchLoc,!0)}else{if(!u)throw new Error("try statement without catch or finally");if(this.prev<a.finallyLoc)return o(a.finallyLoc)}}}},abrupt:function(e,t){for(var r=this.tryEntries.length-1;r>=0;--r){var o=this.tryEntries[r];if(o.tryLoc<=this.prev&&n.call(o,"finallyLoc")&&this.prev<o.finallyLoc){var i=o;break}}i&&("break"===e||"continue"===e)&&i.tryLoc<=t&&t<=i.finallyLoc&&(i=null);var a=i?i.completion:{};return a.type=e,a.arg=t,i?(this.method="next",this.next=i.finallyLoc,g):this.complete(a)},complete:function(e,t){if("throw"===e.type)throw e.arg;return"break"===e.type||"continue"===e.type?this.next=e.arg:"return"===e.type?(this.rval=this.arg=e.arg,this.method="return",this.next="end"):"normal"===e.type&&t&&(this.next=t),g},finish:function(e){for(var t=this.tryEntries.length-1;t>=0;--t){var r=this.tryEntries[t];if(r.finallyLoc===e)return this.complete(r.completion,r.afterLoc),j(r),g}},catch:function(e){for(var t=this.tryEntries.length-1;t>=0;--t){var r=this.tryEntries[t];if(r.tryLoc===e){var n=r.completion;if("throw"===n.type){var o=n.arg;j(r)}return o}}throw new Error("illegal catch attempt")},delegateYield:function(e,r,n){return this.delegate={iterator:O(e),resultName:r,nextLoc:n},"next"===this.method&&(this.arg=t),g}},e}(e.exports);try{regeneratorRuntime=t}catch(e){"object"==typeof globalThis?globalThis.regeneratorRuntime=t:Function("r","regeneratorRuntime = r")(t)}},916:function(e){!function(){"use strict";var t="undefined"!=typeof window&&void 0!==window.document?window.document:{},r=e.exports,n=function(){for(var e,r=[["requestFullscreen","exitFullscreen","fullscreenElement","fullscreenEnabled","fullscreenchange","fullscreenerror"],["webkitRequestFullscreen","webkitExitFullscreen","webkitFullscreenElement","webkitFullscreenEnabled","webkitfullscreenchange","webkitfullscreenerror"],["webkitRequestFullScreen","webkitCancelFullScreen","webkitCurrentFullScreenElement","webkitCancelFullScreen","webkitfullscreenchange","webkitfullscreenerror"],["mozRequestFullScreen","mozCancelFullScreen","mozFullScreenElement","mozFullScreenEnabled","mozfullscreenchange","mozfullscreenerror"],["msRequestFullscreen","msExitFullscreen","msFullscreenElement","msFullscreenEnabled","MSFullscreenChange","MSFullscreenError"]],n=0,o=r.length,i={};n<o;n++)if((e=r[n])&&e[1]in t){for(n=0;n<e.length;n++)i[r[0][n]]=e[n];return i}return!1}(),o={change:n.fullscreenchange,error:n.fullscreenerror},i={request:function(e,r){return new Promise(function(o,i){var a=function(){this.off("change",a),o()}.bind(this);this.on("change",a);var c=(e=e||t.documentElement)[n.requestFullscreen](r);c instanceof Promise&&c.then(a).catch(i)}.bind(this))},exit:function(){return new Promise(function(e,r){if(this.isFullscreen){var o=function(){this.off("change",o),e()}.bind(this);this.on("change",o);var i=t[n.exitFullscreen]();i instanceof Promise&&i.then(o).catch(r)}else e()}.bind(this))},toggle:function(e,t){return this.isFullscreen?this.exit():this.request(e,t)},onchange:function(e){this.on("change",e)},onerror:function(e){this.on("error",e)},on:function(e,r){var n=o[e];n&&t.addEventListener(n,r,!1)},off:function(e,r){var n=o[e];n&&t.removeEventListener(n,r,!1)},raw:n};n?(Object.defineProperties(i,{isFullscreen:{get:function(){return Boolean(t[n.fullscreenElement])}},element:{enumerable:!0,get:function(){return t[n.fullscreenElement]}},isEnabled:{enumerable:!0,get:function(){return Boolean(t[n.fullscreenEnabled])}}}),r?e.exports=i:window.screenfull=i):r?e.exports={isEnabled:!1}:window.screenfull={isEnabled:!1}}()}},t={};function r(n){var o=t[n];if(void 0!==o)return o.exports;var i=t[n]={exports:{}};return e[n](i,i.exports,r),i.exports}r.n=function(e){var t=e&&e.__esModule?function(){return e.default}:function(){return e};return r.d(t,{a:t}),t},r.d=function(e,t){for(var n in t)r.o(t,n)&&!r.o(e,n)&&Object.defineProperty(e,n,{enumerable:!0,get:t[n]})},r.o=function(e,t){return Object.prototype.hasOwnProperty.call(e,t)},r.r=function(e){"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})},function(){"use strict";r(452),r(353)}()}();