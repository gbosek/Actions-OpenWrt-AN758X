#!/usr/bin/env python3
"""The pinned paired fork carries routing fixes; verify rather than re-patch."""
import sys
from pathlib import Path
from check_mwan4_pair import verify_sources
verify_sources(Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve(),Path(__file__).resolve().parents[1])
print('MWAN4 paired routing verified; no legacy patch or release downgrade applied')
