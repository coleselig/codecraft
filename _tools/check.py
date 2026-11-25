#!/usr/bin/env python3
"""Phone and desktop check for demo pages, drawn with their real web fonts.

Run from the repo root:  python3 _tools/check.py SLUG [SLUG ...]     (or no slugs for every page: about 15 minutes)
For each page at 360, 375, 768 and 1280 px wide it reports
  - text or buttons cut off at the screen edge,
  - sideways scrolling,
  - a page that opens already scrolled down,
  - a main headline that spills far out of its own column.
Fix what it prints before sending a page to anyone. It installs the fonts first (_tools/fonts.py), because
this workspace cannot load Google Fonts and fallback fonts give wrong answers in both directions.
"""
import asyncio, os, sys

WIDTHS = (360, 375, 768, 1280)
JS = r"""() => { const vw = document.documentElement.clientWidth; const out = [];
  const skipAnc = (el) => { for (let n = el; n && n !== document.body; n = n.parentElement) { const cs = getComputedStyle(n);
      if (/(auto|scroll)/.test(cs.overflowX)) return 'scroller'; if (n.getAttribute('aria-hidden') === 'true') return 'aria-hidden';
      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return 'hidden';
      if (cs.position === 'fixed') return 'fixed';
      if (cs.animationName && cs.animationName !== 'none' && /infinite/.test(cs.animationIterationCount)) { let moves = false; try { moves = n.getAnimations().some(a => a.effect && a.effect.getKeyframes().some(k => ('transform' in k && k.transform !== 'none') || 'translate' in k || 'left' in k || 'marginLeft' in k || 'right' in k)); } catch (e) { moves = true; } if (moves) return 'anim'; }
      if (/marquee|ticker|tape|scroll|track|slider|carousel/i.test(n.className && n.className.baseVal === undefined ? n.className : '')) return 'marquee';
      if (cs.position === 'absolute' && cs.pointerEvents === 'none') return 'decor';
      if (/(hidden|clip)/.test(cs.overflowX)) { const r = n.getBoundingClientRect(); if (r.right <= vw + 1 && r.left >= -1 && r.width < vw * 0.9) return 'clipped-by-design'; } }
    return null; };
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (w.nextNode()) { const n = w.currentNode; const t = n.textContent.trim(); if (t.length < 2) continue; const pe = n.parentElement; if (!pe || ['SCRIPT','STYLE','NOSCRIPT'].includes(pe.tagName)) continue;
    const rg = document.createRange(); rg.selectNodeContents(n); let bad = null;
    for (const r of rg.getClientRects()) { if (r.width > 0 && r.height > 0 && r.left >= -2 && r.left < vw - 4 && r.right > vw + 5) { bad = r; break; } if (r.width > 0 && r.height > 0 && r.left < -3 && r.right > 4) { bad = r; break; } }
    if (!bad) continue; const why = skipAnc(pe); if (why) continue;
    const key = pe.tagName + t.slice(0, 20); if (seen.has(key)) continue; seen.add(key);
    out.push({tag: pe.tagName + '.' + (pe.className && pe.className.baseVal === undefined ? pe.className : '').toString().slice(0, 24), inH1: !!pe.closest('h1'), inBtn: !!pe.closest('a,button'), l: Math.round(bad.left), r: Math.round(bad.right), y: Math.round(bad.top + scrollY), fs: getComputedStyle(pe).fontSize, t: t.slice(0, 40)});
    if (out.length >= 8) break; }
  const heads = [];
  document.querySelectorAll('h1,h2').forEach(h => { const cs = getComputedStyle(h); if (cs.display === 'none' || cs.visibility === 'hidden') return; if (skipAnc(h) && skipAnc(h) !== 'clipped-by-design') return;
    let R = -1e9; const tw = document.createTreeWalker(h, NodeFilter.SHOW_TEXT); while (tw.nextNode()) { const n = tw.currentNode; if (!n.textContent.trim()) continue; const pcs = getComputedStyle(n.parentElement); if (pcs.display === 'none' || pcs.visibility === 'hidden') continue; const rg = document.createRange(); rg.selectNodeContents(n); for (const r of rg.getClientRects()) if (r.width > 0) R = Math.max(R, r.right); }
    const b = h.getBoundingClientRect(); if (R > b.right + 6 && b.width > 40) heads.push({tag: h.tagName, over: Math.round(R - b.right), box: [Math.round(b.left), Math.round(b.right)], R: Math.round(R), fs: cs.fontSize, t: h.textContent.trim().replace(/\s+/g, ' ').slice(0, 36)}); });
  return {vw, sw: document.documentElement.scrollWidth, n: out.length, out, heads: heads.slice(0, 4)}; }"""


def pages(root, only):
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith('.') and x not in ('media', 'cc-reels', '_tools')]
        if 'index.html' in files:
            rel = os.path.relpath(os.path.join(d, 'index.html'), root).replace(os.sep, '/')
            top = rel.split('/')[0] if '/' in rel else '.'
            if not only or top in only:
                out.append(rel)
    return sorted(out)


async def launch(p):
    try:
        return await p.chromium.launch(args=['--no-sandbox'])
    except Exception:
        for exe in ('/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'):
            if os.path.exists(exe):
                return await p.chromium.launch(executable_path=exe, args=['--no-sandbox'])
        raise


async def main():
    root = os.getcwd()
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import fonts
        fonts.ensure(root)
    except Exception as ex:
        print('fonts: skipped (%s) - results below may be wrong' % str(ex)[:100])
    rels = pages(root, set(a.strip('/') for a in sys.argv[1:]))
    from playwright.async_api import async_playwright
    sem = asyncio.Semaphore(5)
    found = {}
    async with async_playwright() as p:
        browser = await launch(p)

        async def one(rel, w):
            async with sem:
                ctx = await browser.new_context(viewport={'width': w, 'height': 760}, is_mobile=(w < 500), has_touch=(w < 500))
                try:
                    pg = await ctx.new_page()
                    await pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
                    await pg.goto('file://' + os.path.join(root, rel), wait_until='domcontentloaded', timeout=20000)
                    await pg.wait_for_timeout(1100)
                    y = await pg.evaluate('Math.round(scrollY)')
                    await pg.evaluate("document.querySelectorAll('*').forEach(e => { const cs = getComputedStyle(e); if (parseFloat(cs.opacity) === 0 && cs.transitionDuration !== '0s') { e.style.setProperty('opacity','1','important'); e.style.setProperty('transform','none','important'); } })")
                    i = await pg.evaluate(JS)
                    probs = []
                    if y:
                        probs.append('opens scrolled down %dpx' % y)
                    if i['sw'] > i['vw'] + 1:
                        probs.append('sideways scroll (page is %dpx wide)' % i['sw'])
                    for o in i['out'][:3]:
                        probs.append('cut off: "%s" (%s, right edge %d)' % (o['t'][:28], o['fs'], o['r']))
                    for hd in i.get('heads', [])[:2]:
                        if hd['over'] >= 40 or hd['R'] > i['vw'] - 4:
                            probs.append('%s spills %dpx out of its column: "%s" (%s)' % (hd['tag'], hd['over'], hd['t'][:24], hd['fs']))
                    if probs:
                        found.setdefault(rel, {})[w] = probs
                except Exception as ex:
                    found.setdefault(rel, {})[w] = ['could not load: ' + str(ex)[:80]]
                finally:
                    await ctx.close()

        await asyncio.gather(*(one(r, w) for r in rels for w in WIDTHS))
        await browser.close()
    print('checked %d page(s) at %s px' % (len(rels), ', '.join(map(str, WIDTHS))))
    if not found:
        print('all clear')
    for rel in sorted(found):
        print(rel)
        for w in sorted(found[rel]):
            for pr in found[rel][w]:
                print('   %4d  %s' % (w, pr))

if __name__ == '__main__':
    asyncio.run(main())
