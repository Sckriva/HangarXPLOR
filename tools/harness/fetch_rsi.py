"""Download the public RSI assets the harness needs into tools/harness/rsi/ (not versioned: they belong to RSI).

    python tools/harness/fetch_rsi.py

The rsi.core / rsi.account bundle names carry a build hash and only appear on the logged-in hangar page.
When RSI ships a new build, the old URLs may stop working: open the hangar page while logged in,
copy the new URLs from the page's <script> tags, and pass them as arguments:

    python tools/harness/fetch_rsi.py https://static.robertsspaceindustries.com/rsi/static/packages/core/rsi.core.build.XXXXX.js ...
"""
import os, re, sys, urllib.request

RSI = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rsi')
SITE = 'https://robertsspaceindustries.com'
PACKAGES = 'https://static.robertsspaceindustries.com/rsi/static/packages/'

# Last known bundle URLs (October 2026). Arguments override them.
BUNDLES = {
    'rsi.core.js': PACKAGES + 'core/rsi.core.build.688f3.js',
    'rsi.account.js': PACKAGES + 'account/rsi.account.build.bc2e4.js',
}


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def save(name, data):
    with open(os.path.join(RSI, name), 'wb') as f:
        f.write(data)
    print('%-22s %8d bytes' % (name, len(data)))


def main():
    os.makedirs(RSI, exist_ok=True)
    for url in sys.argv[1:]:
        kind = re.search(r'/(core|account)/', url)
        if not kind:
            sys.exit('Unrecognised bundle URL: ' + url)
        BUNDLES['rsi.%s.js' % kind.group(1)] = url

    # The public (logged-out) hangar page still references the shared bundles and stylesheets
    page = get(SITE + '/en/account/pledges').decode('utf-8', 'replace')
    for name, pattern in [('rsi-external-js.js', r'/cache/en/rsi-external-js\.js\?v=[\d.]+'),
                          ('rsi-templates-js.js', r'/cache/en/rsi-templates-js\.js\?v=[\d.]+'),
                          ('rsi-css.css', r'/cache/en/rsi-css\.css\?v=[\d.]+'),
                          ('fonts.css', r'/rsi/assets/fonts\.css\?[^"]+')]:
        m = re.search(pattern, page)
        if not m:
            sys.exit('Could not find %s on the hangar page; RSI changed its markup.' % name)
        save(name, get(SITE + m.group(0).replace('&amp;', '&')))

    for name, url in BUNDLES.items():
        save(name, get(url))
    save('ship-matrix.json', get(SITE + '/ship-matrix/index'))


if __name__ == '__main__':
    main()
