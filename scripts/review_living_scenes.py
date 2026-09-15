"""Exercise every real scene at all native layouts through its first outcome."""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw
from ocdeck.jelly import Jelly,DeckGeometry
from ocdeck.world import World
from ocdeck.world_settings import settings
from ocdeck.world_weather import WeatherService
from ocdeck.world_catalog import SCENES
OUT=Path(__file__).resolve().parents[1]/'docs/jelly/living-previews'
report=[]
for size,rows,cols in ((72,2,3),(80,3,5),(96,4,8)):
 thumbs=[]
 for scene in SCENES:
  o=settings(dict(scene_override=scene,weather=False,auto_location=False,captions=False));w=World(o,WeatherService(o));j=Jelly(DeckGeometry(rows,cols,size,size),6,options={'needs':False,'thoughts':'off'});j.settle(0,0)
  # An occupied middle key exercises layout clipping while leaving a route.
  free=set(range(j.geometry.count))-{1};stages=set();sample=None
  for n in range(1800):
   t=n/24;j.update(t,free);w.tick(t,j,free);stages.add(w.interaction.stage)
   if w.interaction.stage=='use' and w.interaction.objects[w.interaction.target].progress>.45 and sample is None:
    tiles=w.decorate(t,j,j.crops(free),free);assert set(tiles)<=free
    key=j.current;sample=tiles.get(key,Image.new('RGBA',(size,size)))
   if w.interaction.stage=='rest':break
  assert w.interaction.stage=='rest',(scene,size,stages)
  report.append(dict(scene=scene,size=size,stages=sorted(stages),completed=True))
  thumbs.append((scene,sample))
 for batch in range(0,len(thumbs),25):
  sheet=Image.new('RGB',(5*(size+50),5*(size+25)),'#09111b');d=ImageDraw.Draw(sheet)
  for i,(name,tile) in enumerate(thumbs[batch:batch+25]):
   x,y=(i%5)*(size+50),(i//5)*(size+25)
   if tile is not None:sheet.paste(tile,(x,y),tile)
   d.text((x,y+size+2),name,fill='white')
  sheet.save(OUT/f'scenes-{size}-{batch//25}.png')
(OUT/'scene-review.json').write_text(json.dumps(report,indent=2)+'\n');print(len(report),'scene/layout sequences completed')
