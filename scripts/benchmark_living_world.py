"""Compare two real checkouts in isolated Python processes, at identical workloads."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
CODE='''
import json,statistics,sys,time
sys.path.insert(0,sys.argv[1])
from ocdeck.jelly import Jelly,DeckGeometry
from ocdeck.world import World
from ocdeck.world_settings import settings
from ocdeck.world_weather import WeatherService
size,rows,cols=map(int,sys.argv[2:])
o=settings(dict(scene_override='autumn_rake',weather=False,auto_location=False,captions=False))
w=World(o,WeatherService(o));j=Jelly(DeckGeometry(rows,cols,size,size),6,options={'needs':False,'thoughts':'off'});j.settle(0,0)
free=set(range(rows*cols));samples=[];cold=None
for n in range(900):
 t=n/24;start=time.perf_counter();j.update(t,free);w.tick(t,j,free);w.decorate(t,j,j.crops(free),free);ms=(time.perf_counter()-start)*1000
 if cold is None and w.interaction.frame is not None:cold=ms
 if n>=60:samples.append(ms)
print(json.dumps(dict(size=size,keys=rows*cols,first_object_frame_ms=cold,median_ms=statistics.median(samples),mean_ms=statistics.mean(samples),p95_ms=sorted(samples)[int(len(samples)*.95)])))
'''
p=argparse.ArgumentParser();p.add_argument('--baseline-checkout',required=True);args=p.parse_args()
results=[]
for label,path in [('v3.0.13',Path(args.baseline_checkout).resolve()),('candidate',ROOT)]:
 for shape in [(72,2,3),(80,3,5),(96,4,8)]:
  result=json.loads(subprocess.check_output([sys.executable,'-c',CODE,str(path),*map(str,shape)],cwd='/tmp',text=True));result['implementation']=label;results.append(result)
report={'method':'Independent interpreter per checkout and layout; 900 frames at 24Hz simulated time; first 60 excluded from warm statistics; all keys free, seed 6, autumn_rake. First object frame has process-cold object caches; background caches may already be warm. CPU composition only, no USB. Behaviors differ because candidate completes travel and cleanup.', 'results':results}
(ROOT/'docs/jelly/living-previews/comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(results,indent=2))
