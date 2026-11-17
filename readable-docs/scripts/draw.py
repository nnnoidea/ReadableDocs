#!/usr/bin/env python3
"""Small JSON-to-SVG renderer. Python standard library; see references/drawing.md."""
import argparse
import collections
import json
import math
from pathlib import Path
import copy

from canvas import SVG, COLORS, esc, lines, nice_ticks


def flow(d):
    nodes = d['nodes']; ids = [n['id'] for n in nodes]
    if len(ids)!=len(set(ids)) or not ids:
        raise ValueError('nodes need unique ids')
    edges = d.get('edges', [])
    if any(e['from'] not in ids or e['to'] not in ids for e in edges):
        raise ValueError('unknown edge endpoint')
    parents = {e['to'] for e in edges}
    roots = [x for x in ids if x not in parents] or ids[:1]
    ranks = {x:0 for x in roots}; queue = collections.deque(roots)
    # ponytail: breadth-first ranks, not a crossing-minimizing graph layout engine.
    while queue:
        a = queue.popleft()
        for e in edges:
            if e['from']==a and e['to'] not in ranks:
                ranks[e['to']]=ranks[a]+1; queue.append(e['to'])
    for n in nodes:
        ranks[n['id']]=int(n.get('rank',ranks.get(n['id'],0)))
        if ranks[n['id']]<0:raise ValueError('rank must be nonnegative')
    groups = collections.defaultdict(list)
    for n in nodes:groups[ranks[n['id']]].append(n)
    width=max(620, max(map(len,groups.values()))*300+140)
    row_gap=max(150, max(len(lines(n['label'])) for n in nodes)*23+95)
    height=170+(max(groups)+1)*row_gap
    s=SVG(width,height,d.get('title',''),d.get('subtitle',''))
    pos={}
    for rank,items in groups.items():
        for col,n in enumerate(items):
            pos[n['id']]=(width*(col+1)/(len(items)+1),130+rank*row_gap,max(60,len(lines(n['label']))*23+24))
    for i,e in enumerate(edges):
        x,y,h=pos[e['from']];u,v,k=pos[e['to']]
        if e['from']==e['to']:
            points=[(x+115,y),(x+145,y),(x+145,y+h/2+32),(x,y+h/2+32),(x,y+h/2+5)]
            lx,ly=x+150,y+h/2+15
        elif v>y:
            mid=(y+v)/2
            points=[(x,y+h/2),(x,mid),(u,mid),(u,v-k/2-5)]
            lx,ly=(x+u)/2+8,mid-9
        else:
            channel=width-25-(i%3)*17
            points=[(x+115,y),(channel,y),(channel,v),(u+120,v)]
            lx,ly=channel-8,(y+v)/2-8
        s.path(points,True)
        if e.get('label'):s.text(lx,ly,e['label'],13,anchor='start' if v>y else 'end')
    for n in nodes:
        x,y,_=pos[n['id']];s.box(x,y,n['label'],kind=n.get('kind','box'))
    return s.finish(d.get('caption',''))


def lanes(d, sequence=False):
    names=d['participants' if sequence else 'lanes']; steps=d['messages' if sequence else 'steps']
    if not names or len(names)!=len(set(names)):raise ValueError('unique nonempty lanes required')
    if not steps:raise ValueError('steps/messages cannot be empty')
    width=max(650,len(names)*290+80)
    heights=[max(100,len(lines(t.get('note',t.get('label',t.get('text',''))),36))*23+55) for t in steps]
    s=SVG(width,170+sum(heights),d.get('title',''),d.get('subtitle',''))
    xs={n:40+(i+.5)*(width-80)/len(names) for i,n in enumerate(names)}
    for name,x in xs.items():
        s.path([(x,140),(x,s.height-55)],dash=True)
        s.box(x,112,name,width=min(240,(width-80)/len(names)-20))
    y=185; previous=None
    for step,gap in zip(steps,heights):
        if step.get('note'):
            s.box(width/2,y,step['note'],width=min(width-100,700),fill='#fff5dc')
        elif sequence:
            a,b=xs[step['from']],xs[step['to']]
            if a==b:s.path([(a,y),(a+90,y),(a+90,y+24),(a,y+24)],True)
            else:s.path([(a,y+20),(b,y+20)],True)
            for i,row in enumerate(lines(step['label'],max(24,int(abs(a-b)/9)))):
                s.text((a+b)/2,y-(len(lines(step['label'],max(24,int(abs(a-b)/9))))-1-i)*20,row,14)
        else:
            x=xs[step['lane']];h=max(60,len(lines(step['text']))*23+24)
            if previous:
                px,py,ph=previous;mid=(py+y)/2
                s.path([(px,py+ph/2),(px,mid),(x,mid),(x,y-h/2-4)],True)
                if step.get('edge_label'):s.text((px+x)/2+5,mid-7,step['edge_label'],13)
            s.box(x,y,step['text']);previous=(x,y,h)
        y+=gap
    return s.finish(d.get('caption',''))


def numbers(values):
    a=[float(x) for x in values]
    if not a or not all(math.isfinite(x) for x in a):raise ValueError('nonempty finite numbers required')
    return a


def quantile(a,p):
    a=sorted(a);i=(len(a)-1)*p;j=int(i)
    return a[j]+(a[min(j+1,len(a)-1)]-a[j])*(i-j)


def chart(d,kind):
    s=SVG(1000,max(650,210+len(d.get('values',[]))*35) if kind=='pie' else 650,d.get('title',''),d.get('subtitle',''))
    if kind=='pie':
        vals=numbers(d['values']);labels=d['labels']
        if len(labels)!=len(vals) or min(vals)<0 or sum(vals)<=0:raise ValueError('pie needs matching labels and nonnegative values with positive total')
        start=-math.pi/2;cx,cy,r=330,340,205
        for i,(label,val) in enumerate(zip(labels,vals)):
            if val==0:continue
            angle=val/sum(vals)*2*math.pi;end=start+angle;color=COLORS[i%len(COLORS)]
            if angle>=2*math.pi-1e-10:s.circle(cx,cy,r,color)
            else:
                x,y=cx+r*math.cos(start),cy+r*math.sin(start);u,v=cx+r*math.cos(end),cy+r*math.sin(end)
                s.parts.append(f'<path d="M{cx},{cy} L{x},{y} A{r},{r} 0 {int(angle>math.pi)} 1 {u},{v} Z" fill="{color}" stroke="white" stroke-width="2"/>')
            s.rect(610,140+i*35,16,16,fill=color,stroke=color,radius=2)
            s.text(640,154+i*35,f'{label}: {val:g} ({val/sum(vals):.1%})',15,anchor='start')
            start=end
        return s.finish(d.get('caption',''))
    left,right,top,bottom=100,940,110,515
    labels=d.get('labels',[])
    groups=None
    if kind=='histogram':
        data=numbers(d['values']);bins=int(d.get('bins',8))
        if not 1<=bins<=50:raise ValueError('bins must be 1..50')
        lo,hi=min(data),max(data)
        if lo==hi:lo-=.5;hi+=.5
        step=(hi-lo)/bins; vals=[0]*bins
        for x in data:vals[min(bins-1,int((x-lo)/step))]+=1
        labels=[f'{lo+i*step:.3g}–{lo+(i+1)*step:.3g}' for i in range(bins)]
        series=[{'y':vals}]
    elif kind=='boxplot':
        groups=[(g['label'],numbers(g['values'])) for g in d['groups']]
        if not groups:raise ValueError('groups cannot be empty')
        labels=[g[0] for g in groups];series=[{'y':[v for _,a in groups for v in a]}]
    else:
        series=d.get('series') or [{'name':d.get('name',''),'y':d.get('values',[]),'x':d.get('x')}]
    for v in series:v['y']=numbers(v['y'])
    all_y=[x for v in series for x in v['y']];low,high=min(all_y),max(all_y)
    if kind in ('bar','histogram'):low,high=min(0,low),max(0,high)
    if low==high:
        if kind in ('bar','histogram'):low,high=0,1
        else:low-=1;high+=1
    pad=(high-low)*.08
    if kind not in ('bar','histogram') or low!=0:low-=pad
    if kind not in ('bar','histogram') or high!=0:high+=pad
    Y=lambda y:bottom-(y-low)/(high-low)*(bottom-top)
    has_legend=any(v.get('name') for v in series)
    if has_legend:
        from layouts import legend
        top=legend(s,[v.get('name',f'组{i+1}') for i,v in enumerate(series)],x=left,width=right-left)+35
        bottom=max(bottom,top+300);s.height=max(s.height,bottom+130)
    for val in nice_ticks(low,high):
        y=Y(val)
        s.path([(left,y),(right,y)],color='#e2e7ef');s.text(left-12,y+5,f'{val:.4g}',13,anchor='end')
    s.path([(left,top),(left,bottom),(right,bottom)])
    if kind in ('bar','histogram'):
        s.path([(left,Y(0)),(right,Y(0))],color='#65768a')
    s.text(left,top-20,d.get('y_label',''),14,anchor='start')
    s.text((left+right)/2,bottom+85,d.get('x_label',''),15)
    if kind in ('bar','histogram','boxplot'):
        n=len(groups) if groups else len(series[0]['y'])
        if len(labels)!=n or any(len(v['y'])!=n for v in series) and not groups:raise ValueError('matching labels required')
        span=(right-left)/n
        for i,label in enumerate(labels):
            x=left+(i+.5)*span
            for j,line in enumerate(lines(label,max(5,int(span/8)))):s.text(x,bottom+23+j*17,line,12)
            if groups:
                vals=groups[i][1];q1,med,q3=[quantile(vals,p) for p in (.25,.5,.75)];iqr=q3-q1
                inner=[v for v in vals if q1-1.5*iqr<=v<=q3+1.5*iqr];lo,hi=min(inner),max(inner)
                s.path([(x,Y(lo)),(x,Y(hi))]);s.path([(x-15,Y(lo)),(x+15,Y(lo))]);s.path([(x-15,Y(hi)),(x+15,Y(hi))])
                s.rect(x-span*.22,Y(q3),span*.44,max(1,Y(q1)-Y(q3)))
                s.path([(x-span*.22,Y(med)),(x+span*.22,Y(med))])
                for v in vals:
                    if v<lo or v>hi:s.circle(x,Y(v),3)
            else:
                w=span*.75/len(series)
                for j,v in enumerate(series):
                    val=v['y'][i];z=Y(0)
                    s.rect(x-span*.375+j*w,min(Y(val),z),w*.92,abs(Y(val)-z),fill=COLORS[j%6],stroke='none',radius=0)
    else:
        for v in series:
            v['x']=numbers(v.get('x') or list(range(len(v['y']))))
            if len(v['x'])!=len(v['y']):raise ValueError('x/y lengths differ')
        all_x=[x for v in series for x in v['x']];lo,hi=min(all_x),max(all_x)
        if lo==hi:lo-=1;hi+=1
        X=lambda x:left+(x-lo)/(hi-lo)*(right-left)
        unique_x=sorted(set(all_x))
        if labels:
            if len(labels)!=len(series[0]['x']) or any(v['x']!=series[0]['x'] for v in series):
                raise ValueError('Labels require matching shared x positions')
            ticks=list(zip(series[0]['x'],labels))
        else:ticks=[(v,f'{v:.4g}') for v in (unique_x if len(unique_x)<=8 else nice_ticks(lo,hi))]
        for x,label in ticks:s.text(X(x),bottom+25,label,12)
        for i,v in enumerate(series):
            pts=list(zip(map(X,v['x']),map(Y,v['y'])))
            if kind=='line':s.path(pts,color=COLORS[i%6])
            for x,y in pts:s.circle(x,y,4,COLORS[i%6])
    return s.finish(d.get('caption',''))


def render(data):
    data=copy.deepcopy(data)
    if 'template' in data:
        # Resolve layout only: example business data must never fill missing input.
        template=load_template(data.pop('template'));kind=template['type']
        if data.get('type',kind)!=kind:raise ValueError('type conflicts with template')
        data['type']=kind
        for key in ('normalize','columns','display_scale','show_values'):
            if key in template:data.setdefault(key,template[key])
    kind=data['type']
    if kind in ('flow','hierarchy','state'):return flow(data)
    if kind in ('sequence','swimlane'):return lanes(data,kind=='sequence')
    if kind in ('pie','bar','line','scatter','histogram','boxplot'):return chart(data,kind)
    from layouts import render_extra
    return render_extra(data,render)


TEMPLATES=Path(__file__).resolve().parent.parent/'assets'/'templates'


def load_template(name):
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name):
        raise ValueError('Use a template name from --list')
    path=TEMPLATES/(name+'.json')
    if not path.is_file():raise ValueError(f'Unknown template {name!r}; run --list')
    return json.loads(path.read_text())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path,nargs='?');p.add_argument('output',type=Path,nargs='?')
    p.add_argument('--list',action='store_true',help='List available content templates')
    p.add_argument('--template',help='Print a complete editable JSON template')
    p.add_argument('--gallery',type=Path,help='Render all examples and a local HTML index')
    a=p.parse_args()
    if sum([a.list,bool(a.template),bool(a.gallery)])>1:p.error('Choose one of --list, --template, --gallery')
    if a.list:
        for path in sorted(TEMPLATES.glob('*.json')):
            d=json.loads(path.read_text());print(f'{path.stem:24} {d["title"]}')
        return
    if a.template:
        print(json.dumps(load_template(a.template),ensure_ascii=False,indent=2));return
    if a.gallery:
        a.gallery.mkdir(parents=True,exist_ok=True);cards=[]
        for path in sorted(TEMPLATES.glob('*.json')):
            d=json.loads(path.read_text());svg=render(d);(a.gallery/(path.stem+'.svg')).write_text(svg)
            (a.gallery/path.name).write_text(json.dumps(d,ensure_ascii=False,indent=2))
            cards.append(f'<section><h2>{esc(d["title"])}</h2><p><a href="{path.name}">填内容 JSON</a> · <a href="{path.stem}.svg">SVG</a></p><img src="{path.stem}.svg" alt="{esc(d["title"])}" loading="lazy"></section>')
        page='<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ReadableDocs 模板样例</title><style>body{font:16px system-ui;color:#203449;background:#f1f6fa;max-width:1100px;margin:auto;padding:24px}section{background:white;padding:20px;margin:24px 0;border:1px solid #d8e2ea;border-radius:12px}img{width:100%;height:auto}a{color:#28679b}</style><h1>ReadableDocs 模板样例</h1><p>全部内容和数据均为示例；正式使用时替换为有依据的材料。</p>'+''.join(cards)+'</html>'
        (a.gallery/'index.html').write_text(page);print(a.gallery/'index.html');return
    if not a.input or not a.output:p.error('Provide input.json output.svg, or use --list / --template / --gallery')
    try:data=json.loads(a.input.read_text());svg=render(data)
    except (ValueError,KeyError,TypeError) as error:p.error(str(error))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(svg)
    print(a.output)


if __name__=='__main__':main()
