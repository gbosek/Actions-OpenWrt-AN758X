#!/usr/bin/env python3
import json,subprocess,sys,tempfile
from pathlib import Path
repo=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='xg-upstream-install-') as d:
    root=Path(d);queue=root/'target/linux/airoha/patches-6.18';queue.mkdir(parents=True)
    p=root/'target/linux/generic/kernel-6.18';p.parent.mkdir(parents=True);p.write_text('LINUX_VERSION-6.18 = .55\n')
    (queue/'954-rcu.patch').write_text('retained RCU prerequisite\n')
    script=repo/'scripts/apply-reviewed-upstream.py'
    for _ in range(2):subprocess.run([sys.executable,str(script),str(root)],check=True)
    patches=sorted(queue.glob('95[5-7]-*.patch'));assert len(patches)==3
    patches[0].write_text('conflicting source\n')
    assert subprocess.run([sys.executable,str(script),str(root)],capture_output=True).returncode!=0
    patches[0].unlink()
    original=repo/'Upstream/patches/955-netfilter-flowtable-revoke-moved-bridge-destinations.patch'
    (root/'target/linux/generic/708-duplicate.patch').write_bytes(original.read_bytes())
    assert subprocess.run([sys.executable,str(script),str(root)],capture_output=True).returncode!=0
    dns=root/'package/network/services/dnsmasq/files/dnsmasq.init';dns.parent.mkdir(parents=True)
    dns.write_text('start_service() {\n\tDEFAULT_INSTANCE=""\n\tconfig_load dhcp\n\tif true; then\n\t\tdnsmasq_start "$instance"\n\tfi\n}\n')
    for _ in range(2):subprocess.run([sys.executable,str(repo/'scripts/apply-dnsmasq-log-guard.py'),str(root)],check=True)
    assert dns.read_text().count('xg2010g-dnsmasq-log-guard')==1
    for _ in range(2):subprocess.run([sys.executable,str(repo/'scripts/apply-requested-extras.py'),str(root)],check=True)
    assert (root/'package/custom/luci-app-clients/root/usr/libexec/clients-probe').stat().st_mode&0o111
    msd = root/'package/custom/msd_lite'
    meta=json.loads((repo/'Packages/Extras/SOURCE.json').read_text())['source_repositories']['msd_lite']
    import hashlib
    for rel,digest in meta['files_sha256'].items():
        assert hashlib.sha256((msd/rel).read_bytes()).hexdigest()==digest,rel
    assert "option 'enabled' '0'" in (msd/'files/msd_lite.config').read_text()
    duplicate=root/'feeds/packages/net/msd_lite/Makefile';duplicate.parent.mkdir(parents=True)
    duplicate.write_text((msd/'Makefile').read_text())
    assert subprocess.run([sys.executable,str(repo/'scripts/apply-requested-extras.py'),str(root)],capture_output=True).returncode!=0
print('PASS: patch installer idempotency, prefix/semantic duplicate rejection, DNS hook and extras install')
