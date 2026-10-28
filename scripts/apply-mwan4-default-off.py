#!/usr/bin/env python3
"""Install default-off overlays around the already reviewed paired sources."""
import json,shutil,sys
from pathlib import Path
from check_mwan4_pair import verify_sources

def install(root):
    repo=Path(__file__).resolve().parents[1]
    verify_sources(root,repo)
    for rel in ('usr/libexec/xg2010g-mwan4-preset','etc/uci-defaults/99-xg2010g-mwan4-default-off','etc/config/mwan4'):
        src=repo/'files'/rel;dest=root/'files'/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        if src.resolve()!=dest.resolve():shutil.copyfile(src,dest)
        dest.chmod(0o644 if rel=='etc/config/mwan4' else 0o755)
    for rel in ('etc/uci-defaults/98-xg2010g-mwan4-defaults','usr/share/xg2010g/mwan4-stock.config'):
        (root/'files'/rel).unlink(missing_ok=True)
    dest=root/'files/etc/xg2010g-mwan4-source.json';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes((repo/'MWAN4-SOURCE.json').read_bytes())
    print('MWAN4 paired: exact source hashes; first boot stopped; no policy presets')

if __name__=='__main__':install(Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve())
