#!/usr/bin/env python3
"""Guard repeated dnsmasq log-facility before daemon startup, not afterwards."""
import sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
path=root/'package/network/services/dnsmasq/files/dnsmasq.init'
text=path.read_text();marker='\tDEFAULT_INSTANCE=""\n\tconfig_load dhcp\n'
call='\t/usr/libexec/xg2010g-dnsmasq-log-guard || return 1\n'
if call not in text:
    assert text.count(marker)==1,'Unreviewed dnsmasq start layout'
    text=text.replace(marker,marker+call)
assert text.index(call)<text.index('\t\tdnsmasq_start "$instance"',text.index('start_service()'))
legacy = '\tprocd_add_jail_mount /etc/passwd /etc/group /etc/TZ /etc/hosts /etc/ethers'
modern = legacy + ' /etc/localtime /tmp/localtime'
if modern not in text:
    assert text.count(legacy) == 1, 'Unreviewed dnsmasq jail timezone mounts'
    text = text.replace(legacy, modern)
path.write_text(text)
print('DNS log-facility guard installed before daemon start; no restart loop')
