"""CPU-only warmed composition benchmark. Optional argv[1] selects a checkout."""
from pathlib import Path
import json
import statistics
import sys
import time
sys.path.insert(0,str(Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]))
from ocdeck.jelly import Jelly,DeckGeometry
from ocdeck.world import World
from ocdeck.world_settings import settings
from ocdeck.world_weather import WeatherService

report=[]
for size,rows,cols in ((72,2,3),(80,3,5),(96,4,8)):
    g=DeckGeometry(rows,cols,size,size)
    for scene in ('rain','snow','autumn_leaves'):
        o=settings(dict(scene_override=scene,weather=False,auto_location=False,props=False,captions=False))
        w=World(o,WeatherService(o));j=Jelly(g,seed=1);j.settle(0,0);w.tick(0,j)
        available=set(range(g.count));samples=[]
        for i in range(300):
            t=i/24;start=time.perf_counter()
            w.decorate(t,j,j.crops(available),available)
            if i>=60:samples.append((time.perf_counter()-start)*1000)
        report.append(dict(size=size,keys=g.count,scene=scene,median_ms=statistics.median(samples),p95_ms=sorted(samples)[int(.95*len(samples))]))
print(json.dumps(report,indent=2))
