"""Capture each complete production activity without labels on the device image."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from ocdeck.jelly import Jelly, DeckGeometry
from ocdeck.world_interactions import Interaction
from ocdeck.world_catalog import Scene
from ocdeck.world_objects import DEFINITIONS, ATMOSPHERES
from ocdeck.world_settings import settings
from ocdeck.world_environment import layers, SOURCED
from ocdeck.world_art import sky
OUT = Path(__file__).resolve().parents[1] / 'docs/jelly/living-previews'

def capture(name, size, atmosphere=''):
    j = Jelly(DeckGeometry(1,1,size,size), 6, options={'thoughts':'off','needs':False})
    j.settle(0,0)
    d=Interaction();s=Scene(name,'demo',prop=name,sky=atmosphere)
    opts=settings({'scene_override':'autumn_rake'})
    frames=[];picked={};timeline=[]
    for n in range(500):
        t=n/12;j.update(t,{0});d.tick(t,j,{0},'demo',s,opts)
        im=Image.new('RGBA',(size,size),'#050910')
        if atmosphere and atmosphere not in SOURCED:
            logical=Image.new('RGBA',(size//j.geometry.scale,size//j.geometry.scale))
            sky(ImageDraw.Draw(logical),atmosphere,*logical.size,int(t*8),'#83e6d4',seconds=t)
            im.alpha_composite(logical.resize((size,size),Image.Resampling.NEAREST))
        back,front=d.render_layers(j,{0})
        for layer in (layers(d,j,{0}),back,j.crops({0}),front):
            if 0 in layer:im.alpha_composite(layer[0])
        im=im.convert('RGB');frames.append(im)
        phase=d.stage
        if phase=='use':phase+='-'+str(min(3,int(d.objects[d.target].progress*4)))
        if phase not in picked:picked[phase]=im.copy();timeline.append((round(t,3),phase))
        if 'cleanup' in picked and not d.stage:break
    stem=(atmosphere+'-environment' if atmosphere else name)+'-'+str(size)
    temporary=OUT/(stem+'.tmp')
    frames[0].save(temporary,format='GIF',save_all=True,append_images=frames[1:],duration=83,loop=0)
    with Image.open(temporary) as check:
        check.seek(check.n_frames-1);check.load()
    temporary.replace(OUT/(stem+'.gif'))
    stages=['notice','reach','use-0','use-1','use-2','use-3','putdown','rest','cleanup']
    strip=Image.new('RGB',(size*len(stages),size),'#050910')
    for i,stage in enumerate(stages):
        if stage in picked:strip.paste(picked[stage],(i*size,0))
    return strip,{'name':name,'sky':atmosphere,'size':size,'timeline':timeline,'complete':bool('cleanup' in picked and not d.stage)}

def main():
    OUT.mkdir(exist_ok=True);report=[]
    for size in (72,80,96):
        rows=[]
        for name in DEFINITIONS:
            strip,record=capture(name,size);rows.append((name,strip));report.append(record)
        for batch in range(0,len(rows),10):
            page=Image.new('RGB',(size*9+90,(size+16)*len(rows[batch:batch+10])),'#09111b');draw=ImageDraw.Draw(page)
            for i,(name,strip) in enumerate(rows[batch:batch+10]):
                draw.text((3,i*(size+16)+8),name,fill='white');page.paste(strip,(90,i*(size+16)))
            page.save(OUT/f'review-{size}-{batch//10}.png')
    for size in (72,80,96):
        rows=[]
        for kind,name in ATMOSPHERES.items():
            strip,record=capture(name,size,kind);report.append(record);rows.append((kind,strip))
        for batch in range(0,len(rows),10):
            page=Image.new('RGB',(size*9+90,(size+16)*len(rows[batch:batch+10])),'#09111b');draw=ImageDraw.Draw(page)
            for i,(name,strip) in enumerate(rows[batch:batch+10]):
                draw.text((3,i*(size+16)+8),name,fill='white');page.paste(strip,(90,i*(size+16)))
            page.save(OUT/f'environment-review-{size}-{batch//10}.png')
    (OUT/'activity-timelines.json').write_text(json.dumps(report,indent=2)+'\n')
    print(len(report),'complete captures',sum(r['complete'] for r in report))
if __name__=='__main__':main()
