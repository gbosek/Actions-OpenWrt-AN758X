#!/usr/bin/env python3
"""Exercise feed pinning without contacting a device or cloning a build tree."""
import json, subprocess, sys, tempfile
from pathlib import Path

repo=Path(__file__).resolve().parents[1]
meta=json.loads((repo/'BASELINE-FEEDS.json').read_text())
with tempfile.TemporaryDirectory(prefix='offload-feed-test-') as folder:
    root=Path(folder)
    for override in (False, True):
        sources=dict(meta['feeds'])
        if override:sources['pon_userspace']=meta['naoki_onu_override']
        text='# retain comment\n'+''.join('src-git '+name+' '+source['url']+('^'+source['commit'] if override and name=='pon_userspace' else '')+'\n' for name,source in sources.items())+'src-link custom /tmp/custom\n'
        config=root/'feeds.conf.default';config.write_text(text)
        for repeat in range(2):
            subprocess.run([sys.executable,str(repo/'scripts/pin-offload-baseline.py'),str(root)],check=True)
        result=json.loads((root/'files/etc/firmware-feed-pins.json').read_text())
        assert result['selected']==sources
        assert config.read_text().startswith('# retain comment\n') and config.read_text().endswith('src-link custom /tmp/custom\n')
        for name,source in sources.items():assert 'src-git '+name+' '+source['url']+'^'+source['commit'] in config.read_text()
        changed=config.read_text().replace(meta['feeds']['packages']['url'],'https://example.invalid/other.git')
        config.write_text(changed)
        failure=subprocess.run([sys.executable,str(repo/'scripts/pin-offload-baseline.py'),str(root)],capture_output=True)
        assert failure.returncode and config.read_text()==changed
print('PASS: baseline and naoki ONU feeds, idempotent pinning, retained extras, unknown-source refusal')
