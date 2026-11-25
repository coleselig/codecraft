/* Code Craft Media: the "Want it live?" link on concept and preview pages.
   Loaded as <script src="/codecraft/cc.js" defer data-biz="Business" data-kind="concept|preview">.
   It adds one link to the page's own concept note and opens a small sheet with two ways to reply. */
(function () {
  'use strict';
  var s = document.currentScript;
  if (!s || window.__ccYes) return;
  window.__ccYes = 1;

  var biz = (s.getAttribute('data-biz') || document.title.split(/\s[—|·]\s/)[0] || 'your business').trim();
  var kind = s.getAttribute('data-kind') || 'concept';
  var EMAIL = '54321coleman@gmail.com';
  var IG = 'https://ig.me/m/code_craft_media';
  var HOME = 'https://coleselig.github.io/codecraft/';
  var url = location.origin + location.pathname;

  var T = kind === 'preview' ? {
    link: 'Like it? Tap to make it live.',
    strip: 'Like the preview?',
    find: /Preview for [^.]{1,40}\.\s*Built by Code Craft Media/i,
    full: /Preview for [^.]{1,40}\.\s*Built by Code Craft Media/i,
    h: 'Ready to make it live?',
    steps: [
      'Tap Email Cole. The message is already written, so you just hit send. Instagram works too.',
      'Your logo and photos can come later. Cole swaps them in and makes your changes (two rounds of edits are included).',
      'You approve the finished site first. Only then do you pay: one time, from $149. No monthly fees.'
    ],
    subj: 'Go ahead with the ' + biz + ' website',
    body: 'Hi Cole,\n\nI looked at the preview. Go ahead and make it live.\n\n' + url + '\n'
  } : {
    link: 'Want it live?',
    strip: 'This site was made for ' + biz + '.',
    find: /Concept site by\s*Code Craft Media/i,
    full: /Concept site by\s*Code Craft Media[\s\S]{0,200}?Not live/i,
    h: 'Want this site live for ' + biz + '?',
    steps: [
      'Tap Email Cole. The message is already written, so you just hit send. Instagram works too.',
      'Cole puts in your logo and photos and makes your changes (two rounds of edits are included).',
      'You approve the finished site first. Only then do you pay: one time, from $149. No monthly fees.'
    ],
    subj: 'Interested in the ' + biz + ' website',
    body: 'Hi Cole,\n\nI saw the site you made for ' + biz + " and I'm interested. What are the next steps?\n\n" + url + '\n'
  };

  var mailto = 'mailto:' + EMAIL + '?subject=' + encodeURIComponent(T.subj) + '&body=' + encodeURIComponent(T.body);
  var LINK_CSS = 'display:inline!important;padding:0!important;margin:0 0 0 .4em!important;background:none!important;' +
    'border:0!important;box-shadow:none!important;color:inherit!important;font:inherit!important;font-weight:700!important;' +
    'text-decoration:underline!important;text-underline-offset:2px!important;white-space:nowrap!important;cursor:pointer!important;' +
    'letter-spacing:inherit!important;text-transform:inherit!important;opacity:1!important;width:auto!important;height:auto!important;' +
    'min-height:0!important;position:static!important;float:none!important';

  function vis(el) {
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  function deepest(re) {
    var all = document.body.querySelectorAll('div,p,span,small,aside,section,footer,header,li');
    var best = null;
    for (var i = 0; i < all.length; i++) {
      var el = all[i], t = el.textContent || '';
      if (t.length > 420 || !re.test(t)) continue;
      if (!best || best.contains(el)) best = el; /* first match in the page, narrowed to its deepest matching child */
    }
    return best;
  }
  function findNote() {
    var n = deepest(T.full) || deepest(T.find);
    if (!n) return null;
    /* A hidden variant (pages keep a long and a short wording) or a cut-off piece: use the parent that holds the whole note. */
    while (n.parentElement && n.parentElement !== document.body && (n.parentElement.textContent || '').length <= 420 &&
           (!vis(n) || /made for\s*$/i.test((n.textContent || '').trim()))) n = n.parentElement;
    return vis(n) ? n : null;
  }

  function makeLink(text) {
    var a = document.createElement('a');
    a.href = '#yes';
    a.setAttribute('data-cc-yes', '');
    a.textContent = text;
    a.style.cssText = LINK_CSS;
    a.addEventListener('click', function (e) { e.preventDefault(); open(a); });
    return a;
  }

  function strip() {
    var d = document.createElement('div');
    d.setAttribute('data-cc-strip', '');
    d.style.cssText = 'display:block;margin:0;padding:10px 16px;background:#1c1c1e;color:#fff;text-align:center;' +
      'font:500 13px/1.45 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;position:relative;z-index:1';
    d.appendChild(document.createTextNode(T.strip));
    d.appendChild(makeLink(kind === 'preview' ? 'Tap to make it live.' : 'Want it live?'));
    document.body.appendChild(d); /* end of the page: in normal flow, never under a fixed header */
  }

  function inView(r) {
    return r.bottom > 0 && r.top < window.innerHeight && r.right > 0 && r.left < document.documentElement.clientWidth;
  }
  /* Is the point showing something that belongs to the note? Points outside the viewport cannot be tested and count as fine. */
  function owns(note, x, y) {
    if (y < 0 || y >= window.innerHeight || x < 0 || x >= document.documentElement.clientWidth) return true;
    var e = document.elementFromPoint(x, y);
    return !e || note.contains(e);
  }
  function linkOk(note, a) {
    var r = a.getBoundingClientRect(), b = note.getBoundingClientRect();
    var vw = document.documentElement.clientWidth;
    if (!(r.width > 0 && r.height > 0)) return false;
    if (r.left < -1 || r.right > vw + 1 || r.left < b.left - 2 || r.right > b.right + 2) return false;
    if (r.top < b.top - 2 || r.bottom > b.bottom + 2) return false;
    if (getComputedStyle(note).visibility === 'hidden') return false;
    return !inView(r) || owns(note, r.left + r.width / 2, r.top + r.height / 2);
  }
  function pinnedTop(note) {
    for (var n = note; n && n !== document.body; n = n.parentElement) {
      var p = getComputedStyle(n).position;
      if (p === 'fixed' || p === 'sticky') return true;
    }
    return false;
  }
  function lastLineClear(note) {
    var b = note.getBoundingClientRect(), y = b.bottom - 3;
    return owns(note, b.left + b.width * 0.12, y) && owns(note, b.left + b.width * 0.5, y) && owns(note, b.left + b.width * 0.88, y);
  }

  function place() {
    var note = findNote();
    if (!note) { strip(); return; }
    var h0 = note.getBoundingClientRect().height;

    /* 1. Plain: the link follows the note's own text. Fine when nothing moves, or when the note may grow freely. */
    var a = makeLink(T.link);
    note.appendChild(a);
    var grew = note.getBoundingClientRect().height > h0 + 1;
    if (linkOk(note, a) && (!grew || (!pinnedTop(note) && lastLineClear(note)))) return;
    note.removeChild(a);

    /* 2. One line: the note's text shortens with an ellipsis and the link sits at its end, so the note keeps its height. */
    var keep = note.getAttribute('style');
    var wrap = document.createElement('span');
    while (note.firstChild) wrap.appendChild(note.firstChild);
    wrap.style.cssText = 'display:block;flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
    note.appendChild(wrap);
    a = makeLink(T.link);
    a.style.setProperty('flex', 'none', 'important');
    note.appendChild(a);
    var disp = getComputedStyle(note).display;
    note.style.setProperty('display', disp.indexOf('inline') === 0 ? 'inline-flex' : 'flex', 'important');
    note.style.setProperty('flex-direction', 'row', 'important');
    note.style.setProperty('flex-wrap', 'nowrap', 'important');
    note.style.setProperty('justify-content', 'center', 'important');
    note.style.setProperty('align-items', 'baseline', 'important');
    note.style.setProperty('white-space', 'nowrap', 'important');
    note.style.setProperty('max-width', '100%', 'important');
    if (linkOk(note, a) && note.getBoundingClientRect().height <= h0 + 1 && wrap.getBoundingClientRect().width > 90) return;

    /* 3. Neither fits: put the note back exactly as it was and use a strip at the end of the page. */
    note.removeChild(a);
    while (wrap.firstChild) note.insertBefore(wrap.firstChild, wrap);
    note.removeChild(wrap);
    if (keep === null) note.removeAttribute('style'); else note.setAttribute('style', keep);
    strip();
  }

  var host, opener;
  function open(from) {
    opener = from || null;
    if (!host) build();
    host.style.display = 'block';
    var p = host.shadowRoot.querySelector('a.p');
    if (p) p.focus();
    document.addEventListener('keydown', onKey);
  }
  function close() {
    if (host) host.style.display = 'none';
    document.removeEventListener('keydown', onKey);
    if (opener && opener.focus) opener.focus();
  }
  function onKey(e) { if (e.key === 'Escape') close(); }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.textContent = text;
    return n;
  }

  function build() {
    host = document.createElement('div');
    host.id = 'cc-yes-host';
    host.style.cssText = 'display:none';
    var root = host.attachShadow({ mode: 'open' });
    var css = document.createElement('style');
    css.textContent =
      ':host{all:initial}' +
      '.ov{position:fixed;inset:0;z-index:2147483647;background:rgba(12,12,14,.64);display:flex;align-items:flex-end;justify-content:center;' +
      'font-family:Poppins,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}' +
      '.card{position:relative;box-sizing:border-box;width:100%;max-width:440px;max-height:92vh;overflow:auto;background:#1c1c1e;color:#fff;' +
      'border-radius:22px 22px 0 0;padding:26px 22px 22px;padding-bottom:calc(22px + env(safe-area-inset-bottom,0px));box-shadow:0 -12px 60px rgba(0,0,0,.45)}' +
      '@media(min-width:560px){.ov{align-items:center}.card{border-radius:22px;padding:30px 28px 26px}}' +
      'h2{margin:0 40px 16px 0;font-size:22px;line-height:1.2;font-weight:700;letter-spacing:-.01em}' +
      'ol{margin:0 0 20px;padding:0;list-style:none;counter-reset:s}' +
      'li{counter-increment:s;position:relative;margin:0 0 11px;padding:0 0 0 34px;font-size:15px;line-height:1.45;color:#d9d9de}' +
      'li::before{content:counter(s);position:absolute;left:0;top:1px;width:22px;height:22px;border-radius:50%;background:#e8692c;color:#1c1c1e;' +
      'font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center}' +
      'a.b{display:block;box-sizing:border-box;margin:0 0 10px;padding:14px 16px;border-radius:12px;text-align:center;text-decoration:none;font-size:16px;font-weight:600}' +
      'a.p{background:#e8692c;color:#1c1c1e}a.s{background:transparent;color:#fff;border:1.5px solid #55555c}' +
      'p{margin:12px 0 0;font-size:12.5px;line-height:1.55;color:#a3a3ab}p a{color:#d9d9de}' +
      'button{position:absolute;top:14px;right:14px;width:36px;height:36px;border:0;border-radius:50%;background:#2c2c30;color:#fff;font-size:20px;line-height:1;cursor:pointer}' +
      'a:focus-visible,button:focus-visible{outline:3px solid #fff;outline-offset:2px}';
    root.appendChild(css);

    var ov = el('div', 'ov');
    var card = el('div', 'card');
    card.setAttribute('role', 'dialog');
    card.setAttribute('aria-modal', 'true');
    card.setAttribute('aria-labelledby', 'cc-yes-h');
    var x = el('button', '', '×');
    x.type = 'button';
    x.setAttribute('aria-label', 'Close');
    x.addEventListener('click', close);
    var h = el('h2', '', T.h);
    h.id = 'cc-yes-h';
    var ol = el('ol');
    for (var i = 0; i < T.steps.length; i++) ol.appendChild(el('li', '', T.steps[i]));
    var m = el('a', 'b p', 'Email Cole');
    m.href = mailto;
    var g = el('a', 'b s', 'Message on Instagram');
    g.href = IG; g.target = '_blank'; g.rel = 'noopener';
    var f = el('p');
    f.appendChild(document.createTextNode('No mail app? Write to ' + EMAIL + ', or reply to the message Cole sent you. Code Craft Media is run by UTK students in Knoxville. '));
    var hw = el('a', '', 'How it works');
    hw.href = HOME; hw.target = '_blank'; hw.rel = 'noopener';
    f.appendChild(hw);
    card.appendChild(x); card.appendChild(h); card.appendChild(ol); card.appendChild(m); card.appendChild(g); card.appendChild(f);
    ov.appendChild(card);
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
    root.appendChild(ov);
    document.body.appendChild(host);
  }

  function start() {
    try { place(); } catch (e) { /* never break the page */ }
    if (location.hash === '#yes') open(null);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
