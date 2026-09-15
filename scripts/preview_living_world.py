"""Reproducible opt-in director reels; stage timing is saved outside device imagery."""
from pathlib import Path
import json
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from ocdeck.jelly import Jelly, DeckGeometry
from ocdeck.world import World
from ocdeck.world_settings import settings
from ocdeck.world_weather import WeatherService

OUT = Path(__file__).resolve().parents[1] / 'docs/jelly/living-previews'


def render(scene, size, rows, cols, takeover=False):
    g = DeckGeometry(rows, cols, size, size)
    options = settings(dict(living_world=True, scene_override=scene, weather=False, auto_location=False, captions=False))
    w = World(options, WeatherService(options))
    j = Jelly(g, seed=6, options={'thoughts':'off', 'needs':False})
    j.settle(0, 0)
    frames, timeline, durations = [], [], []
    claimed = None
    for i in range(480):
        now = i / 12
        free = set(range(g.count))
        if takeover and now > 12 and claimed is None and w.interaction.target:
            claimed = w.interaction.objects[w.interaction.target].home
        if claimed is not None:
            free.discard(claimed)
        start = time.perf_counter()
        j.update(now, free)
        w.tick(now, j, free)
        crops = w.decorate(now, j, j.crops(free), free)
        durations.append((time.perf_counter()-start)*1000)
        im = Image.new('RGB',g.size,'#09111b')
        for key in range(g.count):
            l,t,r,b=g.bounds(key)
            ImageDraw.Draw(im).rectangle((l,t,r-1,b-1),fill='#050910')
        for key,tile in crops.items():
            im.paste(tile,g.bounds(key)[:2],tile)
        if claimed is not None:
            l,t,r,b=g.bounds(claimed)
            ImageDraw.Draw(im).rectangle((l,t,r-1,b-1),fill='#123826',outline='#20eb75',width=2)
        frames.append(im)
        stage=w.interaction.stage or 'ordinary'
        if not timeline or timeline[-1]['stage']!=stage:
            timeline.append(dict(time=now,stage=stage,actor=j.current,target=w.interaction.key))
        if w.interaction.stage=='rest' and now > timeline[-1]['time']+3:
            break
    name=f'{scene}-{size}'+('-takeover' if takeover else '')
    temporary=OUT/f'{name}.tmp'
    frames[0].save(temporary,format='GIF',save_all=True,append_images=frames[1:],duration=83,loop=0)
    with Image.open(temporary) as check:
        check.seek(check.n_frames-1);check.load()
    temporary.replace(OUT/f'{name}.gif')
    picked=[]
    for row in timeline:
        i=min(len(frames)-1,round((row['time']+.4)*12))
        picked.append(frames[i])
    contact=Image.new('RGB',(g.size[0]*min(3,len(picked)),g.size[1]*((len(picked)+2)//3)),'#09111b')
    for i,im in enumerate(picked):contact.paste(im,(i%3*g.size[0],i//3*g.size[1]))
    contact.save(OUT/f'{name}.png')
    return dict(name=name,stage_timeline=timeline,frames=len(frames),mean_ms=sum(durations)/len(durations),max_ms=max(durations))


def main():
    OUT.mkdir(exist_ok=True)
    report=[]
    for scene in ('autumn_rake','autumn_cocoa'):
        for size,rows,cols in ((72,2,3),(80,3,5),(96,4,8)):
            report.append(render(scene,size,rows,cols))
    report.append(render('autumn_rake',72,2,3,True))
    (OUT/'timings.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
