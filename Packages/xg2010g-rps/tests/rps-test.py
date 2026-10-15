from pathlib import Path
import os,subprocess,tempfile
p=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as d:
 r=Path(d);board=r/'board';board.write_text('gemtek,xg2010g\n');net=r/'net';sock=r/'sock';sock.write_text('0')
 def queue(port):
  q=net/port/'queues/rx-0';q.mkdir(parents=True);(q/'rps_cpus').write_text('0');(q/'rps_flow_cnt').write_text('0');return q
 q=queue('pon0')
 tune=r/'tune';tune.write_text((p/'files/rps-tune.sh').read_text().replace('/tmp/sysinfo/board_name',str(board)).replace('/sys/class/net',str(net)).replace('/proc/sys/net/core/rps_sock_flow_entries',str(sock)));tune.chmod(0o755)
 uci=r/'uci';uci.write_text('#!/bin/sh\necho 4096\n');uci.chmod(0o755)
 generic=r/'generic';generic.write_text('#!/bin/sh\necho "$*" >> "'+str(r/'generic.calls')+'"\n');generic.chmod(0o755)
 platform=r/'platform';platform.write_text((p/'files/packet-steering.sh').read_text().replace('/tmp/sysinfo/board_name',str(board)).replace('/usr/bin/rps-tune.sh',str(tune)).replace('/usr/libexec/network/packet-steering.uc',str(generic)))
 env=dict(os.environ,PATH=str(r)+':'+os.environ['PATH'])
 def run(mode):subprocess.run(['sh',str(platform),mode],env=env,check=True,timeout=3)
 run('2');assert (q/'rps_cpus').read_text().strip()=='f';assert (q/'rps_flow_cnt').read_text().strip()=='1024';assert sock.read_text().strip()=='4096'
 late=queue('lan1');run('2');assert (late/'rps_cpus').read_text().strip()=='f'
 (q/'rps_cpus').write_text('0');run('0');assert (q/'rps_cpus').read_text()=='0';assert '0' in (r/'generic.calls').read_text()
 make=(p/'Makefile').read_text();assert all(x not in make for x in ('rps-watch.sh','rps-guard.sh','xg2010g-rps.init','99-rps-guard'))
print('PASS: one-shot RPS, late interface event, off switch, no installed poller')
