"""Native production weather reels, floor-contact studies and comparative timings."""
from pathlib import Path
import json
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFont
from ocdeck.world import World
from ocdeck.world_settings import settings
from ocdeck.world_weather import WeatherService
from ocdeck.jelly import Jelly,DeckGeometry
from ocdeck.world_particles import atmosphere,particles

OUT=Path(__file__).resolve().parents[1]/'docs/jelly/weather'


def main():
    OUT.mkdir(exist_ok=True)
    report=[]
    for size,rows,cols in ((72,2,3),(80,3,5),(96,4,8)):
        g=DeckGeometry(rows,cols,size,size)
        worlds=[]
        for scene in ('rain','snow','autumn_leaves'):
            o=settings(dict(scene_override=scene,auto_location=False,weather=False,props=False,interactions=False,captions=False,costumes=False))
            j=Jelly(g,seed=1,options={'thoughts':'off'});j.settle(0,0)
            w=World(o,WeatherService(o));w.tick(0,j)
            worlds.append((w,j))
        frames=[];cost=[]
        # Two free cells, one occupied cell: label-free native rendered weather.
        for frame in range(240):
            t=frame/24
            sheet=Image.new('RGB',(size*3+16,size*3+16),'#09111b')
            for row,(w,j) in enumerate(worlds):
                start=time.perf_counter();crops=w.decorate(t,j,j.crops({0,1}),{0,1});cost.append((time.perf_counter()-start)*1000)
                for key in (0,1):
                    tile=Image.new('RGBA',(size,size),'#050910')
                    if key in crops:tile.alpha_composite(crops[key])
                    sheet.paste(tile.convert('RGB'),(key*(size+8),row*(size+8)))
                d=ImageDraw.Draw(sheet);x=2*(size+8);y=row*(size+8)
                d.rectangle((x,y,x+size-1,y+size-1),fill='#10321f',outline='#20eb75',width=2)
                d.text((x+size/2,y+size/2),'AGENT',anchor='mm',fill='#83e6d4',font=ImageFont.load_default(size=10))
            frames.append(sheet)
        frames[0].save(OUT/f'particles-{size}.gif',save_all=True,append_images=frames[1:],duration=[50 if i%6==5 else 40 for i in range(len(frames))],loop=0)
        frames[100].save(OUT/f'particles-{size}.png')
        report.append(dict(size=size,geometry=[rows,cols],frames=len(frames),mean_ms=sum(cost)/len(cost),max_ms=max(cost)))
    # Temporal studies isolate a single identity's floor contact, drawn by production art.
    for kind in ('rain','snow','leaves'):
        selected=[]
        for i in range(1200):
            ps=particles(kind,40,40,i/60,seed=17)
            p=next((p for p in ps if p.index==0 and p.cycle==1),None)
            if p and ((p.stage=='fall' and p.progress>.85) or p.stage!='fall'):
                selected.append((i/60,p.stage))
        indices=[round(i*(len(selected)-1)/7) for i in range(8)]
        sheet=Image.new('RGB',(8*80,100),'#09111b')
        for col,index in enumerate(indices):
            t,stage=selected[index]
            tile=Image.new('RGBA',(40,40));atmosphere(ImageDraw.Draw(tile),kind,40,40,t,seed=17)
            sheet.paste(tile.resize((80,80),Image.Resampling.NEAREST),(col*80,20),tile.resize((80,80),Image.Resampling.NEAREST))
            ImageDraw.Draw(sheet).text((col*80+2,2),f'{stage} {t:.1f}',fill='white')
        sheet.save(OUT/f'{kind}-contact.png')
    (OUT/'render-metrics.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
