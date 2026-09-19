var reloadTimers = false;
if (multiepg_mode == 2) {
	let opena = multiepg_first;
	let openb = multiepg_now;
	let pos = (openb - opena);

	if (pos > 0) {
		pos = pos / 6;
	}

	if (multiepg_day == 0) {
		jQuery(".timetable-now").css('left', (140 + pos) + 'px');

		setTimeout(function () {
			let nowdate = Math.round(+new Date() / 1000);
			let pos = (nowdate - opena);

			if (pos > 0)
				pos = pos / 6;
			jQuery(".timetable-now").css('left', (140 + pos) + 'px');
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
		let new_height = (jQuery("#epgcard").height() * 0.90 - jQuery("#epgcardheaderI").height() - jQuery("#epgcardheaderII").height() - jQuery("#navepg").height() - addScrollBarWidth - 2);
		let scrollwidth = (jQuery("#epgcard").width() - 40) + "px";
		let scrollheightI = new_height + 'px';

		jQuery('#fulltbl').height(scrollheightI);
		jQuery('#fulltbl').width(scrollwidth);
	} else {
		let new_height = (jQuery("#epgcard").height() * 0.90 - jQuery("#epgcardheaderI").height() - jQuery("#epgcardheaderII").height() - jQuery("#navepg").height() - addScrollBarWidth - 2);
		let scrollheightI = new_height + 'px';
		let scrollwidth = (jQuery("#epgcard").width() - 40) + "px";

		jQuery('#fulltbl').height(scrollheightI);
		jQuery('#fulltbl').width(scrollwidth);
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
      let pos = 0;

      if (d == 0 || d == '') {
        let l = jQuery(".timetable-now").css('left');
        pos = Number.parseInt(l.replace('px', ''), 10) || 0;
      } else if (d == 1) {
        pos = 140 + (6 * 3600 / 6);
      } else if (d == 2) {
        pos = 140 + (12 * 3600 / 6);
      } else if (d == 3) {
        pos = 140 + (20 * 3600 / 6);
      }

      if (pos > 0) {
        pos -= 160;

        jQuery('#fulltbl').animate({
          scrollLeft: Math.max(0, pos)
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

console.log('x');