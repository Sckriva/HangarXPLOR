"""Local stand-in for the RSI "My Hangar" page, for testing HangarXPLOR without an RSI account.

Serves the repository root statically, plus:
  /account/pledges?page=N  (and /en/account/pledges)  RSI-like hangar page built from FIXTURES, PER_PAGE per page
  /ship-matrix/index                                   copy of the public ship matrix (tools/harness/rsi/)
  POST /api/account/pledgeLog                          minimal pledge log payload

?ext=<folder> on the hangar page injects the extension found in that folder (default: src),
and is remembered in a cookie so native pager links keep injecting it.
?style=plain drops RSI's stylesheet (faster, and readable without network access).

RSI's own scripts and stylesheet are not versioned: run fetch_rsi.py once to download them.
"""
import http.server, json, os, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RSI = os.path.join(HERE, 'rsi')
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8791
PER_PAGE = 10

# (pledge name, value in USD, [(item title, kind)], extra markup inside the pledge)
LTI = ('Lifetime Insurance', 'Insurance')
FIXTURES = [
    ('Standalone Ship - Cutlass Black - LTI', 110, [('Cutlass Black', 'Ship'), LTI], ''),
    ('Standalone Ship - Gladius', 90, [('Gladius', 'Ship'), ('6 Month Insurance', 'Insurance')], ''),
    ('Upgrade - Avenger Titan to Cutlass Black', 60, [('Upgrade - Avenger Titan to Cutlass Black', '')],
     '<input type="hidden" class="js-upgrade-data" value=\'{"match_items":[{"name":"Avenger Titan"}],"target_items":[{"name":"Cutlass Black"}]}\'>'),
    ('Paints - Constellation Mk V - Blackthorn Paint', 6, [('Constellation Mk V - Blackthorn Paint', 'Skin')], ''),
    ('1 Year Centurion Reward - 10% Coupon: SRDEMO0001', 0, [], ''),
    ('Package - Aurora MR Starter Pack - LTI', 45, [('Aurora MR', 'Ship'), LTI, ('Star Citizen Digital Download', '')], ''),
    ('Standalone Ship - Carrack - LTI', 600, [('Carrack', 'Ship'), LTI], ''),
    ('Standalone Ship - Freelancer', 125, [('Freelancer', 'Ship'), ('6 Month Insurance', 'Insurance')], ''),
    ('Add-Ons - Hangar Decoration - Model Mustang Alpha', 15, [('Model Mustang Alpha', 'Hangar decoration')], ''),
    ('6 Months Imperator Reward - 20% Coupon: SRDEMO0002', 0, [], ''),
    ('Standalone Ship - Prospector - LTI', 155, [('Prospector', 'Ship'), LTI], ''),
    ('Upgrade - Aurora MR to Avenger Titan', 25, [('Upgrade - Aurora MR to Avenger Titan', '')],
     '<input type="hidden" class="js-upgrade-data" value=\'{"match_items":[{"name":"Aurora MR"}],"target_items":[{"name":"Avenger Titan"}]}\'>'),
]
TOTAL = 47

ITEM = """<li> <div class="row trans-03s trans-background "> <div class="basic-infos clearfix"> <div class="item-image-wrapper content-block3 "> <div class="image"></div>
<div class="corner corner-top-left"></div> <div class="corner corner-top-right"></div> <div class="corner corner-bottom-left"></div> <div class="corner corner-bottom-right"></div> </div>
<div class="wrapper-col"> <a class="arrow js-expand-arrow trans-02s"><span class="effect trans-02s trans-opacity"></span></a> <div class="title-col"> <div class="pledge-title-row"> <h3 class=""> {name} </h3> </div>
<input type="hidden" class="js-pledge-id" value="{id}"> <input type="hidden" class="js-pledge-name" value="{name}"> <input type="hidden" class="js-pledge-value" value="${value:.2f} USD">
<input type="hidden" class="js-pledge-configuration-value" value="$0.00 USD"> <input type="hidden" class="js-pledge-currency" value="Store Credit"> {extra} <span class="availability ">Attributed</span> </div>
<div class="date-col"> <label>Created:</label> {date} </div> <div class="items-col"> <label>Contains:</label> {contains} </div> </div> </div>
<div class="items more js-more trans-02s trans-height"> <h2>Items</h2> <a class="shadow-button trans-02s trans-color js-gift gift"><span class="label js-label trans-02s">Gift</span></a>
<div class="content-block1"> <div class="with-images"> {items} <div class="cboth"></div> </div> </div> </div> <div class="line"><div class="effect trans-02s trans-opacity"></div></div> </div> </li>"""

SUBITEM = '<div class="item "> <div class="text"> <div class="title">{title}</div> {kind} </div> </div>'


def pledge(i):
    name, value, items, extra = FIXTURES[i % len(FIXTURES)]
    if 'Coupon' in name:
        name = name.replace('0001', '%04d' % i).replace('0002', '%04d' % i)  # coupon codes are unique
    return ITEM.format(id=100000 - i, name=name, value=value, extra=extra, date='October %d, 2026' % (28 - i % 28),
                       contains=(items[0][0] + (' and %d items' % (len(items) - 1) if len(items) > 1 else '')) if items else name,
                       items=''.join(SUBITEM.format(title=t, kind='<div class="kind">%s</div>' % k if k else '') for t, k in items))


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
        if url.path == '/ship-matrix/index':
            with open(os.path.join(RSI, 'ship-matrix.json'), encoding='utf-8') as f:
                return self.send_body(f.read(), 'application/json')
        return super().do_GET()

    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length') or 0))
        if self.path.startswith('/api/account/pledgeLog'):
            return self.send_body(json.dumps({'success': 1, 'code': 'OK', 'data': {'rendered': 'x' * 200}}), 'application/json')
        self.send_error(404)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


if __name__ == '__main__':
    print('HangarXPLOR harness on http://localhost:%d/en/account/pledges?page=1' % PORT)
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
