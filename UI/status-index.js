// SPDX-License-Identifier: Apache-2.0
// Based on ImmortalWrt LuCI status/index; independently load status cards.
'use strict';
'require view';
'require dom';
'require poll';
'require fs';
'require network';
'require ui';

return view.extend({
	handleToggleSection: function(include, container, ev) {
		var btn = ev.currentTarget;

		include.hide = !include.hide;

		btn.setAttribute('data-style', include.hide ? 'active' : 'inactive');
		btn.setAttribute('class', include.hide ? 'label notice' : 'label');
		btn.firstChild.data = include.hide ? _('Show') : _('Hide');
		btn.blur();

		container.style.display = include.hide ? 'none' : 'block';

		if (include.hide) {
			localStorage.setItem(include.id, 'hide');
		} else {
			dom.content(container,
				E('p', {}, E('em', { 'class': 'spinning' },
					[ _('Collecting data...') ])
				)
			);

			localStorage.removeItem(include.id);
		}
	},

	// XG2010G independent overview cards: a pending RPC never holds the whole view.
	poll_status: function(includes, containers, first_load) {
		if (!containers.length || !containers[0].isConnected)
			return;

		// Refresh the shared network cache once, but do not gate unrelated cards on it.
		if (!this.cacheRefresh) {
			this.cacheRefresh = Promise.resolve().then(function() {
				return network.flushCache();
			}).catch(function() {}).finally(L.bind(function() {
				this.cacheRefresh = null;
			}, this));
		}

		includes.forEach(function(include, i) {
			var container = containers[i];
			if ((include.hide && !first_load) || include.pending)
				return;

			// Keep a single actual request in flight, including after the local notice timer.
			// Releasing the guard on timeout would accumulate RPCs on an unresponsive router.
			include.pending = true;
			var timer = window.setTimeout(function() {
				if (container.isConnected && !include.ready && !include.hide)
					dom.content(container, E('p', {}, _('Waiting for data...')));
			}, 10000);

			Promise.resolve().then(function() {
				return typeof(include.load) == 'function' ? include.load() : null;
			}).then(function(result) {
				if (!container.isConnected)
					return;
				var content = typeof(include.render) == 'function'
					? include.render(result) : include.content;
				if (typeof(include.oneshot) == 'function') {
					include.oneshot(result);
					include.oneshot = null;
				}
				include.ready = true;
				container.parentNode.style.display = content != null ? '' : 'none';
				if (content != null && !include.hide)
					dom.content(container, content);
			}).catch(function(error) {
				// Only this card fails; allow a retry on the next poll and retain existing data.
				if (container.isConnected && !include.ready && !include.hide)
					dom.content(container, E('p', {}, _('RPC call failed')));
				console.warn('Status card failed:', include.id, error);
			}).finally(function() {
				window.clearTimeout(timer);
				include.pending = false;
			});
		});

		var ssi = document.querySelector('div.includes');
		if (ssi) {
			ssi.style.display = '';
			ssi.classList.add('fade-in');
		}
	},

	load: function() {
		return L.resolveDefault(fs.list('/www' + L.resource('view/status/include')), []).then(function(entries) {
			return Promise.all(entries.filter(function(e) {
				return (e.type == 'file' && e.name.match(/\.js$/));
			}).map(function(e) {
				return 'view.status.include.' + e.name.replace(/\.js$/, '');
			}).sort().map(function(n) {
				return L.require(n).catch(function(error) {
					console.warn('Status include unavailable:', n, error);
					return null;
				});
			})).then(function(includes) {
				return includes.filter(function(include) { return include != null; });
			});
		});
	},

	render: function(includes) {
		var rv = E([]), containers = [];

		for (var i = 0; i < includes.length; i++) {
			var title = null;

			if (includes[i].title != null)
				title = includes[i].title;
			else
				title = String(includes[i]).replace(/^\[ViewStatusInclude\d+_(.+)Class\]$/,
					function(m, n) { return n.replace(/(^|_)(.)/g,
						function(m, s, c) { return (s ? ' ' : '') + c.toUpperCase() })
					});

			includes[i].id = title;
			includes[i].hide = localStorage.getItem(includes[i].id) == 'hide';

			includes[i].pending = false;
			includes[i].ready = false;
			var container = E('div', { 'style': includes[i].hide ? 'display: none' : '' },
				E('p', {}, E('em', { 'class': 'spinning' }, _('Collecting data...'))));

			rv.appendChild(E('div', { 'class': 'cbi-section' }, [
				E('div', { 'class': 'cbi-title' },[
					E('h3', { 'style': 'display: flex; justify-content: space-between' }, [
						title || '-',
						E('span', {
							'class': includes[i].hide ? 'label notice' : 'label',
							'role': 'button',
							'style': 'display: flex; align-items: center; justify-content: center; min-width: 4em',
							'data-style': includes[i].hide ? 'active' : 'inactive',
							'data-indicator': 'poll-status',
							'data-clickable': 'true',
							'click': ui.createHandlerFn(this, 'handleToggleSection',
										    includes[i], container)
						}, [ _(includes[i].hide ? 'Show' : 'Hide') ])
					]),
				]),
				container
			]));

			containers.push(container);
		}

		// Return the skeleton synchronously; start work after LuCI attaches it to the DOM.
		window.setTimeout(L.bind(function() {
			this.poll_status(includes, containers, true);
			poll.add(L.bind(this.poll_status, this, includes, containers));
		}, this), 0);
		return rv;
	},

	handleSaveApply: null,
	handleSave: null,
	handleReset: null
});
