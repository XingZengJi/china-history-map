import json,sys,os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from shapely.geometry import shape
fp=fm.FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
P=json.load(open('scripts/polities.json')); meta=json.load(open('build/geo/frames_meta.json'))
land=shape(json.load(open('build/geo/land.geojson'))['features'][0]['geometry'])
COL=['#c8452f','#3d6b9c','#4f8f73','#d9a441','#a8754a','#7d5a8c','#b9b3a4','#9aa5a8','#a9b59c']
sel=[int(x) for x in sys.argv[2:]] or range(len(meta))
which=sys.argv[1]  # 'mid' or 'end' or 'start'
n=len(sel); cols=3; rows=(n+cols-1)//cols
fig,axs=plt.subplots(rows,cols,figsize=(cols*8,rows*5.4)); axs=axs.flatten()
missing=set()
for ax,i in zip(axs,sel):
    m=meta[i]; y={'mid':(m['y0']+m['y1'])//2,'end':m['y1'],'start':m['y0']}[which]
    for g in land.geoms:
        xs,ys=g.exterior.xy; ax.fill(xs,ys,color='#eee',ec='#999',lw=.3)
    fc=json.load(open(f'build/geo/frame_{i}.geojson'))
    for ft in fc['features']:
        st=ft['properties']['st']; cur=None
        for s in st:
            if s[0]<=y: cur=s
        if not cur or cur[1] is None: continue
        if cur[1] not in P: missing.add(cur[1]); continue
        nm=cur[2] if len(cur)>2 and cur[2] is not None else P[cur[1]][0]
        loose=ft['properties']['loose'] or (len(cur)>3 and cur[3])
        g=shape(ft['geometry']); gs=[g] if g.geom_type=='Polygon' else list(g.geoms)
        for p in gs:
            xs,ys=p.exterior.xy; ax.fill(xs,ys,color=COL[P[cur[1]][1]],alpha=.35 if loose else .75,ec='k',lw=.4,hatch='///' if loose else None)
        lp=ft['properties']['lp']
        if lp and nm: ax.text(lp[0],lp[1],nm,fontproperties=fp,fontsize=8,ha='center',va='center')
    for t in m['texts']: ax.text(t[1],t[2],t[0],fontproperties=fp,fontsize=7,ha='center',color='#333')
    ax.set_xlim(70,142); ax.set_ylim(15,56); ax.set_aspect(1.25); ax.set_title(f"#{i} {m['y0']}..{m['y1']} @ {y}  {m['snap']}",fontproperties=fp)
print('missing keys',missing)
plt.tight_layout(); plt.savefig(f'qa_{which}_{sel[0]}.png',dpi=62)
