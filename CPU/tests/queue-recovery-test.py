#!/usr/bin/env python3
"""Connection failures must keep stock builds blocked and retry the dependency check."""
from pathlib import Path
import importlib.util,tempfile,json,sys,http.client,io,contextlib
repo=Path(__file__).resolve().parents[2]
scripts=repo/('scripts' if (repo/'scripts/wait-for-boost.py').exists() else 'Scripts')
spec=importlib.util.spec_from_file_location('queue',scripts/'wait-for-boost.py');queue=importlib.util.module_from_spec(spec);spec.loader.exec_module(queue)
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'deps.json';p.write_text(json.dumps({'dependencies':[{'repository':'test/repo'}]}))
 outcomes=[http.client.RemoteDisconnected('Remote end closed connection without response'),ConnectionResetError('Reset'),http.client.IncompleteRead(b'partial',10),http.client.BadStatusLine('Malformed response'),TimeoutError('Timed out'),OSError('Transport failed'),[{'ready':False,'status':'in_progress'}],[{'ready':True,'status':'completed','conclusion':'success'}]*4]
 sleeps=[];checks=[]
 def fake_check(deps):
  checks.append(1);value=outcomes.pop(0)
  if isinstance(value,Exception):raise value
  return value
 queue.check=fake_check;queue.time.sleep=lambda seconds:sleeps.append(seconds)
 sys.argv=['wait-for-boost','--manifest',str(p)]
 output=io.StringIO()
 with contextlib.redirect_stdout(output):queue.main()
 assert not outcomes and len(checks)==8 and sleeps==[60]*7
 assert output.getvalue().count('Dependency check unavailable:')==6
 assert output.getvalue().count('All four latest boost firmware builds succeeded.')==1
 # A single check still reports unavailable and never starts builds on a broken API.
 queue.check=lambda deps: (_ for _ in ()).throw(http.client.RemoteDisconnected('Disconnected'))
 sys.argv+=['--once']
 try:
  with contextlib.redirect_stdout(io.StringIO()):queue.main()
 except SystemExit as e:assert e.code==3
 else:raise AssertionError('Unavailable API did not block the one-shot check')
print('PASS: disconnect/reset/truncated response/protocol/timeout errors retry; pending builds stay blocked until all four succeed')
