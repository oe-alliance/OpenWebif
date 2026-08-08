// TODO minimize js

var isSecure = (window.location.protocol == 'https:');

var PlayerObj = function () {
	var self;
	var _hls = null;
	var _video = null;
	return {
		setup: function (auth, streamingport, live555HlsBase, strings) {
			self = this;
			self.auth = auth;
			self.streamingport = streamingport;
			self.live555HlsBase = live555HlsBase || '';
			self.activeLive555Url = '';
			self.pendingStop = null;
			self.switchRequest = 0;
			self.hlsSession = 0;
			self.playRequested = false;
			self.nativeLiveMonitorGeneration = 0;
			self.nativeLiveMonitorTimer = null;
			self.nativeLiveMonitorRequest = null;
			self.strings = strings || {};
			self.pl = GetLSValue('webtvplayerl', 'hls');
			self.pr = GetLSValue('webtvplayerr', 'hls');
			self.folderoptions = '';
			self.dn = '';

			_video = document.getElementById('hlsPlayer');

			$('#sbtn0').click(function () {
				++self.switchRequest;
				self.stop();
				$('#streambouquets_chosen').css('display', 'inline-block');
				$('#streamchannels_chosen').css('display', 'inline-block');
				$('#streamrecordings_chosen').css('display', 'none');
				$('#moviesort-button').hide();
				self.currentp = self.pl;
			});
			$('#sbtn1').click(function () {
				++self.switchRequest;
				self.stop();
				$('#streambouquets_chosen').css('display', 'none');
				$('#streamrecordings_chosen').css('display', 'inline-block');
				$('#streamchannels_chosen').css('display', 'none');
				$('#moviesort-button').show();
				self.currentp = self.pr;
			});
$("#srcbuttons").buttonset();
			$("#streambouquets").chosen({disable_search_threshold: 5, no_results_text: "Oops, nothing found!", width: "200px"});
			$("#streambouquets").chosen().change(function () {
				self.loadBouquet($("#streambouquets").val());
			});
			$("#streamchannels").chosen({disable_search_threshold: 10, no_results_text: "Oops, nothing found!", width: "400px"});
			$("#streamchannels").chosen().change(function () {
				var sref = $("#streamchannels").val();
				var name = $("#streamchannels option:selected").text();
				var iptvurl = $("#streamchannels option:selected").attr('data-iptvurl') || '';
				self.afterStop(function (switchRequest) {
					if (iptvurl) {
						self.loadUrl(iptvurl, iptvurl.indexOf('.m3u8') !== -1);
						self.play();
					} else {
						self.startLiveChannel(sref, name, switchRequest);
					}
				});
			});

			$("#streamrecordings").chosen({disable_search_threshold: 10, no_results_text: "Oops, nothing found!", width: "400px"});
			$("#streamrecordings").chosen().change(function () {
				var ref = $("#streamrecordings").val();
				var name = $("#streamrecordings option:selected").text();
				if (ref !== '') {
					if (ref === name) {
						$("#streamrecordings").empty();
						$('#streamrecordings').trigger("chosen:updated");
						$("#moviesort-button .ui-selectmenu-text .sortimg").empty();
						self.getRecordings(ref, function () {
							$('#streamrecordings').trigger("chosen:updated");
						});
					} else {
						self.afterStop(function () {
							self.setUrl(ref, name);
							self.play();
						});
					}
				}
			});

			$('.chosen-container .chosen-drop').addClass('ui-widget-content');
			if (theme === 'eggplant' || theme === 'vader') {
				$('.chosen-container .chosen-drop').css('background-image', 'none');
			}

			$('#btnstop').click(function () {
				++self.switchRequest;
				self.stop();
				$(this).blur();
			});

			$('#wzapstream').prop('checked', GetLSValue('webtvzapstream', false));
			$('#wzapstream').click(function () {
				SetLSValue('webtvzapstream', $('#wzapstream').is(':checked'));
				$(this).blur();
			});

			$('#streamchannels_chosen').css('display', 'inline-block');
			$('#streamrecordings_chosen').css('display', 'none');

$.widget("custom.iconselectmenu", $.ui.selectmenu, {
				_renderItem: function (ul, item) {
					var li = $("<li>"),
						wrapper = $("<div>", {text: item.label}).prepend(
							$("<span class='sortimg'>").append(
								$("<i>", {"class": "fa " + item.element.data("class")})
							)
						);
					return li.append(wrapper).appendTo(ul);
				}
			});

			var ms = GetLSValue('webtvms', 'name');
			$('#moviesort').val(ms).change();
			$('#moviesort').iconselectmenu({
				change: function (event, ui) {
					$("#streamrecordings").empty();
					SetLSValue('webtvms', ui.item.value);
					self.SortMovies();
				}
			}).addClass('ui-menu-icons');

			$('#moviesort-button').hide();
			$('#moviesort-button').css('margin-left', '10px');
			$('#btnstop').button();
			$('#wzapstream').checkboxradio();
			$("#srcbuttons").buttonset();

			self.getRecordings('', function () {
				$('#streamrecordings').trigger("chosen:updated");
			});

			if (isSecure) {
				$('#srcbuttons').hide();
				$('#sbtn1').trigger("click");
			} else {
				self.loadBouquets();
			}

		}, afterStop: function (callback) {
			var switchRequest = ++self.switchRequest;
			var stopRequest = self.stop();
			stopRequest.done(function () {
				if (switchRequest === self.switchRequest) callback(switchRequest);
			});
			stopRequest.fail(function (xhr, status, error) {
				if (window.console) console.warn('Unable to release Live555 HLS source', status, error);
			});

		}, startLiveChannel: function (sref, name, switchRequest) {
			if ($('#wzapstream').is(':checked')) {
				self.zapAndPlay(sref, name, switchRequest);
				return;
			}
			$.ajax({
				url: '/api/serviceplayable',
				dataType: 'json',
				cache: false,
				data: { sRef: sref, sRefPlaying: current_ref || '' },
				success: function (data) {
					if (switchRequest !== self.switchRequest) return;
					if (data.service && data.service.isplayable) {
						self.setUrl(sref, name, true);
						self.play();
					} else {
						self.confirmZapAndPlay(sref, name, switchRequest);
					}
				}
			});

		}, zapAndPlay: function (sref, name, switchRequest) {
			$.ajax({
				url: '/api/zap',
				dataType: 'json',
				cache: false,
				data: { sRef: sref, title: name },
				success: function () {
					if (switchRequest !== self.switchRequest) return;
					self.setUrl(sref, name, true);
					self.play();
				}
			});

		}, confirmZapAndPlay: function (sref, name, switchRequest) {
			var strings = self.strings;

			if (!$('#modaldialog').length) {
				if (confirm(strings.notunerfree + ' ' + strings.switchchannelquestion)) self.zapAndPlay(sref, name, switchRequest);
				return;
			}

			var buttons = {};
			buttons[strings.yes] = function () {
				$(this).dialog('close');
				self.zapAndPlay(sref, name, switchRequest);
			};
			buttons[strings.no] = function () {
				$(this).dialog('close');
			};
			$('#modaldialog').empty().append($('<p>').text(strings.switchchannelquestion)).dialog({
				modal: true,
				title: strings.notunerfree,
				autoOpen: true,
				width: 'auto',
				buttons: buttons,
				close: function () {
					$(this).dialog('destroy');
					$(this).empty();
				}
			});

		}, setUrl: function (sref, name, live) {
			try {
				if (!live) {
					var fn = sref.split('/').reverse()[0];
					var path = encodeURIComponent(sref.substring(0, sref.length - fn.length));
					fn = fn.replace(/___/g, "'");
					var base = window.location.protocol + '//' + self.auth + window.location.hostname;
					if (window.location.port !== '')
						base += ':' + window.location.port;
					self.loadUrl(base + '/file?file=' + path + escape(fn), false);
				} else if (self.live555HlsBase) {
					self.loadUrl(self.live555HlsBase + '?ref=' + encodeURIComponent(sref), true);
				} else {
					self.loadUrl('http://' + self.auth + window.location.hostname + ':' + self.streamingport + '/' + sref, false);
				}
			} catch (e) { }

		}, loadUrl: function (url, isHls) {
			var isLive555Hls = isHls && self.live555HlsBase &&
				url.indexOf(self.live555HlsBase) === 0;
			if (isLive555Hls) {
				url = self.withNewWebTvSession(url);
			}
			self.stopNativeLiveMonitor();
			self.playRequested = false;
			if (_hls) {
				_hls.destroy();
				_hls = null;
			}
			_video.oncanplay = null;
			_video.pause();
			_video.removeAttribute('src');
			_video.load();
			self.activeLive555Url = isLive555Hls ? url : '';

			if (isHls) {
				var hlsJsSupported = typeof Hls !== 'undefined' && Hls.isSupported();
				var nativeHlsSupported = !!_video.canPlayType('application/vnd.apple.mpegurl');
				var userAgent = navigator.userAgent || '';
				var isGoogleChrome = /(?:Chrome|Chromium)\//.test(userAgent) &&
					!/(?:Edg|Vivaldi|OPR|SamsungBrowser)\//.test(userAgent);
				var isAppleSafari = /Safari\//.test(userAgent) &&
					!/(?:Chrome|Chromium|CriOS|Edg|EdgiOS|EdgA|FxiOS|OPR|Vivaldi|SamsungBrowser)\//.test(userAgent);
				var needsNativeLiveRefresh = isLive555Hls &&
					(isGoogleChrome || isAppleSafari);
				var preferNativeHls = nativeHlsSupported &&
					(!hlsJsSupported || needsNativeLiveRefresh);
				if (window.console)
					console.info('WebTV HLS backend: ' + (preferNativeHls ? 'native' : 'hls.js'));
				if (preferNativeHls) {
					_video.oncanplay = function () {
						if (self.playRequested) self.startPlayback();
					};
					_video.src = url;
					if (needsNativeLiveRefresh)
						self.startNativeLiveMonitor(url);
				} else if (hlsJsSupported) {
					var hls = new Hls();
					_hls = hls;
					hls.on(Hls.Events.MEDIA_ATTACHED, function () {
						if (_hls === hls) hls.loadSource(url);
					});
					hls.on(Hls.Events.MANIFEST_PARSED, function () {
						if (_hls === hls && self.playRequested) self.startPlayback();
					});
					hls.on(Hls.Events.ERROR, function (event, data) {
						if (_hls !== hls || !data.fatal) return;
						if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
							hls.startLoad();
						} else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
							hls.recoverMediaError();
						} else {
							if (window.console) console.error('Fatal HLS playback error', data);
							hls.destroy();
							if (_hls === hls) _hls = null;
						}
					});
					hls.attachMedia(_video);
				} else if (nativeHlsSupported) {
					_video.oncanplay = function () {
						if (self.playRequested) self.startPlayback();
					};
					_video.src = url;
				}
			} else {
				_video.src = url;
			}

		}, withNewWebTvSession: function (url) {
			++self.hlsSession;
			var session = new Date().getTime() + '-' + self.hlsSession;
			if (/[?&]webtv_session=/.test(url))
				return url.replace(/([?&]webtv_session=)[^&#]*/, '$1' + session);
			return url + (url.indexOf('?') === -1 ? '?' : '&') +
				'webtv_session=' + session;

		}, startNativeLiveMonitor: function (url) {
			self.stopNativeLiveMonitor();
			var generation = self.nativeLiveMonitorGeneration;
			var startedAt = new Date().getTime();
			var poll = function () {
				if (generation !== self.nativeLiveMonitorGeneration ||
					self.activeLive555Url !== url || !self.playRequested) return;
				var request = $.ajax({
					url: url,
					type: 'GET',
					dataType: 'text',
					crossDomain: true,
					timeout: 3000
				});
				self.nativeLiveMonitorRequest = request;
				request.done(function (playlist) {
					if (generation !== self.nativeLiveMonitorGeneration ||
						self.activeLive555Url !== url || typeof playlist !== 'string') return;
					var liveSegments = (playlist.match(/^#EXTINF:/gm) || []).length;
					if (liveSegments >= 4 && playlist.indexOf('-bootstrap-') === -1) {
						self.reloadNativeLiveHls(url, generation, liveSegments);
					}
				});
				request.always(function () {
					if (self.nativeLiveMonitorRequest === request)
						self.nativeLiveMonitorRequest = null;
					if (generation === self.nativeLiveMonitorGeneration &&
						self.activeLive555Url === url &&
						new Date().getTime() - startedAt < 60000) {
						self.nativeLiveMonitorTimer = window.setTimeout(poll, 1000);
					}
				});
			};
			self.nativeLiveMonitorTimer = window.setTimeout(poll, 1000);

		}, reloadNativeLiveHls: function (url, generation, liveSegments) {
			if (generation !== self.nativeLiveMonitorGeneration ||
				self.activeLive555Url !== url) return;
			if (window.console)
				console.info('Native HLS live playlist stable (' + liveSegments +
					' segments); rebuilding media element');
			self.stopNativeLiveMonitor();
			var refreshedUrl = self.withNewWebTvSession(url);
			self.activeLive555Url = refreshedUrl;
			var oldVideo = _video;
			var volume = oldVideo.volume;
			var muted = oldVideo.muted;
			var playbackRate = oldVideo.playbackRate;
			oldVideo.oncanplay = null;
			oldVideo.pause();
			oldVideo.removeAttribute('src');
			oldVideo.load();

			var newVideo = oldVideo.cloneNode(false);
			newVideo.volume = volume;
			newVideo.muted = muted;
			newVideo.playbackRate = playbackRate;
			oldVideo.parentNode.replaceChild(newVideo, oldVideo);
			_video = newVideo;
			_video.oncanplay = function () {
				if (self.playRequested) self.startPlayback();
			};
			_video.src = refreshedUrl;
			_video.load();
			self.startPlayback();

		}, stopNativeLiveMonitor: function () {
			++self.nativeLiveMonitorGeneration;
			if (self.nativeLiveMonitorTimer) {
				window.clearTimeout(self.nativeLiveMonitorTimer);
				self.nativeLiveMonitorTimer = null;
			}
			var request = self.nativeLiveMonitorRequest;
			self.nativeLiveMonitorRequest = null;
			if (request) request.abort();

		}, stop: function () {
			self.stopNativeLiveMonitor();
			var stopUrl = self.activeLive555Url;
			self.activeLive555Url = '';
			self.playRequested = false;
			if (_hls) {
				_hls.stopLoad();
				_hls.destroy();
				_hls = null;
			}
			_video.oncanplay = null;
			_video.pause();
			_video.removeAttribute('src');
			_video.load();

			if (!stopUrl) {
				if (self.pendingStop) return self.pendingStop;
				return $.Deferred().resolve().promise();
			}

			var stopRequest = $.ajax({
				url: stopUrl,
				type: 'DELETE',
				crossDomain: true,
				timeout: 7000
			});
			self.pendingStop = stopRequest;
			stopRequest.fail(function () {
				if (!self.activeLive555Url) self.activeLive555Url = stopUrl;
			});
			stopRequest.always(function () {
				if (self.pendingStop === stopRequest) self.pendingStop = null;
			});
			return stopRequest;

		}, play: function () {
			self.playRequested = true;
			self.startPlayback();

		}, startPlayback: function () {
			if (!_video || !self.playRequested) return;
			var playPromise = _video.play();
			if (playPromise && typeof playPromise.catch === 'function') {
				playPromise.catch(function (error) {
					if (error.name !== 'AbortError' && window.console)
						console.warn('Unable to start WebTV playback', error);
				});
			}

		}, SortMovies: function () {
			var idx = GetLSValue('webtvms', 'name');
			var _mv = MLHelper.SortMovies(idx).slice();
			var options = self.folderoptions;
			var items = [];
			for (var i = 0, len = _mv.length; i < len; i++) {
				items.push("<option value='" + _mv[i].fn + "'>" + _mv[i].title + "&nbsp;/&nbsp;" + _mv[i].bt + "</option>");
			}
			options += "<optgroup label='" + self.dn + "'>" + items.join("") + "</optgroup>";
			$("#streamrecordings").append(options);
			$('#streamrecordings').trigger("chosen:updated");

		}, loadBouquets: function () {
			$.ajax({
				url: '/api/bouquets',
				dataType: 'json',
				cache: false,
				success: function (data) {
					var options = '';
					var lastBouquet = GetLSValue('webtvbouquet', '');
					$.each(data.bouquets, function (i, b) {
						var sref = b[0], name = b[1];
						var sel = (sref === lastBouquet) ? ' selected' : '';
						options += "<option value='" + sref + "'" + sel + ">" + name + "</option>";
					});
					$("#streambouquets").append(options);
					$('#streambouquets').trigger("chosen:updated");
					var sref = $("#streambouquets").val();
					if (sref) self.loadBouquet(sref);
				}
			});

		}, loadBouquet: function (sref) {
			SetLSValue('webtvbouquet', sref);
			$.ajax({
				url: '/api/servicelistplayable',
				dataType: 'json',
				cache: false,
				data: { sRef: sref, sRefPlaying: current_ref || '', includeName: 1 },
				success: function (data) {
					$("#streamchannels").empty();
					var options = "<option value=''></option>";
					$.each(data.services, function (i, s) {
						var iptvattr = s.iptvurl ? ' data-iptvurl="' + s.iptvurl.replace(/"/g, '&quot;') + '"' : '';
						options += "<option value='" + s.servicereference + "'" + iptvattr + ">" + s.servicename + "</option>";
					});
					$("#streamchannels").append(options);
					if (current_ref) $("#streamchannels").val(current_ref);
					$('#streamchannels').trigger("chosen:updated");
					if (current_ref && $("#streamchannels").val() === current_ref) {
						var iptvurl = $("#streamchannels option:selected").attr('data-iptvurl') || '';
						if (iptvurl) {
							self.loadUrl(iptvurl, iptvurl.indexOf('.m3u8') !== -1);
						} else {
							self.setUrl(current_ref, current_name, true);
						}
						self.play();
					}
				}
			});

		}, getRecordings: function (_dirname, callback) {
			var rdata = {fields: 'f'};
			if (_dirname !== '')
				rdata = {dirname: _dirname, fields: 'f'};
			$.ajax({
				url: '/api/movielist',
				dataType: 'json',
				cache: false,
				data: rdata,
				success: function (data) {
					var mv = data['movies'];
					self.dn = data['directory'];
					var subdirs = data['bookmarks'];
					var lastdir = '';
					var dira = self.dn.split('/');
					var options = '';
					if (dira.length > 1) {
						for (var i = 0; i < dira.length - 2; i++) {
							lastdir += dira[i] + '/';
						}
					}
					if (lastdir !== '') {
						options = "<optgroup label='Folders'>";
						options += "<option value='' disabled selected style='display:none;'></option>";
						options += "<option value='" + lastdir + "'>" + lastdir + "</option>";
						for (var j = 0; j < subdirs.length; j++) {
							options += "<option value='" + self.dn + subdirs[j] + "'>" + self.dn + subdirs[j] + "</option>";
						}
						options += "</optgroup>";
					}
					self.folderoptions = options;
					var _mv = [];
					$.each(mv, function (key, val) {
						var _fn = val['filename'].replace(/'/g, '___');
						_mv.push({title: val['eventname'], bt: val['begintime'], start: val['recordingtime'], fn: _fn});
					});
					MLHelper.SetMovies(_mv);
					self.SortMovies();
					callback();
				}
			});
		}
	}
};
