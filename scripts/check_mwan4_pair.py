#!/usr/bin/env python3
"""Check the actual complete pair, including code hashes and Chinese catalog."""
import hashlib,json,re
from pathlib import Path

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify_sources(root,repo):
    meta=json.loads((repo/'MWAN4-SOURCE.json').read_text())
    for kind,name in [('backend','mwan4'),('frontend','luci-app-mwan4')]:
        package=root/'package/custom'/name
        release=meta[kind]['version'].rsplit('-r',1)[1]
        assert re.search(r'^PKG_RELEASE:='+release+r'$',(package/'Makefile').read_text(),re.M),'Unexpected package release: '+name
        for rel,sha in meta[kind]['installed_files_sha256'].items():
            src=package/('files/'+rel if kind=='backend' else 'htdocs/'+rel[4:] if rel.startswith('www/') else 'root/'+rel)
            assert digest(src)==sha,'Paired source differs: '+str(src)
    frontend=root/'package/custom/luci-app-mwan4'
    assert digest(frontend/'po/zh_Hans/mwan4.po')==meta['frontend']['po_sha256'],'Chinese source catalog differs'
    assert (root/'package/custom/mwan4/files/etc/config/mwan4').read_bytes()==(repo/'files/etc/config/mwan4').read_bytes(),'Fresh config differs'
    return meta

def verify_installed(installed,repo):
    meta=json.loads((repo/'MWAN4-SOURCE.json').read_text())
    for kind in ('backend','frontend'):
        for rel,sha in meta[kind]['installed_files_sha256'].items():
            assert digest(installed/rel)==sha,'Installed pair differs: '+rel
    assert digest(installed/'usr/lib/lua/luci/i18n/mwan4.zh-cn.lmo')==meta['translation']['lmo_sha256'],'Complete Chinese LMO differs'
    assert json.loads((installed/'etc/xg2010g-mwan4-source.json').read_text())==meta,'Installed paired provenance differs'
    print('PASS: paired backend/frontend installed file hashes and complete Chinese LMO')
