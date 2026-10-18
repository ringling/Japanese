/* Site-wide light/dark. Loaded in <head> so the right theme is set before first paint.
   Choice is stored in localStorage 'site-theme' ('light' | 'dark'); with no choice it follows the OS. */
(function () {
  var KEY = 'site-theme', root = document.documentElement, mq = window.matchMedia('(prefers-color-scheme: dark)');
  var own = /\/(grammar|yobanashi)\//.test(location.pathname); // these pages ship their own dark palette
  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function current() { var s = stored(); return s === 'dark' || s === 'light' ? s : (mq.matches ? 'dark' : 'light'); }
  function apply() {
    var t = current();
    root.setAttribute('data-theme', t);
    if (t === 'dark' && !own) root.setAttribute('data-site-dark', ''); else root.removeAttribute('data-site-dark');
    window.dispatchEvent(new Event('site-theme'));
  }
  window.SiteTheme = {
    get: current,
    set: function (t) { try { localStorage.setItem(KEY, t); } catch (e) {} apply(); },
    toggle: function () { this.set(current() === 'dark' ? 'light' : 'dark'); }
  };
  if (mq.addEventListener) mq.addEventListener('change', function () { if (!stored()) apply(); });
  window.addEventListener('storage', function (e) { if (e.key === KEY) apply(); });
  apply();
})();
