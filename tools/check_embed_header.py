#!/usr/bin/env python3
"""Before a deploy: will the pages that embed this site still be allowed to?

Other sites show this one inside a frame. The live site tells browsers who may do
that with one response header (Content-Security-Policy: frame-ancestors ...), set
in netlify.toml. If a deploy ships a shorter list, the dropped pages show a blank
frame and nothing errors on this side.

This script compares the list in the local netlify.toml with the list the live
site serves right now. It reads only; it changes nothing.

    python3 tools/check_embed_header.py
    python3 tools/check_embed_header.py https://some-preview--datavault-foundations.netlify.app

Exit 0: every origin allowed live today is still allowed by the local file.
Exit 1: the local file would drop at least one origin (they are listed).
"""
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = sys.argv[1] if len(sys.argv) > 1 else 'https://datavault-foundations.netlify.app/'


def ancestors(csp):
    m = re.search(r'frame-ancestors\s+([^;]+)', csp or '')
    return set(m.group(1).split()) if m else set()


toml = open(os.path.join(ROOT, 'netlify.toml'), encoding='utf-8').read()
m = re.search(r'^\s*Content-Security-Policy\s*=\s*"([^"]*)"', toml, flags=re.M)
local = ancestors(m.group(1) if m else '')

req = urllib.request.Request(LIVE, headers={'User-Agent': 'Mozilla/5.0 embed-header-check'})
with urllib.request.urlopen(req, timeout=30) as r:
    live_csp = r.headers.get('Content-Security-Policy', '')
live = ancestors(live_csp)

print('live  :', ' '.join(sorted(live)) or '(no frame-ancestors header)')
print('local :', ' '.join(sorted(local)) or '(no frame-ancestors in netlify.toml)')
if not live:
    print('NOTE: the address checked sends no frame-ancestors list at all. Any page may frame it, '
          'so nothing is blocked, but netlify.toml was not applied to that deploy.')
dropped = sorted(live - local)
added = sorted(local - live)
if added:
    print('local adds:', ' '.join(added))
if dropped:
    print('WOULD DROP:', ' '.join(dropped))
    print('A deploy from this folder would blank the frame on those pages.')
    sys.exit(1)
print('OK: a deploy from this folder keeps every origin that is allowed today.')
