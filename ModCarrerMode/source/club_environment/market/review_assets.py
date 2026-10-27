"""Export only installed game artwork into the isolated review directory."""
from pathlib import Path
import io,json
from PIL import Image,ImageDraw
import portable_paths as portable

def export_assets(data,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    keys={'crest_'+str(data['clubId'])}
    for row in data['transfers']:
        keys.add('head_'+str(row['playerId']))
        for key in ('from','to'):
            keys.add('crest_'+str(row[key]['id']))
            if row[key]['leagueId']:keys.add('league_'+str(row[key]['leagueId']))
    if data['myLeague'].get('id'):keys.add('league_'+str(data['myLeague']['id']))
    assets={};report=[]
    for key in sorted(keys):
        kind,ident=key.split('_',1)
        candidates=(f'data/ui/imgAssets/heads/p{ident}.dds',) if kind=='head' else (
            f'data/ui/imgAssets/crest/light/l{ident}.dds',f'data/ui/imgAssets/crest/dark/l{ident}.dds') if kind=='crest' else (
            f'data/ui/imgAssets/careerCompetitionIcons/{ident}.png',f'data/ui/imgAssets/league/light/l{ident}.dds',f'data/ui/imgAssets/league/dark/l{ident}.dds')
        image=None;source=None
        for candidate in candidates:
            try:
                image=Image.open(io.BytesIO(portable.read_asset(candidate))).convert('RGBA');source=candidate;break
            except (OSError,ValueError):continue
        fallback=image is None
        if fallback:
            image=Image.new('RGBA',(128,128),(0,0,0,0));draw=ImageDraw.Draw(image)
            if kind=='head':
                draw.ellipse((40,12,88,60),fill='#9daeb6');draw.rounded_rectangle((18,66,110,124),22,fill='#9daeb6')
            elif kind=='league':
                draw.rounded_rectangle((39,18,89,77),8,fill='#a5b6bf');draw.rectangle((59,77,69,102),fill='#a5b6bf');draw.rectangle((41,101,87,111),fill='#a5b6bf')
            else:draw.polygon(((24,15),(104,15),(100,77),(64,113),(28,77)),fill='#b7c5cc')
        canvas=Image.new('RGBA',(160,160),(0,0,0,0));image.thumbnail((152,152),Image.Resampling.LANCZOS)
        canvas.alpha_composite(image,((160-image.width)//2,(160-image.height)//2))
        target=folder/(key+'.png');canvas.save(target)
        assets[key]=str(target);report.append(dict(key=key,source=source,fallback=fallback))
    return assets,report
