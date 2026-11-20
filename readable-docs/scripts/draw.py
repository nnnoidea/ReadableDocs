#!/usr/bin/env python3
"""Small JSON-to-SVG renderer. Python standard library; see references/drawing.md."""
import argparse
import collections
import json
import math
from pathlib import Path
import copy

from structures import connect_objects, cell_height, paint_cell, identity_colors
from canvas import SVG, COLORS, INK, MUTED, GRID, CONTEXT, ACCENT, esc, lines, nice_ticks, item_color, label_indices, box_rows, text_width


def flow(d):
    nodes = d['nodes']; ids = [n['id'] for n in nodes]
    identity_colors(d,nodes)
    if len(ids)!=len(set(ids)) or not ids:
        raise ValueError('nodes need unique ids')
    edges = d.get('edges', [])
    path=d.get('focus_path',[])
    if not isinstance(path,list) or any(v not in ids for v in path):raise ValueError('focus_path must list existing node IDs')
    pairs=list(zip(path,path[1:]))
    if any(not any(e['from']==a and e['to']==b for e in edges) for a,b in pairs):raise ValueError('focus_path must follow existing directed edges')
    for n in nodes:
        if n['id'] in path:n['emphasis']=True
    for e in edges:
        if (e['from'],e['to']) in pairs:e['emphasis']=True
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
    incoming={i:{e['from'] for e in edges if e['to']==i and not e.get('feedback')} for i in ids}
    remaining=list(ids);dag={}
    while remaining:
        ready=[i for i in remaining if not incoming[i].intersection(remaining)]
        if not ready:break
        for i in ready:dag[i]=max([0]+[dag[p]+1 for p in incoming[i]])
        remaining=[i for i in remaining if i not in ready]
    if not remaining:ranks=dag
    for n in nodes:
        ranks[n['id']]=int(n.get('rank',ranks.get(n['id'],0)))
        if ranks[n['id']]<0:raise ValueError('rank must be nonnegative')
    groups = collections.defaultdict(list)
    for n in nodes:groups[ranks[n['id']]].append(n)
    visual=lambda n:any(k in n for k in ('symbol','detail','presentation'))
    sizes={n['id']:(cell_height(n,230) if visual(n) else box_rows(n['label'],kind=n.get('kind','box'))[1]) for n in nodes}
    chain=(len(nodes)<=4 and len(edges)==len(nodes)-1 and len(groups)==len(nodes)
           and all(ranks[e['to']]==ranks[e['from']]+1 for e in edges))
    direction=d.get('direction','auto')
    if direction not in ('auto','horizontal','vertical'):raise ValueError('direction must be auto, horizontal or vertical')
    horizontal=chain and direction!='vertical'
    width=max(620, max(map(len,groups.values()))*300+140)
    centers={};bottom=100
    edge_space=max([70]+[len(lines(e.get('label',''),25))*19+35 for e in edges])
    for rank in sorted(groups):
        h=max(sizes[n['id']] for n in groups[rank]);centers[rank]=bottom+h/2;bottom+=h+edge_space
    height=bottom-edge_space+40
    horizontal_gap=max([64]+[min(180,text_width(e.get('label',''),13)+24) for e in edges])
    if horizontal:width=max(620,len(nodes)*230+(len(nodes)-1)*horizontal_gap+80);height=170+max(sizes.values())
    s=SVG(width,height,d.get('title',''),d.get('subtitle',''))
    pos={}
    for rank,items in groups.items():
        for col,n in enumerate(items):
            pos[n['id']]=(40+115+rank*(230+horizontal_gap)+(width-(len(nodes)*230+(len(nodes)-1)*horizontal_gap+80))/2,110+max(sizes.values())/2,sizes[n['id']]) if horizontal else (width*(col+1)/(len(items)+1),centers[rank],sizes[n['id']])
    if not chain:
        if direction=='horizontal':
            ranked=sorted(groups);width=len(ranked)*350+140
            height=max(sum(sizes[n['id']]+80 for n in group) for group in groups.values())+170
            s.width,s.height=width,height
            for col,rank in enumerate(ranked):
                top=130
                for n in groups[rank]:
                    h=sizes[n['id']];pos[n['id']]=(185+col*350,top+h/2,h);top+=h+80
        else:
            s.width+=80;s.height+=80
            pos={key:(x+40,y+20,h) for key,(x,y,h) in pos.items()}
    connect_objects(s,nodes,{key:(x-115,y-h/2,230,h) for key,(x,y,h) in pos.items()},edges)
    for n in nodes:
        x,y,h=pos[n['id']]
        if visual(n):paint_cell(s,n,(x-115,y-h/2,230,h))
        else:s.box(x,y,n['label'],kind=n.get('kind','box'),emphasis=n.get('emphasis',False))
    return s.finish(d.get('caption',''))


def lanes(d, sequence=False):
    names=d['participants' if sequence else 'lanes']; steps=d['messages' if sequence else 'steps']
    if not names or len(names)!=len(set(names)):raise ValueError('unique nonempty lanes required')
    if not steps:raise ValueError('steps/messages cannot be empty')
    width=max(650,len(names)*290+80)
    xs={n:40+(i+.5)*(width-80)/len(names) for i,n in enumerate(names)}
    header_width=min(240,(width-80)/len(names)-20)
    header_h=max(box_rows(name,header_width)[1] for name in names)
    header_y=100+header_h/2
    positions=[];cursor=100+header_h+35
    for step in steps:
        if step.get('note'):h=box_rows(step['note'],min(width-100,700))[1]
        elif sequence:
            if step['from'] not in xs or step['to'] not in xs:raise ValueError('Unknown message participant')
            label_width=max(24,int(abs(xs[step['from']]-xs[step['to']])/9))
            h=len(lines(step['label'],label_width))*21+42
        else:
            if step['lane'] not in xs:raise ValueError('Unknown lane')
            h=box_rows(step['text'])[1]
        before=max(35,len(lines(step.get('edge_label',''),24))*19+20)
        if positions:cursor+=before
        positions.append((cursor,h));cursor+=h
    s=SVG(width,cursor+45,d.get('title',''),d.get('subtitle',''))
    for name,x in xs.items():
        s.path([(x,header_y+header_h/2),(x,s.height-25)],dash=True,color=GRID)
        s.box(x,header_y,name,width=header_width)
    previous=None
    for step,(top,h) in zip(steps,positions):
        y=top+h/2
        if step.get('note'):
            s.box(width/2,y,step['note'],width=min(width-100,700),fill='#fff5dc',emphasis=step.get('emphasis',False))
        elif sequence:
            a,b=xs[step['from']],xs[step['to']]
            rows=lines(step['label'],max(24,int(abs(a-b)/9)));line_y=top+len(rows)*21+6
            if a==b:s.path([(a,line_y),(a+90,line_y),(a+90,line_y+24),(a,line_y+24)],True,color=ACCENT if step.get('emphasis') else MUTED)
            else:s.path([(a,line_y),(b,line_y)],True,color=ACCENT if step.get('emphasis') else MUTED)
            for i,row in enumerate(rows):s.text((a+b)/2,top+15+i*21,row,15)
        else:
            x=xs[step['lane']]
            if previous:
                px,py,ph=previous;mid=(py+ph/2+top)/2
                s.path([(px,py+ph/2),(px,mid),(x,mid),(x,top-4)],True,color=ACCENT if step.get('emphasis') else MUTED)
                if step.get('edge_label'):
                    label_h=(len(lines(step['edge_label'],24))-1)*19
                    s.paragraph((px+x)/2+8,mid-8-label_h,step['edge_label'],180,13)
            s.box(x,y,step['text'],emphasis=step.get('emphasis',False));previous=(x,y,h)
    return s.finish(d.get('caption',''))


def numbers(values):
    a=[float(x) for x in values]
    if not a or not all(math.isfinite(x) for x in a):raise ValueError('nonempty finite numbers required')
    return a


def quantile(a,p):
    a=sorted(a);i=(len(a)-1)*p;j=int(i)
    return a[j]+(a[min(j+1,len(a)-1)]-a[j])*(i-j)


def chart(d,kind):
    if kind=='bar':
        orientation=d.get('orientation','auto')
        if orientation not in ('auto','horizontal','vertical'):raise ValueError('orientation must be auto, horizontal or vertical')
        labels=d.get('labels',[])
        if orientation=='horizontal' or (orientation=='auto' and (len(labels)>6 or any(text_width(v)>110 for v in labels))):
            from layouts import horizontal_bar
            return horizontal_bar(d)
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
    if kind=='bar':
        s.width=max(680,min(1000,180+len(labels)*160));s.height=460
        right=s.width-60;bottom=345
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
    direct=kind=='line' and len(series)<=6
    if direct:
        endpoints=[(v.get('x') or list(range(len(v['y']))))[-1] for v in series]
        direct=all(v==endpoints[0] for v in endpoints) and all(max(v.get('x') or list(range(len(v['y']))))==endpoints[0] for v in series)
    if direct:right=735
    has_legend=not direct and len(series)>1 and any(v.get('name') for v in series)
    if has_legend:
        from layouts import legend
        top=legend(s,[v.get('name',f'组{i+1}') for i,v in enumerate(series)],x=left,width=right-left,
                   colors=[item_color(series,v,i,d.get('color_map')) for i,v in enumerate(series)],line=kind in ('line','scatter'))+35
        bottom=max(bottom,top+(220 if kind=='bar' else 300));s.height=max(s.height,bottom+115)
    for val in nice_ticks(low,high):
        y=Y(val)
        s.path([(left,y),(right,y)],color=GRID,weight=1);s.text(left-12,y+5,f'{val:.4g}',13,anchor='end')
    s.path([(left,top),(left,bottom),(right,bottom)])
    if kind in ('bar','histogram'):
        s.path([(left,Y(0)),(right,Y(0))],color='#65768a')
    s.text(left,top-20,d.get('y_label',''),14,anchor='start')
    s.text((left+right)/2,bottom+85,d.get('x_label',''),15)
    if kind in ('bar','histogram','boxplot'):
        n=len(groups) if groups else len(series[0]['y'])
        if len(labels)!=n or any(len(v['y'])!=n for v in series) and not groups:raise ValueError('matching labels required')
        span=(right-left)/n
        focus=d.get('focus',[])
        if not isinstance(focus,list) or any(v not in labels for v in focus):raise ValueError('focus must list existing category labels')
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
                w=min(48,span*.70/len(series)) if kind=='bar' else span/len(series)
                for j,v in enumerate(series):
                    val=v['y'][i];z=Y(0)
                    bx=x-len(series)*w/2+j*w
                    color=item_color(series,v,j,d.get('color_map'))
                    if focus and label not in focus:color=CONTEXT
                    s.rect(bx,min(Y(val),z),w*.85,abs(Y(val)-z),fill=color,stroke='none',radius=0)
                    if kind=='bar' and (d.get('show_values',n*len(series)<=8) or label in focus):
                        s.text(bx+w*.425,Y(val)+(-10 if val>=0 else 20),f'{val:g}',14,color=INK,weight='bold' if label in focus else 'normal')
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
        callouts=[]
        for i,v in sorted(enumerate(series),key=lambda entry:bool(entry[1].get('emphasis'))):
            pts=list(zip(map(X,v['x']),map(Y,v['y'])))
            color=item_color(series,v,i,d.get('color_map'))
            if kind=='line':s.path(pts,color=color,weight=3 if v.get('emphasis') else 2)
            selected=label_indices(d,len(pts))
            for k,(x,y) in enumerate(pts):
                s.circle(x,y,5 if k in selected else 4,color,ring=True)
                if kind=='line' and k in selected and not (direct and k==len(pts)-1) and (d.get('show_values') is not False or 'label_indices' in d):
                    s.text(x-8 if k==len(pts)-1 else x,y-12,f"{v['y'][k]:g}",14,'end' if k==len(pts)-1 else 'middle')
            if direct:
                label=v.get('name','')
                if len(pts)-1 in selected and (d.get('show_values') is not False or 'label_indices' in d):label+=((' ' if label else '')+f"{v['y'][-1]:g}")
                if label:callouts.append((pts[-1][1],label,color,bool(v.get('emphasis'))))
        if direct:s.end_labels(callouts,right,top,bottom)
    return s.finish(d.get('caption',''))


def render(data):
    data=copy.deepcopy(data)
    if 'template' in data:
        # Resolve layout only: example business data must never fill missing input.
        template=load_template(data.pop('template'));kind=template['type']
        if data.get('type',kind)!=kind:raise ValueError('type conflicts with template')
        data['type']=kind
        for key in ('normalize','columns','display_scale','show_values','orientation','connect_rows'):
            if key in template and (key!='columns' or type(template[key]) is int):data.setdefault(key,template[key])
    color_map=data.get('color_map',{})
    if not isinstance(color_map,dict) or any(not isinstance(k,str) or v not in COLORS for k,v in color_map.items()):
        raise ValueError('color_map must map object names to ReadableDocs palette hex values')
    kind=data['type']
    if kind in ('grouped','aligned','detail'):
        from structures import grouped, aligned, detail
        return grouped(data) if kind=='grouped' else aligned(data) if kind=='aligned' else detail(data,render)
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
    p.add_argument('--colors',type=Path,help='Shared JSON name-to-color map for this document')
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
    try:
        data=json.loads(a.input.read_text())
        if a.colors:data['color_map']={**json.loads(a.colors.read_text()),**data.get('color_map',{})}
        svg=render(data)
    except (ValueError,KeyError,TypeError) as error:p.error(str(error))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(svg)
    print(a.output)


if __name__=='__main__':main()
