(function () {
  var tree = window.SITE_TREE;
  if (!tree) return;

  var me = document.currentScript;
  var base = new URL('../', me.src).href;
  var here = location.href.split('#')[0].split('?')[0];

  var css = `
  .snav, .snav * { box-sizing: border-box; }
  .snav { position: fixed; top: 0; left: 0; bottom: 0; width: 280px; z-index: 900;
    background: #ebe4d6; border-right: 1px solid #c9bfa9; overflow-y: auto;
    font: 400 13px/1.45 'IBM Plex Sans', system-ui, sans-serif; color: #1a1a1a;
    padding: 14px 10px 40px; transition: transform .2s; }
  .snav.closed { transform: translateX(-100%); }
  .snav-head { display: flex; align-items: center; justify-content: space-between; margin: 0 4px 10px; }
  .snav-title { font: 500 10px 'IBM Plex Mono', monospace; letter-spacing: 2px; text-transform: uppercase; color: #8b1a1a; }
  .snav input { width: 100%; padding: 6px 9px; margin-bottom: 10px; border: 1px solid #c9bfa9;
    background: #f4efe6; border-radius: 3px; font: inherit; color: inherit; }
  .snav details { margin: 0; }
  .snav summary { cursor: pointer; padding: 4px 6px; border-radius: 3px; list-style: none; font-weight: 500; color: #3a3a3a; }
  .snav summary::-webkit-details-marker { display: none; }
  .snav summary::before { content: '▸'; display: inline-block; width: 14px; color: #6b6357; transition: transform .12s; }
  .snav details[open] > summary::before { transform: rotate(90deg); }
  .snav summary:hover, .snav a:hover { background: #e2d9c4; }
  .snav .kids { margin-left: 9px; padding-left: 8px; border-left: 1px solid #c9bfa9; }
  .snav a { display: block; padding: 3px 6px; border-radius: 3px; color: #3a3a3a; text-decoration: none; }
  .snav a.cur { background: #8b1a1a; color: #f4efe6; }
  .snav .hide { display: none; }
  .snav-toggle { position: fixed; top: 10px; left: 10px; z-index: 950; width: 34px; height: 34px;
    border: 1px solid #c9bfa9; background: #ebe4d6; color: #8b1a1a; border-radius: 3px; cursor: pointer;
    font: 500 16px/1 'IBM Plex Mono', monospace; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
  @media (min-width: 1100px) { html.snav-on { padding-left: 280px; } .snav-toggle { left: 290px; }
    html:not(.snav-on) .snav-toggle { left: 10px; } }
  @media print { .snav, .snav-toggle { display: none; } html.snav-on { padding-left: 0; } }`;

  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };

  var nav = document.createElement('nav');
  nav.className = 'snav';
  nav.setAttribute('aria-label', 'Site navigation');
  nav.innerHTML = '<div class="snav-head"><span class="snav-title">Index</span></div>' +
    '<input type="search" placeholder="Filter pages…" aria-label="Filter pages">';
  var root = document.createElement('div');
  nav.appendChild(root);

  function resolve(p) { return new URL(p, base).href; }

  function build(items, parent) {
    var hasCur = false;
    items.forEach(function (n) {
      if (n.children) {
        var d = document.createElement('details');
        var s = document.createElement('summary');
        s.textContent = n.label;
        var kids = document.createElement('div');
        kids.className = 'kids';
        d.appendChild(s);
        d.appendChild(kids);
        var open = build(n.children, kids);
        if (open || n.open) d.open = true;
        parent.appendChild(d);
        hasCur = hasCur || open;
      } else {
        var a = document.createElement('a');
        a.href = resolve(n.href);
        a.textContent = n.label;
        a.dataset.q = n.label.toLowerCase();
        if (a.href === here || (n.href.slice(-10) === 'index.html' && a.href.replace(/index\.html$/, '') === here)) {
          a.className = 'cur';
          hasCur = true;
        }
        parent.appendChild(a);
      }
    });
    return hasCur;
  }
  build(tree, root);

  var filter = nav.querySelector('input');
  filter.addEventListener('input', function () {
    var q = filter.value.trim().toLowerCase();
    root.querySelectorAll('a').forEach(function (a) {
      a.classList.toggle('hide', !!q && a.dataset.q.indexOf(q) === -1);
    });
    root.querySelectorAll('details').forEach(function (d) {
      var any = d.querySelector('a:not(.hide)');
      d.classList.toggle('hide', !any);
      if (q && any) d.open = true;
    });
  });

  var btn = document.createElement('button');
  btn.className = 'snav-toggle';
  btn.setAttribute('aria-label', 'Toggle navigation');
  btn.textContent = '☰';

  var wide = window.matchMedia('(min-width: 1100px)');
  var pref = store.get('snav-open');
  var open = pref === null ? wide.matches : pref === '1';

  function apply() {
    nav.classList.toggle('closed', !open);
    document.documentElement.classList.toggle('snav-on', open);
  }
  btn.addEventListener('click', function () { open = !open; store.set('snav-open', open ? '1' : '0'); apply(); });

  function mount() {
    document.body.appendChild(nav);
    document.body.appendChild(btn);
    apply();
    var cur = nav.querySelector('a.cur');
    if (cur) cur.scrollIntoView({ block: 'center' });
  }
  if (document.body) mount(); else document.addEventListener('DOMContentLoaded', mount);
})();
