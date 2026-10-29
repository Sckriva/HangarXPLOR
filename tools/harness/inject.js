// Page-world replica of content_scripts/loader.js, used by server.py to inject the extension into the harness page.
// ?src=<folder> is the extension folder relative to the repository root (default: src).
!function() {
  var me = document.currentScript.src;
  var src = new URL(me).searchParams.get('src') || 'src';
  var base = me.replace(/tools\/harness\/inject\.js.*/, '') + src.replace(/\/$/, '') + '/';

  // Replacement for chrome.storage, answering the shim's postMessage protocol.
  // Persisted in localStorage so settings and cache survive reloads, like chrome.storage
  var store = { sync: {}, local: {} };
  try { store = JSON.parse(localStorage.getItem('__hxStore')) || store; } catch (e) {}
  window.__hxStore = store;
  window.addEventListener('message', function(event) {
    if (event.source != window || !event.data || !event.data.type) return;
    var m = /^storage\.(sync|local)\.(get|set|remove|clear)\.request$/.exec(event.data.type);
    if (!m) return;
    var area = store[m[1]], p = event.data.payload, result;
    if (m[2] == 'get') { result = p == null ? JSON.parse(JSON.stringify(area)) : {}; if (p != null) [].concat(typeof p == 'object' && !Array.isArray(p) ? Object.keys(p) : p).forEach(function(k) { if (k in area) result[k] = area[k]; }); }
    if (m[2] == 'set') Object.assign(area, p);
    if (m[2] == 'remove') [].concat(p).forEach(function(k) { delete area[k]; });
    if (m[2] == 'clear') Object.keys(area).forEach(function(k) { delete area[k]; });
    if (m[2] != 'get') localStorage.setItem('__hxStore', JSON.stringify(store));
    setTimeout(function() { window.postMessage({ type: 'storage.' + m[2] + '.response', callbackIndex: event.data.callbackIndex, result: result }, '*'); }, 5);
  });

  var xhr = new XMLHttpRequest();
  xhr.open('GET', base + 'content_scripts/loader.js', false);
  xhr.send();
  // Pull the scripts/styles lists out of the real loader so the test follows any changes to it
  var scripts = eval('(' + /var scripts = (\[[\s\S]*?\]);/.exec(xhr.responseText)[1] + ')');
  var styles = eval('(' + /var styles = (\[[\s\S]*?\]);/.exec(xhr.responseText)[1] + ')');

  styles.forEach(function(s, i) {
    var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = base + s; l.id = 'HangarXPLOR-css-' + i; document.body.appendChild(l);
  });
  var a = document.createElement('script'); a.id = 'HangarXPLOR-ajax-ship-codes-json'; a.type = 'text/x-ajax-url'; a.dataset.ajax = base + 'web_resources/ship-codes.json'; document.body.appendChild(a);

  var i = 0;
  var loadScript = function() {
    if (scripts.length == 0) return;
    var s = document.createElement('script');
    s.id = 'HangarXPLOR-js-' + i++;
    s.src = base + scripts.pop();
    s.onload = loadScript;
    s.onerror = function() { console.error('Failed to load', s.src); };
    document.body.appendChild(s);
  };
  loadScript();
}();
