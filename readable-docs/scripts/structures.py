"""Composable explanatory layouts and obstacle-aware connectors. Standard library only."""
import heapq
import math
import xml.etree.ElementTree as ET

from canvas import SVG, ACCENT, COLORS, GRID, HIGHLIGHT, INK, MUTED, PALE, esc, lines, text_width

SYMBOLS = {'object', 'collection', 'document', 'store', 'search', 'process', 'filter', 'decision', 'result'}
SHAPES = {'circle', 'square', 'diamond', 'hexagon'}


def symbol(s, x, y, kind, size=36, color=ACCENT, shape='circle', status='neutral'):
    if kind not in SYMBOLS or shape not in SHAPES:raise ValueError('Unknown symbol or object shape')
    if status not in ('neutral','pass','fail'):raise ValueError('status must be neutral, pass or fail')
    s.parts.append(f'<g transform="translate({x},{y}) scale({size/40})" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">')
    drawings = {
        'document':'<path d="M9 3H25L32 10V37H9Z M25 3V11H32 M14 19H26 M14 25H26 M14 31H22"/>',
        'collection':'<path d="M5 28V4H25 M10 32V9H30"/><rect x="15" y="14" width="20" height="23" rx="3"/>',
        'store':'<ellipse cx="20" cy="8" rx="14" ry="5"/><path d="M6 8V31C6 38 34 38 34 31V8 M6 20C6 27 34 27 34 20"/>',
        'search':'<circle cx="17" cy="17" r="12"/><path d="M26 26L36 36"/>',
        'process':'<rect x="6" y="8" width="28" height="24" rx="5"/><path d="M1 20H12 M28 20H39 M23 15L28 20L23 25"/>',
        'filter':'<path d="M3 6H37L25 23V34L15 38V23Z"/>',
        'decision':'<path d="M20 2L38 20L20 38L2 20Z M16 15C16 9 25 9 25 15C25 19 20 19 20 23 M20 28V29"/>',
        'result':'<circle cx="20" cy="20" r="17"/><path d="'+{'neutral':'M12 16H28 M12 24H24','pass':'M10 20L17 27L30 13','fail':'M12 12L28 28 M28 12L12 28'}[status]+'"/>',
    }
    shapes = {'circle':'<circle cx="20" cy="20" r="16"/>', 'square':'<rect x="4" y="4" width="32" height="32" rx="6"/>',
              'diamond':'<path d="M20 2L38 20L20 38L2 20Z"/>', 'hexagon':'<path d="M20 2L36 11V29L20 38L4 29V11Z"/>'}
    s.parts.append(shapes[shape] if kind == 'object' else drawings[kind])
    s.parts.append('</g>')


def cell(value):
    if isinstance(value, str):return {'label':value}
    if not isinstance(value, dict) or not value.get('label'):raise ValueError('Each object needs a label')
    return value


def cell_height(value, width):
    n=cell(value)
    if n.get('presentation','card') not in ('card','symbol'):raise ValueError('presentation must be card or symbol')
    compact = n.get('presentation') != 'symbol'
    text_width=width-(84 if n.get('symbol') and compact else 32)
    return max(76, (78 if not compact else 32) + len(lines(n['label'],int(text_width/9.52)))*24
               + (len(lines(n['detail'],int(text_width/8.4)))*21+8 if n.get('detail') else 0))


def paint_cell(s, value, rect):
    n=cell(value);x,y,w,h=rect
    color=n.get('color',ACCENT if n.get('emphasis') else COLORS[0])
    if color not in COLORS:raise ValueError('Use a ReadableDocs palette color')
    compact=n.get('presentation')!='symbol'
    if compact:s.rect(x,y,w,h,HIGHLIGHT if n.get('emphasis') else 'white',color if n.get('emphasis') else GRID,12)
    kind=n.get('symbol', 'object' if not compact else None)
    if kind:symbol(s,x+18 if compact else x+w/2-24,y+18,kind,36 if compact else 48,color,n.get('shape','circle'),n.get('status','neutral'))
    tx=x+(68 if kind else 16) if compact else x+w/2;tw=w-(84 if kind and compact else 32)
    anchor='start' if compact else 'middle'
    top=y+(34 if compact else 86)
    used=s.paragraph(tx,top,n['label'],tw,17,INK,'bold',anchor)
    if n.get('detail'):s.paragraph(tx,top+used+6,n['detail'],tw,15,MUTED,anchor=anchor)


def intersects(a,b,r):
    """Whether an orthogonal segment crosses the interior of a rectangle."""
    x,y,w,h=r
    if a[0]==b[0]:return x<a[0]<x+w and max(min(a[1],b[1]),y)<min(max(a[1],b[1]),y+h)
    if a[1]==b[1]:return y<a[1]<y+h and max(min(a[0],b[0]),x)<min(max(a[0],b[0]),x+w)
    raise ValueError('Connector segments must be orthogonal')


def route(start, end, obstacles, width, height, used=()):
    # A visibility grid over object boundaries keeps routing independent of diagram semantics.
    xs={16,width-16,start[0],end[0]};ys={96,height-16,start[1],end[1]}
    for x,y,w,h in obstacles:
        xs.update((max(16,x-18),min(width-16,x+w+18)))
        ys.update((max(96,y-18),min(height-16,y+h+18)))
    xs=sorted(xs);ys=sorted(ys);source=(xs.index(start[0]),ys.index(start[1]),-1)
    goal=(xs.index(end[0]),ys.index(end[1]))
    queue=[(0,source)];cost={source:0};parent={};blocked={}
    while queue:
        score,u=heapq.heappop(queue)
        if score!=cost[u]:continue
        i,j,direction=u
        if (i,j)==goal:
            path=[]
            while True:
                path.append((xs[u[0]],ys[u[1]]))
                if u not in parent:break
                u=parent[u]
            path.reverse();clean=[]
            for p in path:
                if len(clean)>1 and ((clean[-2][0]==clean[-1][0]==p[0]) or (clean[-2][1]==clean[-1][1]==p[1])):clean.pop()
                clean.append(p)
            return clean
        for ni,nj,nd in ((i-1,j,0),(i+1,j,0),(i,j-1,1),(i,j+1,1)):
            if not 0<=ni<len(xs) or not 0<=nj<len(ys):continue
            a,b=(xs[i],ys[j]),(xs[ni],ys[nj]);key=tuple(sorted((a,b)))
            if key not in blocked:blocked[key]=any(intersects(a,b,r) for r in obstacles)
            if blocked[key]:continue
            distance=abs(a[0]-b[0])+abs(a[1]-b[1])
            overlap=any((a[0]==b[0]==p[0]==q[0] and max(min(a[1],b[1]),min(p[1],q[1]))<min(max(a[1],b[1]),max(p[1],q[1]))) or
                        (a[1]==b[1]==p[1]==q[1] and max(min(a[0],b[0]),min(p[0],q[0]))<min(max(a[0],b[0]),max(p[0],q[0]))) for p,q in used)
            value=score+distance+(28 if direction not in (-1,nd) else 0)+(distance*.4 if overlap else 0)
            v=(ni,nj,nd)
            if value<cost.get(v,math.inf):cost[v]=value;parent[v]=u;heapq.heappush(queue,(value,v))
    raise ValueError('No clear connector route; split the diagram or increase spacing')


def ports(rect):
    x,y,w,h=rect
    return {'left':(x,y+h/2),'right':(x+w,y+h/2),'top':(x+w/2,y),'bottom':(x+w/2,y+h)}


def connect(s, boxes, edges, blockers=(), anchors=None):
    obstacles=list(boxes.values())+list(blockers);used=[];labels=[];paths=[]
    for edge_index,edge in enumerate(edges):
        a,b=edge['from'],edge['to']
        if a not in boxes or b not in boxes:raise ValueError('Unknown connector endpoint')
        pa,pb=(anchors or {}).get(a,ports(boxes[a])),(anchors or {}).get(b,ports(boxes[b]))
        dx=pb['top'][0]-pa['top'][0];dy=pb['left'][1]-pa['left'][1]
        returning=edge.get('feedback') or any(e['from']==b and e['to']==a for e in edges[:edge_index])
        if a==b:sides=('right','top')
        elif returning or (abs(dy)>=abs(dx) and dy<0) or (abs(dx)>abs(dy) and dx<0):
            sides=('right','right') if abs(dy)>=abs(dx) else ('bottom','bottom')
        elif abs(dx)>abs(dy):sides=('right','left') if dx>0 else ('left','right')
        else:sides=('bottom','top') if dy>0 else ('top','bottom')
        side_a,side_b=edge.get('from_side',sides[0]),edge.get('to_side',sides[1])
        if side_a not in pa or side_b not in pb:raise ValueError('Ports use left/right/top/bottom')
        start,end=pa[side_a],pb[side_b]
        offsets={'left':(-24,0),'right':(24,0),'top':(0,-24),'bottom':(0,24)}
        da,db=offsets[side_a],offsets[side_b]
        start_stub=(start[0]+da[0],start[1]+da[1]);end_stub=(end[0]+db[0],end[1]+db[1])
        clearance=[(x-7,y-7,w+14,h+14) for x,y,w,h in obstacles+labels]
        points=[start,*route(start_stub,end_stub,clearance,s.width,s.height,used),end]
        color=edge.get('color',ACCENT if edge.get('emphasis') else MUTED)
        if color not in COLORS and color!=MUTED:raise ValueError('Use a ReadableDocs palette color')
        s.path(points,edge.get('directed',True),color,edge.get('dash',False),3 if edge.get('emphasis') else 2)
        paths.append(points)
        if edge.get('label'):
            rows=lines(edge['label'],18);w=max(64,max(text_width(v,13) for v in rows)+24);h=len(rows)*18.2+14
            candidates=[]
            for p,q in reversed(list(zip(points,points[1:]))):
                for ratio in (.5,.2,.8):
                    cx,cy=p[0]+(q[0]-p[0])*ratio,p[1]+(q[1]-p[1])*ratio
                    if p[1]==q[1]:candidates.extend([(cx-w/2,cy-h-6,w,h),(cx-w/2,cy+6,w,h)])
                    else:candidates.extend([(cx+8,cy-h/2,w,h),(cx-w-8,cy-h/2,w,h)])
            def clear(r):
                x,y,w,h=r
                return x>=8 and y>=90 and x+w<=s.width-8 and y+h<=s.height-8 and not any(x<u+v and x+w>u and y<t+k and y+h>t for u,t,v,k in obstacles+labels) and not any(intersects(p,q,r) for p,q in [*used,*zip(points,points[1:])])
            place=next((r for r in candidates if clear(r)),None)
            if place is None:raise ValueError('Connector label needs room; shorten it or increase spacing')
            x,y,w,h=place;s.rect(x,y,w,h,'white','none',4);s.paragraph(x+8,y+17,edge['label'],w-16,13,MUTED)
            labels.append(place)
        used.extend(zip(points,points[1:]))
    return paths


def connect_objects(s, nodes, boxes, edges, blockers=()):
    shapes=dict(boxes);obstacles=list(blockers);anchors={}
    for node in nodes:
        if node.get('presentation')!='symbol':continue
        ident=node['id'];x,y,w,h=boxes[ident]
        shapes[ident]=(x+w/2-24,y+18,48,48)
        anchors[ident]=ports(shapes[ident])
        anchors[ident]['bottom']=(x+w/2,y+h)
        obstacles.append((x+16,y+72,w-32,h-72))
    return connect(s,shapes,edges,obstacles,anchors)


def unique_nodes(nodes):
    ids=[n['id'] for n in nodes]
    if not ids or any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):raise ValueError('Objects need unique nonempty IDs')


def group_plan(group, edges):
    nodes=group['nodes'];unique_nodes(nodes)
    # Explicit rows are semantic stages, not pixel coordinates. Otherwise derive DAG levels.
    if 'rows' in group:
        rows=group['rows']
        if not rows or any(not r for r in rows) or sorted(v for r in rows for v in r)!=sorted(n['id'] for n in nodes):raise ValueError('rows must contain every node exactly once')
    else:
        ids={n['id'] for n in nodes};links=[e for e in edges if e['from'] in ids and e['to'] in ids and not e.get('feedback')]
        incoming={i:{e['from'] for e in links if e['to']==i} for i in ids};remaining=[n['id'] for n in nodes];rows=[]
        while remaining:
            row=[i for i in remaining if not incoming[i].intersection(remaining)]
            if not row:raise ValueError('Mark feedback edges or provide explicit stage rows for a cycle')
            rows.append(row);remaining=[i for i in remaining if i not in row]
    by_id={n['id']:n for n in nodes};cell_w=240;gap=76
    width=max(len(r) for r in rows)*(cell_w+gap)+40
    header=max(56,len(lines(group['label'],int((width-48)/10.64)))*27+30)
    rects={};top=header+20
    for row in rows:
        height=max(cell_height(by_id[i],cell_w) for i in row)
        left=(width-(len(row)*cell_w+(len(row)-1)*gap))/2
        for j,i in enumerate(row):rects[i]=(left+j*(cell_w+gap),top,cell_w,height)
        top+=height+gap
    return width,top-gap+40,header,rects


def identity_colors(d, nodes):
    for n in nodes:
        if not isinstance(n,dict):continue
        color=d.get('color_map',{}).get(n.get('id'),d.get('color_map',{}).get(n['label']))
        if color:n.setdefault('color',color)


def grouped(d):
    groups=d['groups'];edges=d.get('edges',[])
    if not groups:raise ValueError('groups cannot be empty')
    nodes=[n for g in groups for n in g['nodes']];unique_nodes(nodes);identity_colors(d,nodes)
    if any(e['from'] not in {n['id'] for n in nodes} or e['to'] not in {n['id'] for n in nodes} for e in edges):raise ValueError('Unknown connector endpoint')
    cols=int(d.get('columns',min(2,len(groups))))
    if not 1<=cols<=3:raise ValueError('Group columns must be 1 to 3')
    plans=[group_plan(g,edges) for g in groups];gap=100;margin=90
    widths=[max(p[0] for i,p in enumerate(plans) if i%cols==j) for j in range(min(cols,len(groups)))]
    row_heights=[max(p[1] for p in plans[i:i+cols]) for i in range(0,len(plans),cols)]
    width=sum(widths)+gap*(len(widths)-1)+margin*2;height=140+sum(row_heights)+gap*(len(row_heights)-1)+90
    s=SVG(width,height,d.get('title',''),d.get('subtitle',''));boxes={};blockers=[];top=140
    for row in range(len(row_heights)):
        left=margin
        for col in range(cols):
            i=row*cols+col
            if i>=len(groups):break
            w,h,header,rects=plans[i];g=groups[i]
            s.rect(left,top,widths[col],h,PALE,GRID,18)
            s.paragraph(left+24,top+32,g['label'],widths[col]-48,19,INK,'bold')
            blockers.append((left+12,top+6,widths[col]-24,header-10))
            for ident,(x,y,cw,ch) in rects.items():boxes[ident]=(left+x+(widths[col]-w)/2,top+y,cw,ch)
            left+=widths[col]+gap
        top+=row_heights[row]+gap
    connect_objects(s,nodes,boxes,edges,blockers)
    for n in nodes:paint_cell(s,n,boxes[n['id']])
    return s.finish(d.get('caption',''))


def aligned(d):
    columns=d['columns'];rows=d['rows']
    if not 2<=len(columns)<=4 or not rows:raise ValueError('Use 2–4 columns and at least one shared row')
    columns=[cell(c) for c in columns]
    identity_colors(d,columns+[v for row in rows for v in row['cells'] if v is not None])
    flow=d.get('connect_rows',False);cw=260;gap=44;left=240
    header=max(cell_height(c,cw) for c in columns);top=130+header+32
    positions=[]
    for row in rows:
        if len(row['cells'])!=len(columns):raise ValueError('Every row needs one cell per column; use null for absence')
        rh=max([60,len(lines(row['label'],18))*24+20]+[cell_height(v,cw) for v in row['cells'] if v is not None])
        positions.append((top,rh));top+=rh+(66 if flow else 28)
    s=SVG(left+len(columns)*(cw+gap)+46,top+40,d.get('title',''),d.get('subtitle',''))
    boxes={};values={};edges=[]
    for j,c in enumerate(columns):
        x=left+j*(cw+gap);s.rect(x-12,110,cw+24,top-90,PALE,'none',18)
        paint_cell(s,c,(x,124,cw,header))
    for i,(row,(y,h)) in enumerate(zip(rows,positions)):
        s.paragraph(48,y+30,row['label'],left-80,17,INK,'bold')
        for j,v in enumerate(row['cells']):
            x=left+j*(cw+gap)
            if v is None:s.text(x+cw/2,y+30,'—',17,color=MUTED);continue
            ident=f'{i}:{j}';boxes[ident]=(x,y,cw,h);values[ident]=v
            if flow and i and rows[i-1]['cells'][j] is not None:edges.append({'from':f'{i-1}:{j}','to':ident})
    connect_objects(s,[{**cell(v),'id':ident} for ident,v in values.items()],boxes,edges)
    for ident,value in values.items():paint_cell(s,value,boxes[ident])
    return s.finish(d.get('caption',''))


def embedded(s,root,rect,prefix):
    x,y,w,h=rect
    for element in root.iter():
        if 'id' in element.attrib:element.set('id',prefix+element.attrib['id'])
        for key,value in list(element.attrib.items()):
            if 'url(#' in value:element.set(key,value.replace('url(#','url(#'+prefix))
    root.set('x',str(x));root.set('y',str(y));root.set('width',str(w));root.set('height',str(h))
    s.parts.append(ET.tostring(root,encoding='unicode'))


def detail(d,render):
    objects=d['overview'];details=d['details'];unique_nodes(objects);identity_colors(d,objects)
    if not details:raise ValueError('details cannot be empty')
    ids={n['id'] for n in objects}
    if any(v['target'] not in ids for v in details):raise ValueError('Detail target must identify an overview object')
    roots=[]
    for item in details:
        figure=item['figure']
        if figure.get('type',figure.get('template')) in ('detail','overview-detail'):raise ValueError('Use one overview/detail level')
        roots.append(ET.fromstring(render({**figure,'color_map':{**d.get('color_map',{}),**figure.get('color_map',{})}})))
    heights=[max(180,float(r.get('viewBox').split()[3])*680/float(r.get('viewBox').split()[2])) for r in roots]
    by_id={n['id']:n for n in objects}
    headers=[max(38,len(lines('局部 · '+by_id[item['target']]['label'],77))*21+16) for item in details]
    overview_header=max(52,len(lines(d.get('overview_label','总览'),23))*27+24)
    ow=240;gap=80;overview_h=sum(cell_height(n,ow)+gap for n in objects)
    height=max(overview_h+overview_header+128,sum(heights)+sum(headers)+52*len(heights)+140)
    s=SVG(1220,height,d.get('title',''),d.get('subtitle',''));boxes={};top=118+overview_header
    s.rect(48,118,300,height-160,PALE,GRID,18);s.paragraph(72,148,d.get('overview_label','总览'),252,19,INK,'bold')
    for n in objects:
        h=cell_height(n,ow);boxes[n['id']]=(78,top,ow,h);top+=h+gap
    connect_objects(s,objects,boxes,d.get('edges',[]))
    detail_boxes={};y=130
    for i,(item,h) in enumerate(zip(details,heights)):
        # Each panel identifies its source object; connector is a correspondence, not a process arrow.
        ident=f'__detail_{i}'
        while ident in boxes:ident+='_'
        detail_boxes[ident]=(490,y,680,h+headers[i])
        y+=h+headers[i]+52
    all_boxes={**boxes,**detail_boxes}
    links=[{'from':v['target'],'to':ident,'directed':False,'dash':True,'emphasis':True,'from_side':'right','to_side':'left'} for v,ident in zip(details,detail_boxes)]
    connect_objects(s,objects,all_boxes,links)
    for n in objects:paint_cell(s,n,boxes[n['id']])
    by_id={n['id']:n for n in objects}
    for i,(item,root,rect) in enumerate(zip(details,roots,detail_boxes.values())):
        x,y,w,h=rect;s.rect(x-4,y-4,w+8,h+8,'white',GRID,14)
        s.paragraph(x+16,y+23,'局部 · '+by_id[item['target']]['label'],648,15,ACCENT,'bold')
        embedded(s,root,(x,y+headers[i],w,h-headers[i]),f'detail{i}-')
    return s.finish(d.get('caption',''))
