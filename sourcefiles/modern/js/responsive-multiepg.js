var reloadTimers = false;
if (multiepg_mode == 2) {
	let opena = multiepg_first;
	let openb = multiepg_now;
	let pos = (openb - opena);

	if (pos > 0) {
		pos = pos / 6;
	}

	if (multiepg_day == 0) {
		jQuery(".timetable-now").css('left', 151 + pos);

		setTimeout(function () {
			let nowdate = Math.round(+new Date() / 1000);
			let pos = (nowdate - opena);

			if (pos > 0)
				pos = pos / 6;
			jQuery(".timetable-now").css('left', 151 + pos);
		}, 10000);

		jQuery(".timetable-now").css('height', jQuery("#tblinner").height());
	} else {
		jQuery(".timetable-now").css('height', '0');
	}
}

function getScrollBarWidth() {
  let outer = jQuery('<div>').css({
      visibility: 'hidden',
      width: 100,
      overflow: 'scroll'
    }).appendTo('body'),
    widthWithScroll = jQuery('<div>').css({
      width: '100%'
    }).appendTo(outer).outerWidth();

  outer.remove();

  return 100 - widthWithScroll;
}

function fixTableHeight() {
  let addScrollBarWidth = scrollBarWidth;

  if (jQuery('#tbl1').width() <= jQuery("#tvcontent").width()) {
    addScrollBarWidth = 0;
  }

	if (multiepg_mode == 1) {
		let new_height = (jQuery("#epgcard").height() * 0.85 - jQuery("#epgcardheaderI").height() - jQuery("#epgcardheaderII").height() - jQuery("#navepg").height() - 2 * jQuery("#tbl1 thead").height() - addScrollBarWidth - 2);
		let scrollwidth = (jQuery("#epgcard").width() - 40) + "px";
		let scrollheightI = new_height + 'px';

		jQuery("#tbl1body").height(new_height + "px");
		jQuery('#tbl1body').height(scrollheightI);
		jQuery('#fulltbl').width(scrollwidth);
		jQuery("#fulltbl").height((jQuery("#leftsidemenu").height() - 300) + "px");
	} else {
		let new_height = (jQuery("#epgcard").height() * 0.90 - jQuery("#epgcardheaderI").height() - jQuery("#epgcardheaderII").height() - jQuery("#navepg").height() - 2 * jQuery("#tbl1 thead").height() - addScrollBarWidth - 2);
		let scrollheightI = new_height + 'px';
		let scrollwidth = (jQuery("#epgcard").width() - 40) + "px";

		jQuery('#fulltbl').height(scrollheightI);
		jQuery('#tblinner').width(scrollwidth);
	}
}

var scrollBarWidth = getScrollBarWidth();
fixTableHeight();

jQuery(window).resize(function () {
  fixTableHeight();
});

jQuery(".bq").click(function () {
  let id = jQuery(this).data("ref");

  jQuery("#tvcontent").html(loadspinner).load('ajax/multiepg?bref=' + id + '&day=' + multiepg_day + '&epgmode=' + multiepg_epgmode);
  SetLSValue("lastmbq_" + multiepg_epgmode, id);
});

if (multiepg_mode == 1) {
	jQuery(".service").click(function () {
		let ref = jQuery(this).data("ref");

		if (ref != undefined) {
			zapChannel(ref, '');
		}
	});
}

jQuery(".plusclick").click(function () {
  let day = jQuery(this).data("day");

  if (day != undefined) {
    if (day > 999) {
      let w = day - 1000;

      jQuery("#tvcontent").html(loadspinner).load('ajax/multiepg?bref=' + multiepg_bref + '&day=' + multiepg_day + '&epgmode=' + multiepg_epgmode + '&week=' + w);
    } else if (day > 199) {
      let d = day - 200;
      let dt = (d == 0) ? '' : jQuery(this).html();
      let pos = 0;

      jQuery('#tblinner').scrollLeft(0);
      jQuery("#timescroller li ol .event").each(function () {
        if (pos == 0) {
          if (jQuery(this).data("dt") == dt) {
            if (jQuery(this).position() != undefined)
              pos = jQuery(this).position().left;
          }
        }
      });

      if (d == '') {
        let l = jQuery(".timetable-now").css('left');

        pos = parseInt(l.replace('px', ''));
      }

      if (pos > 0) {
        pos -= 200;

        jQuery('#tbl1body').animate({
          scrollLeft: pos
        }, 500);
      }
    } else if (day > 100) {
      let mode = day - 100;

      if (mode != multiepg_mode) {
        jQuery.ajax({
          url: 'api/setwebconfig?mepgmode=' + mode,
          success: function (data) {
            jQuery("#tvcontent").html(loadspinner).load('ajax/multiepg?bref=' + multiepg_bref + '&day=' + multiepg_day + '&epgmode=' + multiepg_epgmode + '&week=' + multiepg_week);
          }
        });
      }
    } else {
      jQuery("#tvcontent").html(loadspinner).load('ajax/multiepg?bref=' + multiepg_bref + '&day=' + day + '&epgmode=' + multiepg_epgmode + '&week=' + multiepg_week);
    }
  } else {
    let epgmode = jQuery(this).data("tvradio");

    if (epgmode != undefined) {
      jQuery("#tvcontent").html(loadspinner).load('ajax/multiepg?day=' + day + '&epgmode=' + multiepg_epgmode);
    }
  }
});

if (jQuery("#header").is(':hidden')) {
  jQuery('#compressmepg').show();
  jQuery('#refreshmepg2').show();
}

if (mepgdirect == 1) {
  mepgdirect = 0; //NOSONAR
  jQuery("#expandmepg").click();
}

jQuery(".togglescroll").click(function () {
  if (jQuery('#tblinner').css('overflow-y') == 'hidden') {
    jQuery('#tblinner').css('overflow-y', '');
    jQuery('.togglescroll').removeClass('ui-widget-header');
    SetLSValue('MultiEPGScrollStyle', '1');
  } else {
    jQuery('#tblinner').css('overflow-y', 'hidden');
    jQuery('.togglescroll').addClass('ui-widget-header');
    SetLSValue('MultiEPGScrollStyle', '0');
  }
});

if (multiepg_mode == 2) {
	jQuery(function () {
		if (GetLSValue('MultiEPGScrollStyle', '0') == '0') {
			jQuery('#tblinner').css('overflow-y', 'hidden');
			jQuery('.togglescroll').addClass('ui-widget-header');
		} else {
			jQuery('#tblinner').css('overflow-y', '');
			jQuery('.togglescroll').removeClass('ui-widget-header');
		}
	});
}

console.log('x');