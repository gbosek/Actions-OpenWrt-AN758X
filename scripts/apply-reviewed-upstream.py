#!/usr/bin/env python3
"""Install exact reviewed maintenance backports after the guarded binding set."""
import hashlib,json,re,shutil,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[1];root=Path(sys.argv[1]).resolve()
meta=json.loads((repo/'Upstream/SOURCE.json').read_text())
assert re.search(r'^LINUX_VERSION-6\.18\s*:?=\s*\.55$',(root/'target/linux/generic/kernel-6.18').read_text(),re.M)
queue=root/'target/linux/airoha/patches-6.18'
assert len(list(queue.glob('954-*.patch')))==1,'RCU guarded baseline missing'
for item in meta['patches']:
	source=repo/'Upstream/patches'/item['file'];digest=hashlib.sha256(source.read_bytes()).hexdigest()
	assert digest==item['sha256'],source
	same=list(queue.glob(source.name[:4]+'*.patch'))
	assert not same or (len(same)==1 and same[0].name==source.name and same[0].read_bytes()==source.read_bytes()),'Conflicting prefix '+source.name
	subject=next(x for x in source.read_text().splitlines() if x.startswith('Subject:'))
	for parent in [root/'target/linux/generic',queue]:
		for other in parent.rglob('*.patch'):
			if other.name!=source.name:assert subject not in other.read_text(errors='replace'),'Duplicate upstream feature: '+str(other)
	shutil.copyfile(source,queue/source.name)
dest=root/'files/etc/xg2010g-upstream-source.json';dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(meta,indent=2)+'\n')
print('Installed reviewed flowtable and PON-only PPPoE MTU fixes; guarded PPE method retained')
