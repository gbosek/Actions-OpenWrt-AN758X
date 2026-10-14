#!/usr/bin/env python3
"""Block stock builds until all latest boost branch runs succeed."""
import argparse,json,os,time,urllib.request,urllib.error,http.client
from pathlib import Path

def choose_run(head,runs,workflow):
 matches=[r for r in runs if r['head_sha']==head and r.get('path','').split('@')[0]==workflow and r.get('event')=='push']
 return max(matches,key=lambda r:r['id']) if matches else None

def ready(run):
 return bool(run and run['status']=='completed' and run['conclusion']=='success')

def request(url):
 token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
 headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'XG2010G-build-queue'}
 if token:headers['Authorization']='Bearer '+token
 with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as r:return json.load(r)

def check(deps,fetch=request):
 states=[]
 for d in deps:
  base='https://api.github.com/repos/'+d['repository']
  head=fetch(base+'/branches/'+d['branch'])['commit']['sha']
  runs=fetch(base+'/actions/runs?branch='+d['branch']+'&head_sha='+head+'&event=push&per_page=10')['workflow_runs']
  run=choose_run(head,runs,d['workflow'])
  states.append({'repository':d['repository'],'branch':d['branch'],'head':head,'run_id':run['id'] if run else None,'status':run['status'] if run else 'not_started','conclusion':run['conclusion'] if run else None,'ready':ready(run)})
 return states

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--once',action='store_true');a=p.parse_args()
 deps=json.loads(a.manifest.read_text())['dependencies'];deadline=time.monotonic()+330*60
 while time.monotonic()<deadline:
  try:
   states=check(deps);print(json.dumps(states,ensure_ascii=False),flush=True)
   if all(s['ready'] for s in states):
    print('All four latest boost firmware builds succeeded. Stock builds may start.',flush=True);return
   if a.once:raise SystemExit(2)
  except (OSError,http.client.HTTPException,urllib.error.URLError,KeyError,json.JSONDecodeError) as e:
   print('Dependency check unavailable: '+str(e),flush=True)
   if a.once:raise SystemExit(3)
  time.sleep(60)
 raise SystemExit('Timed out waiting for boost firmware success; stock builds were not started.')
if __name__=='__main__':main()
