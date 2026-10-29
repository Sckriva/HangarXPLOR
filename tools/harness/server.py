"""Local stand-in for the RSI "My Hangar" page, for testing HangarXPLOR without an RSI account.

Serves the repository root statically, plus:
  /account/pledges?page=N  (and /en/account/pledges)  RSI-like hangar page built from FIXTURES, PER_PAGE per page
  /account/buy-back-pledges?page=N                     RSI-like buyback page built from BUYBACKS
  /ship-matrix/index                                   copy of the public ship matrix (tools/harness/rsi/)
  POST /api/account/pledgeLog                          minimal pledge log payload

?ext=<folder> on the hangar page injects the extension found in that folder (default: src),
and is remembered in a cookie so native pager links keep injecting it.
?style=plain drops RSI's stylesheet (faster, and readable without network access).

RSI's own scripts and stylesheet are not versioned: run fetch_rsi.py once to download them.

Live mode: the real RSI page may load the extension from this server (tools/harness/inject.js?src=...),
so CORS and Private Network Access headers allow robertsspaceindustries.com. POST /capture?name=X saves
the request body to tools/harness/private/X.html (git-ignored) to turn real pages into local fixtures.
"""
import http.server, json, os, re, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RSI = os.path.join(HERE, 'rsi')
PRIVATE = os.path.join(HERE, 'private')
RSI_ORIGINS = ('https://robertsspaceindustries.com', 'https://www.robertsspaceindustries.com')
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8791
PER_PAGE = 10

# Fixture pledges, modelled on real RSI markup (Oct 2026). Items are (title, kind):
#   kind ''   -> item listed with images but an empty kind (e.g. upgrades)
#   kind None -> item with no .kind element at all, as RSI lists armor pieces and paints of packs
# upgraded: RSI marks CCU'd pledges with <h3 class="upgraded"> and an "Upgrades" log button inside the title.
# image: RSI's own pledge image (often the ship with its paint); otherwise RSI's default image.
LTI = ('Lifetime Insurance', 'Insurance')
UPGRADE_DATA = '<input type="hidden" class="js-upgrade-data" value=\'{"match_items":[{"name":"%s"}],"target_items":[{"name":"%s"}]}\'>'
MEDIA = 'https://media.robertsspaceindustries.com/%s/heap_infobox.jpg'
FIXTURES = [
    dict(name='Standalone Ship - Cutlass Black - LTI', value=110, items=[('Cutlass Black', 'Ship'), LTI]),
    dict(name='Standalone Ships - Constellation Mk V Centaurus plus Magnitude Paint', value=320, image=MEDIA % 'mqp9fiwtx3x6b',
         items=[('Constellation Mk V Centaurus', 'Ship'), ('Constellation Mk V - Magnitude Paint', 'Skin'), LTI]),
    dict(name='Upgrade - Avenger Titan to Cutlass Black', value=60, items=[('Upgrade - Avenger Titan to Cutlass Black', '')],
         extra=UPGRADE_DATA % ('Avenger Titan', 'Cutlass Black')),
    dict(name='Standalone Ships - Intrepid plus Oblivion Paint', value=60, upgraded=True, image=MEDIA % 'bw965uo7ci0yj',
         items=[('Perseus', 'Ship'), ('Intrepid - Oblivion Paint', 'Skin'), ('120 Month Insurance', 'Insurance')]),
    dict(name='1 Year Centurion Reward - 10% Coupon: SRDEMO0001', value=0, items=[]),
    dict(name='Outcast Paint Pack', value=15, items=[('Vulture - Outcast Paint', None), ('Prospector - Outcast Paint', None), ('Fortune - Outcast Paint', None)]),
    dict(name='CDS ADP-mk4 \u2018SecondWind\u2019 Heavy Armor', value=0, items=[('FBL-8u \'SecondWind\' Undersuit', None), ('ADP-mk4 \'SecondWind\' Core', None),
         ('ADP-mk4 \'SecondWind\' Helmet', None), ('ADP-mk4 \'SecondWind\' Arms', None), ('ADP-mk4 \'SecondWind\' Legs', None)]),
    dict(name='Package - Aurora MR Starter Pack - LTI', value=45, items=[('Aurora MR', 'Ship'), LTI, ('Star Citizen Digital Download', None), ('Self-Land Hangar', None)]),
    dict(name='Gear - Pirate Week Treasure Pack', value=0, items=[('Pirate Captain Hat', 'FPS Equipment'), ('Pirate Captain Coat', 'FPS Equipment'), ('Salvaged Skull 1 SCU Container', None)]),
    dict(name='Standalone Ships - Hermes plus Tripline Paint', value=240, image=MEDIA % 'rkznko83r31s7', items=[('Hermes', 'Ship'), ('Hermes - Tripline Paint', 'Skin'), LTI]),
    dict(name='Add-Ons - Hangar Decoration - Model Mustang Alpha', value=15, items=[('Model Mustang Alpha', 'Hangar decoration')]),
    dict(name='6 Months Imperator Reward - 20% Coupon: SRDEMO0002', value=0, items=[]),
    dict(name='Standalone Ship - Prospector - LTI', value=155, items=[('Prospector', 'Ship'), LTI]),
    dict(name='Upgrade - Aurora MR to Avenger Titan', value=25, items=[('Upgrade - Aurora MR to Avenger Titan', '')],
         extra=UPGRADE_DATA % ('Aurora MR', 'Avenger Titan')),
]
TOTAL = 47

ITEM = """<li> <div class="row trans-03s trans-background "> <div class="basic-infos clearfix"> <div class="item-image-wrapper content-block3 "> <div class="image" style="background-image:url('{image}');"></div>
<div class="corner corner-top-left"></div> <div class="corner corner-top-right"></div> <div class="corner corner-bottom-left"></div> <div class="corner corner-bottom-right"></div> </div>
<div class="wrapper-col"> <a class="arrow js-expand-arrow trans-02s"><span class="effect trans-02s trans-opacity"></span></a> <div class="title-col"> <div class="pledge-title-row"> <h3 class="{h3class}"> {name} {upgradelog}</h3> </div>
<input type="hidden" class="js-pledge-id" value="{id}"> <input type="hidden" class="js-pledge-name" value="{name}"> <input type="hidden" class="js-pledge-value" value="${value:.2f} USD">
<input type="hidden" class="js-pledge-configuration-value" value="$0.00 USD"> <input type="hidden" class="js-pledge-currency" value="Store Credit"> {extra} <span class="availability ">Attributed</span> </div>
<div class="date-col"> <label>Created:</label> {date} </div> <div class="items-col"> <label>Contains:</label> {contains} </div> </div> </div>
<div class="items more js-more trans-02s trans-height"> <h2>Items</h2> <a class="shadow-button trans-02s trans-color js-gift gift"><span class="label js-label trans-02s">Gift</span></a>
<div class="content-block1"> <div class="with-images"> {items} <div class="cboth"></div> </div> <div class="without-images"> {kindless} <div class="cboth"></div> </div> </div> </div> <div class="line"><div class="effect trans-02s trans-opacity"></div></div> </div> </li>"""

SUBITEM = '<div class="item "> <div class="text"> <div class="title">{title}</div> {kind} </div> </div>'
KINDLESS = '<div class="item "> <div class="title"> {title} </div> </div>'
UPGRADE_LOG = ('<a class="shadow-button trans-02s trans-color js-upgrade-log upgrade"> <span class="label js-label trans-02s">Upgrades</span>'
               ' <span class="icon trans-02s"><span class="effect trans-opacity trans-03s"></span></span> </a> ')
DEFAULT_IMAGE = 'https://cdn.robertsspaceindustries.com/static/images/Temp/default-image.png'


def pledge(i):
    f = FIXTURES[i % len(FIXTURES)]
    name, items = f['name'], f['items']
    if 'Coupon' in name:
        name = name.replace('0001', '%04d' % i).replace('0002', '%04d' % i)  # coupon codes are unique
    return ITEM.format(id=100000 - i, name=name, value=f['value'], extra=f.get('extra', ''), date='October %d, 2026' % (28 - i % 28),
                       image=f.get('image', DEFAULT_IMAGE), h3class='upgraded' if f.get('upgraded') else '',
                       upgradelog=UPGRADE_LOG if f.get('upgraded') else '',
                       contains=(items[0][0] + (' and %d items' % (len(items) - 1) if len(items) > 1 else '')) if items else name,
                       items=''.join(SUBITEM.format(title=t, kind='<div class="kind">%s</div>' % k if k else '') for t, k in items if k is not None),
                       kindless=''.join(KINDLESS.format(title=t) for t, k in items if k is None))


def native_pager(page, pages):
    links = ''.join('<a class="trans-02s trans-color %s" href="/account/pledges?page=%d">%d</a>' % ('active' if p == page else '', p, p)
                    for p in range(max(1, page - 1), min(pages, page + 2) + 1))
    return '<div class="pager clearfix"><div class="right">%s<span class="spacer"></span></div></div>' % links


PLAIN_CSS = """<style>body{background:#fff;font:13px sans-serif} .selectlist{display:block;position:relative;border:1px solid #888;padding:4px;cursor:pointer;float:left;margin-right:8px}
.selectlist ul.body{position:absolute;top:100%;left:0;background:#eee;z-index:20;list-style:none;padding:0;margin:0;width:100%} .pager a{padding:0 4px;cursor:pointer} .pager a.active{font-weight:bold;color:red}
.list-items{clear:both} .list-items h3{margin:2px 0;font-size:13px} .items{display:none} .billing-title-pager-wrapper{overflow:hidden;padding:6px 0} .left{float:left}.right{float:left}</style>"""

RSI_CSS = """<link rel="stylesheet" href="/tools/harness/rsi/fonts.css"><link rel="stylesheet" href="/tools/harness/rsi/rsi-css.css">"""


def hangar_page(page, ext, style):
    pages = (TOTAL + PER_PAGE - 1) // PER_PAGE
    page = min(max(page, 1), pages)  # RSI returns the last page for out-of-range page numbers
    start = (page - 1) * PER_PAGE
    items = ''.join(pledge(i) for i in range(start, min(TOTAL, start + PER_PAGE)))
    selectlist = ('<div class="product-type-filter js-product-type-filter" style="width: 150px;"><a class="js-selectlist selectlist " rel="" href="">'
                  '<div class="arrow"></div><span>All</span><ul class="body"><li class="js-option option selected" rel="?page=1&amp;product-type=">All</li>'
                  '<li class="js-option option " rel="?page=1&amp;product-type=upgrade">Upgrades</li></ul>'
                  '<input type="hidden" name="" class="js- js-form-data" id="" value="?page=1&amp;product-type="></a></div>')
    inject = ('<script src="/tools/harness/inject.js?src=%s"></script>' % urllib.parse.quote(ext)) if ext else ''
    css = RSI_CSS if style != 'plain' and os.path.exists(os.path.join(RSI, 'rsi-css.css')) else PLAIN_CSS
    return """<!doctype html><html><head><meta charset="utf-8"><title>My Hangar (harness)</title>%s
<script src="/tools/harness/rsi/rsi-external-js.js"></script><script src="/tools/harness/rsi/rsi-templates-js.js"></script>
<script src="/tools/harness/rsi/rsi.core.js"></script><script src="/tools/harness/rsi/rsi.account.js"></script>
<script>$(document).ready(function() { window.Common = new RSI.Common({}); });</script>
</head><body><div id="bodyWrapper"><div id="contentbody" class="account-section"><div class="wrapper"><div id="billing" class="content-wrapper content-block1 pledges"><div class="content clearfix"><div class="inner-content">
<div class="billing-title-pager-wrapper"><h3>MY GEAR</h3><div class="controls">%s<div class="options-selector pager-wrapper">%s</div></div></div>
<ul class="list-items">%s</ul>
<div class="bottom billing-title-pager-wrapper">%s</div>
</div></div></div></div></div></div>%s</body></html>""" % (css, selectlist, native_pager(page, pages), items, native_pager(page, pages), inject)


# Buyback page, modelled on the real markup (Oct 2026). RSI serves 10 per page here and ignores &pagesize=.
BUYBACK_PER_PAGE = 10
BUYBACKS = [
    ('Paints', 'Railen - Insularis Paint', 'Railen - Insularis Paint', 'd993fzx6ja8he'),
    ('Paints', 'Clipper - Regatta Paint', 'Clipper - Regatta Paint', 'nfqpqu20a0a2m'),
    ('Paints', 'ATLS - 4 Paint Pack', '4 items', 'myzjzr8ynvhbv'),
    ('Standalone Ship', 'Avenger Titan', 'Avenger Titan and 1 item', 'b5dkcbyojrq3g'),
    ('Upgrade', 'Avenger Titan to Cutlass Black', 'Upgrade - Avenger Titan to Cutlass Black', 'h84m7m1hw0dcq'),
    ('Package', 'Aurora MR Starter Pack', 'Aurora MR and 3 items', 'rh3zjmon4w468'),
    ('Add-Ons', 'Model Mustang Alpha', 'Model Mustang Alpha', 'td5w87d85m3j7'),
]
BUYBACK_TOTAL = 14
BUYBACK_ITEM = """<li> <article class="pledge"> <div class="information no-countdown"> <figure> <img src="https://media.robertsspaceindustries.com/{media}/heap_infobox.jpg" alt="{type} - {name}"> </figure> <div>
<div class="pledge-title-row no-countdown"> <h1 title="{type} - {name}">{type} - {name}</h1> </div>
<dl> <dt>Reclaim Date</dt> <dd>{date}</dd> <dt>Contained</dt> <dd>{contained}</dd> </dl>
<div class="buyback-action"> <a class="holosmallbtn" href="/pledge/buyback/{id}"> <span class="holosmallbtn-top abs-overlay trans-02s js-label">Buy Back</span> <span class="holosmallbtn-bottom abs-overlay trans-02s"></span> </a> </div>
<div class="unavailable"> <div class="caption">Not available</div> <a href="#" class="why"> Why can't I pledge for this item? <section class="unavailable-tooltip"> <p>This pledge is unavailable for one of the following reasons:</p>
<ul> <li>It includes physical items [that are no longer available.]</li> <li>It was a special discounted or limited offer</li> </ul> <div class="triangle"></div> </section> </a> </div>
</div> </div> </article> </li>"""


def buyback_page(page, ext, css):
    start = (max(page, 1) - 1) * BUYBACK_PER_PAGE
    items = ''.join(BUYBACK_ITEM.format(type=t, name=n, contained=c, media=m, id=200000 - i, date='June %d, 2026' % (1 + i % 28))
                    for i, (t, n, c, m) in ((i, BUYBACKS[i % len(BUYBACKS)]) for i in range(start, min(BUYBACK_TOTAL, start + BUYBACK_PER_PAGE))))
    items = items or '<li class="no-buy-backs">No pledges available</li>'
    inject = ('<script src="/tools/harness/inject.js?src=%s"></script>' % urllib.parse.quote(ext)) if ext else ''
    return """<!doctype html><html><head><meta charset="utf-8"><title>Buy Back Pledges (harness)</title>%s
<script src="/tools/harness/rsi/rsi-external-js.js"></script><script src="/tools/harness/rsi/rsi-templates-js.js"></script>
<script src="/tools/harness/rsi/rsi.core.js"></script><script src="/tools/harness/rsi/rsi.account.js"></script>
<script>$(document).ready(function() { window.Common = new RSI.Common({}); });</script>
</head><body><div id="bodyWrapper"><div class="page-wrapper"><div id="contentbody" class="account-section buy-back-pledges"><div class="wrapper">
<div id="billing" class="content-wrapper content-block1 pledges buy-back"><div class="content clearfix"><div class="inner-content">
<section class="available-pledges"> <form class="filters legacy-form"> <a class="js-selectlist selectlist " rel="" href=""> <div class="arrow"></div> <span></span> <ul class="body">
<li class="js-option option selected" rel="?page=1&amp;product-type=">All</li> <li class="js-option option " rel="?page=1&amp;product-type=standalone_ship">Standalone Ships</li> </ul>
<input type="hidden" name="" class="js- js-form-data" id="" value="?page=1&amp;product-type="> </a> </form>
<div class="js-buyback-results"> <ul class="pledges"> %s </ul> <div class="options-selector pager-wrapper"> </div> </div> </section>
</div></div></div></div></div></div></div>%s</body></html>""" % (css, items, inject)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def send_body(self, body, ctype, cookies=()):
        data = body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        for c in cookies:
            self.send_header('Set-Cookie', c + '; Path=/')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        if url.path in ('/account/pledges', '/en/account/pledges'):
            jar = dict(c.strip().split('=', 1) for c in self.headers.get('Cookie', '').split(';') if '=' in c)
            ext = q['ext'][0] if 'ext' in q else urllib.parse.unquote(jar.get('hxext', 'src'))
            style = q['style'][0] if 'style' in q else jar.get('hxstyle', '')
            cookies = ['hxext=' + urllib.parse.quote(ext, safe=''), 'hxstyle=' + style]
            # Pages fetched by the extension's own ajax get no injection; the page the user opens does
            if 'X-Requested-With' in self.headers:
                ext = ''
            return self.send_body(hangar_page(int(q.get('page', ['1'])[0]), ext, style), 'text/html; charset=utf-8', cookies)
        if url.path in ('/account/buy-back-pledges', '/en/account/buy-back-pledges'):
            jar = dict(c.strip().split('=', 1) for c in self.headers.get('Cookie', '').split(';') if '=' in c)
            ext = q['ext'][0] if 'ext' in q else urllib.parse.unquote(jar.get('hxext', 'src'))
            style = q['style'][0] if 'style' in q else jar.get('hxstyle', '')
            if 'X-Requested-With' in self.headers:
                ext = ''
            css = RSI_CSS if style != 'plain' and os.path.exists(os.path.join(RSI, 'rsi-css.css')) else PLAIN_CSS
            return self.send_body(buyback_page(int(q.get('page', ['1'])[0]), ext, css), 'text/html; charset=utf-8',
                                  ['hxext=' + urllib.parse.quote(ext or 'src', safe=''), 'hxstyle=' + style])
        if url.path == '/ship-matrix/index':
            with open(os.path.join(RSI, 'ship-matrix.json'), encoding='utf-8') as f:
                return self.send_body(f.read(), 'application/json')
        return super().do_GET()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        url = urllib.parse.urlparse(self.path)
        if url.path == '/capture':
            name = re.sub(r'[^A-Za-z0-9_.-]', '_', urllib.parse.parse_qs(url.query).get('name', ['capture'])[0])
            os.makedirs(PRIVATE, exist_ok=True)
            with open(os.path.join(PRIVATE, name + '.html'), 'wb') as f:
                f.write(body)
            return self.send_body(json.dumps({'saved': name, 'bytes': len(body)}), 'application/json')
        if self.path.startswith('/api/account/pledgeLog'):
            return self.send_body(json.dumps({'success': 1, 'code': 'OK', 'data': {'rendered': 'x' * 200}}), 'application/json')
        self.send_error(404)

    def end_headers(self):
        origin = self.headers.get('Origin', '')
        if origin in RSI_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.send_header('Access-Control-Allow-Private-Network', 'true')
            self.send_header('Vary', 'Origin')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


if __name__ == '__main__':
    print('HangarXPLOR harness on http://localhost:%d/en/account/pledges?page=1' % PORT)
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
