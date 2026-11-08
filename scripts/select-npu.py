#!/usr/bin/env python3
from pathlib import Path
import argparse,shutil,json
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--variant',choices=['naoki'],required=True);a=p.parse_args();P=Path(__file__).resolve().parents[1];S=a.source.resolve();d=S/'package/custom/luci-app-airoha-npu'
if d.exists():shutil.rmtree(d)
shutil.copytree(P/'StableRefresh/packages/luci-app-airoha-npu',d)
meta={'upstream':'naoki66/luci-app-airoha','commit':'9263b4a64c5a76e51e9cafc88b5df432feec5ed4','upstream_version':'2.0.0-r9','cpu_control':'removed upstream'}
(S/'files/etc').mkdir(parents=True,exist_ok=True);(S/'files/etc/airoha-build-source.json').write_text(json.dumps(meta,indent=2)+'\n')
