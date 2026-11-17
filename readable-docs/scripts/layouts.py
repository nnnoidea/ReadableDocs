"""Content-only layouts for ReadableDocs; all coordinates are computed here."""
import datetime as dt
import math
import xml.etree.ElementTree as ET
from canvas import SVG, COLORS, INK, MUTED, GRID, PALE, esc, lines, text_width, nice_ticks


def finite(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('Values must be finite numbers')
    return number


def rows_of(d, key='rows'):
    rows = d.get(key, [])
    if not isinstance(rows, list) or not rows:
        raise ValueError(f'{key} must be a nonempty list')
    return rows


def frame(d, height, width=1000):
    return SVG(width, height, d.get('title', ''), d.get('subtitle', ''))


def note(d, extra=''):
    return ' · '.join(str(x) for x in [d.get('caption', ''), extra] if x)


def fmt(v):
    return f'{v:,.6g}'


def containment(d):
    root = d['root']
    def measure(n, w, depth=0):
        if depth > 12:
            raise ValueError('Containment depth exceeds 12; split into local diagrams')
        if w<140:raise ValueError('Containment is too deeply nested; split into local diagrams')
        head = len(lines(n['label'], int((w-40)/10)))*25+30
        children = n.get('children', [])
        if not children:
            return max(76, head)
        cols = min(2, len(children)); cw = (w-44-(cols-1)*18)/cols
        if cw < 140:
            cols = 1; cw = w-44
        heights = [measure(c, cw, depth+1) for c in children]
        return head+sum(max(heights[i:i+cols])+18 for i in range(0,len(children),cols))+12
    def paint(n, x, y, w, depth=0):
        h = measure(n,w,depth)
        s.rect(x,y,w,h,fill=PALE if depth%2==0 else 'white',stroke=GRID)
        head = len(lines(n['label'],int((w-40)/10)))*25+30
        s.paragraph(x+20,y+30,n['label'],w-40,18,INK,'bold')
        children = n.get('children',[])
        if children:
            cols=min(2,len(children));cw=(w-44-(cols-1)*18)/cols
            if cw<140:cols=1;cw=w-44
            cy=y+head
            for i in range(0,len(children),cols):
                group=children[i:i+cols]
                for j,c in enumerate(group):paint(c,x+22+j*(cw+18),cy,cw,depth+1)
                cy+=max(measure(c,cw,depth+1) for c in group)+18
    height=measure(root,936);s=frame(d,height+130)
    paint(root,32,100,936)
    return s.finish(d.get('caption',''))


def sets(d):
    sets=rows_of(d,'sets')
    if len(sets)!=2:
        raise ValueError('sets uses two sets; use matrix for more sets')
    left,right=sets
    a,b=set(map(str,left['items'])),set(map(str,right['items']))
    regions=[sorted(a-b),sorted(a&b),sorted(b-a)]
    contents=['\n'.join(v) if v else '∅' for v in regions]
    row_count=max(len(lines(v,20)) for v in contents)
    body=max(300,row_count*24+120);s=frame(d,body+160)
    for x,color in [(350,COLORS[0]),(650,COLORS[1])]:
        s.parts.append(f'<ellipse cx="{x}" cy="{130+body/2}" rx="300" ry="{body/2}" fill="{color}" fill-opacity="0.08" stroke="{color}" stroke-width="2"/>')
    for x,label in [(220,left['label']),(780,right['label'])]:
        s.paragraph(x,115,label,260,19,INK,'bold','middle')
    for x,caption,content in zip([220,500,780],['仅左侧','交集','仅右侧'],contents):
        s.text(x,176,caption,16,color=MUTED)
        s.paragraph(x,211,content,190,17,anchor='middle')
    return s.finish(note(d,'区域表示成员归属，面积不表示数量'))


def mapping(d):
    left,right=rows_of(d,'left'),rows_of(d,'right');links=d.get('links',[])
    def ids(items):
        values=[x['id'] for x in items]
        if len(values)!=len(set(values)):raise ValueError('Mapping IDs must be unique per side')
        return values
    li,ri=ids(left),ids(right)
    if any(e['from'] not in li or e['to'] not in ri for e in links):raise ValueError('Unknown mapping endpoint')
    gap=max(110,max(len(lines(n['label'],24))*25+45 for n in left+right))
    n=max(len(left),len(right));s=frame(d,n*gap+180)
    pos={}
    for side,items,x in [('left',left,190),('right',right,810)]:
        for i,item in enumerate(items):pos[(side,item['id'])]=(x,155+i*gap)
    for i,e in enumerate(links):
        x,y=pos['left',e['from']];u,v=pos['right',e['to']]
        s.path([(x+130,y),(u-130,v)],arrow=bool(e.get('directed',True)),color=COLORS[i%len(COLORS)])
        if e.get('label'):
            # Labels sit near their source; use matrix for dense labeled mappings.
            s.paragraph(346,y-12-(i%2)*22,e['label'],280,14,MUTED)
    for side,items in [('left',left),('right',right)]:
        for item in items:
            x,y=pos[side,item['id']];s.box(x,y,item['label'],260)
    return s.finish(d.get('caption',''))


def matrix(d, heat=False):
    labels=rows_of(d,'rows');cols=rows_of(d,'columns');values=rows_of(d,'values')
    if len(values)!=len(labels) or any(len(row)!=len(cols) for row in values):raise ValueError('Matrix dimensions must match rows and columns')
    cw=max(110,min(200,max(text_width(v)+24 for v in cols)));left=max(150,min(280,max(text_width(v)+20 for v in labels)))
    width=left+cw*len(cols)+50
    header=max(55,max(len(lines(c,int((cw-15)/10)))*25+20 for c in cols))
    top=100+header
    rh=max(64,max(len(lines(str(v),int((cw-14)/(17*.56))))*24+24 for row in values for v in row),
           max(len(lines(v,int((left-25)/(17*.56))))*24+24 for v in labels))
    s=frame(d,top+rh*len(labels)+85,width)
    if heat:
        numeric=[finite(v) for row in values for v in row if v is not None]
        if not numeric:raise ValueError('Heatmap requires at least one numeric value')
        low,high=min(numeric),max(numeric)
    for j,c in enumerate(cols):s.paragraph(left+(j+.5)*cw,112,c,cw-12,17,anchor='middle')
    for i,label in enumerate(labels):
        label_count=len(lines(label,int((left-25)/(17*.56))))
        s.paragraph(left-14,top+i*rh+rh/2+5-(label_count-1)*17*.7,label,left-25,17,anchor='end')
        for j,v in enumerate(values[i]):
            x,y=left+j*cw,top+i*rh;fill=PALE if i%2==0 else '#ffffff';color=INK
            shown='—' if v is None else str(v)
            if heat and v is not None:
                value=finite(v)
                if low<0<high:
                    intensity=abs(value)/max(abs(low),abs(high));base=COLORS[0] if value>=0 else COLORS[4]
                else:
                    intensity=(value-low)/(high-low) if high!=low else .5;base=COLORS[0]
                rgb=[int(base[k:k+2],16) for k in (1,3,5)]
                fill='#'+''.join(f'{round(255*(1-intensity*.88)+c*intensity*.88):02x}' for c in rgb)
                color='white' if intensity>.65 else INK;shown=fmt(value)
            s.rect(x,y,cw-3,rh-3,fill=fill,stroke='white',radius=4)
            line_count=len(lines(shown,int((cw-14)/(17*.56))))
            s.paragraph(x+cw/2,y+rh/2+5-(line_count-1)*17*.7,shown,cw-14,17,color,anchor='middle')
    extra=''
    if heat:
        extra=f"数值范围 {fmt(low)} 至 {fmt(high)} {d.get('unit','')}；空值为 —"
        if low<0<high:extra+='；蓝色为正、红色为负，深浅表示绝对值'
        else:extra+='；颜色越深，数值越大'
    return s.finish(note(d,extra))


def timeline(d):
    events=rows_of(d,'events');width=1000
    title_heights=[len(lines(e['label'],66))*27 for e in events]
    heights=[max(95,h+len(lines(e.get('detail',''),78))*24+28) for e,h in zip(events,title_heights)]
    s=frame(d,sum(heights)+140);y=115
    for i,(e,h,title_h) in enumerate(zip(events,heights,title_heights)):
        if i<len(events)-1:s.path([(210,y),(210,y+h)],color=GRID)
        s.circle(210,y,6,COLORS[i%len(COLORS)])
        s.paragraph(185,y+6,e['date'],155,16,MUTED,anchor='end')
        s.paragraph(240,y+6,e['label'],710,19,INK,'bold')
        s.paragraph(240,y+title_h+10,e.get('detail',''),710,16,MUTED)
        y+=h
    return s.finish(note(d,'按输入先后排列，节点间距不表示时长'))


def gantt(d):
    rows=rows_of(d)
    dates=isinstance(rows[0]['start'],str)
    def value(v):
        if dates:return dt.date.fromisoformat(v).toordinal()
        return finite(v)
    ranges=[(value(r['start']),value(r['end'])) for r in rows]
    if any(a>b for a,b in ranges):raise ValueError('Gantt end must not precede start')
    low=min(a for a,b in ranges);high=max(b for a,b in ranges)
    if low==high:high=low+1
    left=280;right=940;top=125;gap=max(72,max(len(lines(r['label'],26))*24+20 for r in rows))
    s=frame(d,top+len(rows)*gap+75);X=lambda v:left+(v-low)/(high-low)*(right-left)
    ticks=sorted(set(round(low+(high-low)*i/4) for i in range(5))) if dates else nice_ticks(low,high)
    for v in ticks:
        label=dt.date.fromordinal(v).isoformat() if dates else fmt(v)
        s.path([(X(v),top-10),(X(v),top+gap*len(rows))],color=GRID)
        s.text(X(v),top+gap*len(rows)+28,label,14,color=MUTED)
    for i,(r,(a,b)) in enumerate(zip(rows,ranges)):
        y=top+i*gap;s.paragraph(left-20,y+24,r['label'],250,17,anchor='end')
        color=COLORS[i%len(COLORS)]
        if a==b:s.circle(X(a),y+17,6,color)
        else:s.rect(X(a),y,X(b)-X(a),34,color,'none',5)
        if r.get('note'):s.paragraph(left,y+54,r['note'],right-left,14,MUTED)
    return s.finish(note(d,'横轴按实际时间；区间从开始时刻到结束时刻，点表示里程碑' if dates else f"横轴单位：{d.get('unit','数值')}"))


def legend(s,names,x=250,y=105,width=680):
    cols=2;cell=width/cols;rows=[]
    for i in range(0,len(names),cols):
        h=max(len(lines(v,int((cell-35)/9)))*24+12 for v in names[i:i+cols]);rows.append(h)
    cy=y
    for i,h in zip(range(0,len(names),cols),rows):
        for j,name in enumerate(names[i:i+cols]):
            px=x+j*cell;s.rect(px,cy-13,14,14,COLORS[(i+j)%len(COLORS)],'none',3)
            s.paragraph(px+23,cy,name,cell-32,16)
        cy+=h
    return cy


def stacked(d):
    rows=rows_of(d);names=rows_of(d,'series');normalize=d.get('normalize',True)
    vals=[[finite(v) for v in r['values']] for r in rows]
    if any(len(v)!=len(names) for v in vals) or any(v<0 for row in vals for v in row):raise ValueError('Stacked rows require matching nonnegative series values')
    totals=list(map(sum,vals))
    if normalize and min(totals)<=0:raise ValueError('Normalized stacked rows need positive totals')
    max_total=max(totals) or 1;left,right=270,890
    row_gap=max(92,max(len(lines(r['label'],26))*24+35 for r in rows))
    s=frame(d,200+len(rows)*row_gap+len(names)*24);top=legend(s,names)+20
    for i,(r,values,total) in enumerate(zip(rows,vals,totals)):
        y=top+i*row_gap;s.paragraph(left-18,y+25,r['label'],240,17,anchor='end')
        x=left;small=[]
        for j,v in enumerate(values):
            w=(right-left)*v/(total if normalize else max_total)
            if w>0:s.rect(x,y,w,38,COLORS[j%len(COLORS)],'none',0)
            label=fmt(v)
            if w>text_width(label,16)+14:s.text(x+w/2,y+25,label,16,color='white',weight='bold')
            elif v:small.append(f'{names[j]} {label}')
            x+=w
        s.text(right+15,y+25,fmt(total),16,'start',MUTED)
        if small:s.paragraph(left,y+62,'；'.join(small),right-left,14,MUTED)
    s.height=top+len(rows)*row_gap+10
    return s.finish(note(d,f"{'每条表示该行的 100%，段长表示占比' if normalize else '各条使用相同数值刻度，段长表示数量'}；标注为原始数值 {d.get('unit','')}"))


def delta(d):
    rows=rows_of(d);names=rows_of(d,'series');scale=finite(d.get('display_scale',1))
    if scale<=0:raise ValueError('display_scale must be positive')
    vals=[[finite(v)*scale for v in row['values']] for row in rows]
    if any(len(v)!=len(names) for v in vals):raise ValueError('Delta row series lengths differ')
    all_values=[v for row in vals for v in row];lo=min(0,min(all_values));hi=max(0,max(all_values))
    if lo==hi:lo,hi=-1,1
    pad=(hi-lo)*.17;lo-=pad;hi+=pad
    left,right=310,900;gap=max(64,len(names)*27+30,max(len(lines(r['label'],28))*24+16 for r in rows))
    s=frame(d,200+len(rows)*gap);top=legend(s,names,x=310,width=600)+24
    X=lambda v:left+(v-lo)/(hi-lo)*(right-left)
    for v in sorted(set(nice_ticks(lo,hi)+[0])):
        s.path([(X(v),top-12),(X(v),top+len(rows)*gap-10)],color=MUTED if v==0 else GRID)
        s.text(X(v),top+len(rows)*gap+20,f'{v:+.3g}' if v else '0',14,color=MUTED)
    for i,(r,values) in enumerate(zip(rows,vals)):
        y=top+i*gap;s.paragraph(left-25,y+20,r['label'],270,17,anchor='end')
        for j,v in enumerate(values):
            yy=y+j*27+10;color=COLORS[j%len(COLORS)]
            s.path([(X(0),yy),(X(v),yy)],color=color);s.circle(X(v),yy,5,color)
            s.text(X(v)+(9 if v>=0 else -9),yy+5,f'{v:+.4g}',15,'start' if v>=0 else 'end',color,'bold')
    s.height=top+len(rows)*gap+45
    return s.finish(note(d,f"单位：{d.get('unit','差值')}；正值高于各行标明的基线，负值低于基线"))


def trend(d):
    xs=[finite(x) for x in rows_of(d,'x')];series=rows_of(d,'series');refs=d.get('references',[])
    if any(b<=a for a,b in zip(xs,xs[1:])):raise ValueError('Trend x values must be strictly increasing')
    ys=[[finite(v) for v in row['values']] for row in series]
    if any(len(v)!=len(xs) for v in ys):raise ValueError('Trend x/values lengths differ')
    values=[v for row in ys for v in row]+[finite(r['value']) for r in refs]
    lo,hi=min(values),max(values)
    pad=(hi-lo)*.18 if hi!=lo else max(abs(hi)*.1,1)
    low=finite(d.get('y_min',lo-pad));high=finite(d.get('y_max',hi+pad))
    if low>=high or lo<low or hi>high:raise ValueError('Axis limits must include every value and reference')
    s=frame(d,590);top=legend(s,[v['name'] for v in series],x=100,width=800)+35;bottom=top+310
    s.height=bottom+75;left,right=110,880
    xlo,xhi=min(xs),max(xs)
    if xlo==xhi:xlo-=1;xhi+=1
    X=lambda x:left+(x-xlo)/(xhi-xlo)*(right-left);Y=lambda y:bottom-(y-low)/(high-low)*(bottom-top)
    for v in nice_ticks(low,high):
        s.path([(left,Y(v)),(right,Y(v))],color=GRID);s.text(left-12,Y(v)+5,f'{v:.5g}',15,'end',MUTED)
    indices=list(range(len(xs))) if len(xs)<=8 else sorted(set(round(i*(len(xs)-1)/6) for i in range(7)))
    for i in indices:s.text(X(xs[i]),bottom+28,fmt(xs[i]),15,color=MUTED)
    for i,r in enumerate(refs):
        y=Y(finite(r['value']));s.path([(left,y),(right,y)],color=COLORS[2],dash=True)
        s.text(right,y-9-i*18,f"{r['label']} {fmt(finite(r['value']))}",15,'end',COLORS[2],'bold')
    for j,(series_row,values_row) in enumerate(zip(series,ys)):
        pts=[(X(x),Y(y)) for x,y in zip(xs,values_row)];color=COLORS[j%len(COLORS)]
        s.path(pts,color=color)
        for i,((x,y),value) in enumerate(zip(pts,values_row)):
            s.circle(x,y,5,color)
            if d.get('show_values',len(xs)<=6):
                baseline=y+(24 if (i+j)%2==0 else -13)
                if any(abs(baseline-Y(finite(r['value'])))<19 for r in refs):baseline=y+24
                if baseline>bottom-5:baseline=y-13
                anchor='start' if i==0 else ('end' if i==len(xs)-1 else 'middle')
                s.text(x+(8 if i==0 else -8 if i==len(xs)-1 else 0),baseline,fmt(value),14,anchor,color)
    s.text((left+right)/2,bottom+61,d.get('x_label',''),17)
    return s.finish(note(d,f"纵轴：{d.get('unit','数值')}；局部范围 {low:.5g} 至 {high:.5g}"))


def panels(d, render):
    items=rows_of(d,'panels');cols=int(d.get('columns',1))
    if cols not in (1,2):raise ValueError('panels columns must be 1 or 2')
    for item in items:
        if item.get('type',item.get('template'))=='panels':raise ValueError('Nested panels are not supported')
    roots=[ET.fromstring(render(item)) for item in items]
    cell=1000;gap=30;width=cols*cell+(cols+1)*gap
    heights=[float(r.attrib['viewBox'].split()[3])*cell/float(r.attrib['viewBox'].split()[2]) for r in roots]
    total=sum(max(heights[i:i+cols])+gap for i in range(0,len(items),cols))
    s=frame(d,130+total,width);y=100
    for i in range(0,len(items),cols):
        for j,r in enumerate(roots[i:i+cols]):
            prefix=f'panel{i+j}-'
            for element in r.iter():
                if 'id' in element.attrib:element.set('id',prefix+element.attrib['id'])
                for key,value in list(element.attrib.items()):
                    if 'url(#' in value:element.set(key,value.replace('url(#','url(#'+prefix))
            r.set('x',str(gap+j*(cell+gap)));r.set('y',str(y));r.set('width',str(cell));r.set('height',str(heights[i+j]))
            s.parts.append(ET.tostring(r,encoding='unicode'))
        y+=max(heights[i:i+cols])+gap
    return s.finish(d.get('caption',''))


def render_extra(d, render):
    kind=d['type']
    if kind=='containment':return containment(d)
    if kind=='sets':return sets(d)
    if kind=='mapping':return mapping(d)
    if kind in ('matrix','heatmap'):return matrix(d,kind=='heatmap')
    if kind=='timeline':return timeline(d)
    if kind=='gantt':return gantt(d)
    if kind=='stacked':return stacked(d)
    if kind=='delta':return delta(d)
    if kind=='trend':return trend(d)
    if kind=='panels':return panels(d,render)
    raise ValueError('Unsupported type: '+str(kind))
