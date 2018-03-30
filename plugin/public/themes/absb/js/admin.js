if(typeof jQuery==="undefined"){throw new Error("jQuery plugins need to be before this file")}$.AdminBSB={};$.AdminBSB.options={colors:{red:"#F44336",pink:"#E91E63",purple:"#9C27B0",deepPurple:"#673AB7",indigo:"#3F51B5",blue:"#2196F3",lightBlue:"#03A9F4",cyan:"#00BCD4",teal:"#009688",green:"#4CAF50",lightGreen:"#8BC34A",lime:"#CDDC39",yellow:"#ffe821",amber:"#FFC107",orange:"#FF9800",deepOrange:"#FF5722",brown:"#795548",grey:"#9E9E9E",blueGrey:"#607D8B",black:"#000000",white:"#ffffff"},leftSideBar:{scrollColor:"rgba(0,0,0,0.5)",scrollWidth:"4px",scrollAlwaysVisible:false,scrollBorderRadius:"0",scrollRailBorderRadius:"0",scrollActiveItemWhenPageLoad:true,breakpointWidth:1170},dropdownMenu:{effectIn:"fadeIn",effectOut:"fadeOut"}};$.AdminBSB.leftSideBar={activate:function(){var c=this;var b=$("body");var a=$(".overlay");$(window).click(function(f){var d=$(f.target);if(f.target.nodeName.toLowerCase()==="i"){d=$(f.target).parent()}if(!d.hasClass("bars")&&c.isOpen()&&d.parents("#leftsidebar").length===0){if(!d.hasClass("js-right-sidebar")){a.fadeOut()}b.removeClass("overlay-open")}});$.each($(".menu-toggle.toggled"),function(d,e){$(e).next().slideToggle(0)});$.each($(".menu .list li.active"),function(e,f){var d=$(f).find("a:eq(0)");d.addClass("toggled");d.next().show()});$(".menu-toggle").on("click",function(h){var g=$(this);var d=g.next();if($(g.parents("ul")[0]).hasClass("list")){var f=$(h.target).hasClass("menu-toggle")?h.target:$(h.target).parents(".menu-toggle");$.each($(".menu-toggle.toggled").not(f).next(),function(e,j){if($(j).is(":visible")){$(j).prev().toggleClass("toggled");$(j).slideUp()}})}g.toggleClass("toggled");d.slideToggle(320)});c.setMenuHeight();c.checkStatuForResize(true);$(window).resize(function(){c.setMenuHeight();c.checkStatuForResize(false)});Waves.attach(".menu .list a",["waves-block"]);Waves.init()},setMenuHeight:function(b){if(typeof $.fn.slimScroll!="undefined"){var e=$.AdminBSB.options.leftSideBar;var a=($(window).height()-($(".legal").outerHeight()+$(".user-info").outerHeight()+$(".navbar").innerHeight()));var d=$(".list");d.slimscroll({height:a+"px",color:e.scrollColor,size:e.scrollWidth,alwaysVisible:e.scrollAlwaysVisible,borderRadius:e.scrollBorderRadius,railBorderRadius:e.scrollRailBorderRadius});if($.AdminBSB.options.leftSideBar.scrollActiveItemWhenPageLoad){var c=$(".menu .list li.active")[0].offsetTop;if(c>150){d.slimscroll({scrollTo:c+"px"})}}}},checkStatuForResize:function(d){var c=$("body");var a=$(".navbar .navbar-header .bars");var b=c.width();if(d){c.find(".content, .sidebar").addClass("no-animate").delay(1000).queue(function(){$(this).removeClass("no-animate").dequeue()})}if(b<$.AdminBSB.options.leftSideBar.breakpointWidth){c.addClass("ls-closed");a.fadeIn()}else{c.removeClass("ls-closed");a.fadeOut()}},isOpen:function(){return $("body").hasClass("overlay-open")}};$.AdminBSB.slimScrollModal={activate:function(){var c=$.AdminBSB.options.leftSideBar;if(typeof $.fn.slimScroll!="undefined"){var a=($(window).height()-180);var b=$(".modal-scroll");b.slimscroll({height:a+"px",color:c.scrollColor,size:c.scrollWidth,alwaysVisible:c.scrollAlwaysVisible,borderRadius:c.scrollBorderRadius,railBorderRadius:c.scrollRailBorderRadius})}}};$.AdminBSB.rightSideBar={activate:function(){var c=this;var b=$("#rightsidebar");var a=$(".overlay");$(window).click(function(f){var d=$(f.target);if(f.target.nodeName.toLowerCase()==="i"){d=$(f.target).parent()}if(!d.hasClass("js-right-sidebar")&&c.isOpen()&&d.parents("#rightsidebar").length===0){if(!d.hasClass("bars")){a.fadeOut()}b.removeClass("open")}});$(".js-right-sidebar").on("click",function(){b.toggleClass("open");if(c.isOpen()){a.fadeIn()}else{a.fadeOut()}})},isOpen:function(){return $(".right-sidebar").hasClass("open")}};$.AdminBSB.navbar={activate:function(){var b=$("body");var a=$(".overlay");$(".bars").on("click",function(){b.toggleClass("overlay-open");if(b.hasClass("overlay-open")){a.fadeIn()}else{a.fadeOut()}});$('.nav [data-close="true"]').on("click",function(){var c=$(".navbar-toggle").is(":visible");var d=$(".navbar-collapse");if(c){d.slideUp(function(){d.removeClass("in").removeAttr("style")})}});$('.leftnav [data-close="true"]').on("click",function(){var c=$("#leftsidebarin").is(":visible");if(c){b.toggleClass("overlay-open");a.fadeOut()}})}};$.AdminBSB.input={activate:function(){$(".form-control").focus(function(){$(this).parent().addClass("focused")});$(".form-control").focusout(function(){var a=$(this);if(a.parents(".form-group").hasClass("form-float")){if(a.val()==""){a.parents(".form-line").removeClass("focused")}}else{a.parents(".form-line").removeClass("focused")}});$("body").on("click",".form-float .form-line .form-label",function(){$(this).parent().find("input").focus()});$(".form-control").each(function(){if($(this).val()!==""){$(this).parents(".form-line").addClass("focused")}})}};$.AdminBSB.select={activate:function(){if($.fn.selectpicker){$("select:not(.ms, .no-default-select)").selectpicker()}}};$.AdminBSB.dropdownMenu={activate:function(){var a=this;$(".dropdown, .dropup, .btn-group").on({"show.bs.dropdown":function(){var b=a.dropdownEffect(this);a.dropdownEffectStart(b,b.effectIn)},"shown.bs.dropdown":function(){var b=a.dropdownEffect(this);if(b.effectIn&&b.effectOut){a.dropdownEffectEnd(b,function(){})}},"hide.bs.dropdown":function(b){var c=a.dropdownEffect(this);if(c.effectOut){b.preventDefault();a.dropdownEffectStart(c,c.effectOut);a.dropdownEffectEnd(c,function(){c.dropdown.removeClass("open")})}}});Waves.attach(".dropdown-menu li a",["waves-block"]);Waves.init()},dropdownEffect:function(f){var e=$.AdminBSB.options.dropdownMenu.effectIn,d=$.AdminBSB.options.dropdownMenu.effectOut;var g=$(f),a=$(".dropdown-menu",f);if(g.length>0){var b=g.data("effect-in");var c=g.data("effect-out");if(b!==undefined){e=b}if(c!==undefined){d=c}}return{target:f,dropdown:g,dropdownMenu:a,effectIn:e,effectOut:d}},dropdownEffectStart:function(b,a){if(a){b.dropdown.addClass("dropdown-animating");b.dropdownMenu.addClass("animated dropdown-animated");b.dropdownMenu.addClass(a)}},dropdownEffectEnd:function(b,c){var a="webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend";b.dropdown.one(a,function(){b.dropdown.removeClass("dropdown-animating");b.dropdownMenu.removeClass("animated dropdown-animated");b.dropdownMenu.removeClass(b.effectIn);b.dropdownMenu.removeClass(b.effectOut);if(typeof c=="function"){c()}})}};var edge="Microsoft Edge";var ie10="Internet Explorer 10";var ie11="Internet Explorer 11";var opera="Opera";var firefox="Mozilla Firefox";var chrome="Google Chrome";var safari="Safari";$.AdminBSB.browser={activate:function(){var b=this;var a=b.getClassName();if(a!==""){$("html").addClass(b.getClassName())}},getBrowser:function(){var a=navigator.userAgent.toLowerCase();if(/edge/i.test(a)){return edge}else{if(/rv:11/i.test(a)){return ie11}else{if(/msie 10/i.test(a)){return ie10}else{if(/opr/i.test(a)){return opera}else{if(/chrome/i.test(a)){return chrome}else{if(/firefox/i.test(a)){return firefox}else{if(!!navigator.userAgent.match(/Version\/[\d\.]+.*Safari/)){return safari}}}}}}}return undefined},getClassName:function(){var a=this.getBrowser();if(a===edge){return"edge"}else{if(a===ie11){return"ie11"}else{if(a===ie10){return"ie10"}else{if(a===opera){return"opera"}else{if(a===chrome){return"chrome"}else{if(a===firefox){return"firefox"}else{if(a===safari){return"safari"}else{return""}}}}}}}}};$(function(){$.AdminBSB.browser.activate();$.AdminBSB.leftSideBar.activate();$.AdminBSB.rightSideBar.activate();$.AdminBSB.navbar.activate();$.AdminBSB.dropdownMenu.activate();$.AdminBSB.input.activate();$.AdminBSB.select.activate();setTimeout(function(){$(".page-loader-wrapper").fadeOut()},50);var a=false;if(/(android|bb\d+|meego).+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|ipad|iris|kindle|Android|Silk|lge |maemo|midp|mmp|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino/i.test(navigator.userAgent)||/1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i.test(navigator.userAgent.substr(0,4))){a=true}if(!a){$.AdminBSB.slimScrollModal.activate()}});