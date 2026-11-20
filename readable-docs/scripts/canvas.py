"""ReadableDocs SVG primitives and shared visual style (Python standard library)."""
import html
import math
import re
import unicodedata

INK = '#203449'
MUTED = '#5a6e80'
GRID = '#d8e2ea'
PALE = '#f1f6fa'
CONTEXT = '#a6b4c0'
ACCENT = '#187e75'
HIGHLIGHT = '#e7f3f0'
COLORS = ['#28679b', '#187e75', '#96703a', '#8668a4', '#b75654', '#667b90']
FONT = 'PingFang SC,Noto Sans CJK SC,Microsoft YaHei,Arial,sans-serif'
TITLE, HEADING, BODY, LABEL, SMALL, NUMBER = 27, 19, 17, 15, 13, 44
STROKE_GRID, STROKE_REFERENCE, STROKE_NORMAL, STROKE_FOCUS = 1, 1.5, 2, 3


def type_size(size):
    # Common roles also normalize legacy layouts to the shared type scale.
    return {12: SMALL, 14: LABEL, 16: LABEL, 18: HEADING}.get(size, size)


def esc(value):
    return html.escape(str(value), quote=True)


def lines(value, width=24):
    result = []
    for paragraph in str(value).split('\n'):
        row, used = '', 0
        for token in re.findall(r'[A-Za-z0-9_]+(?:[./:-][A-Za-z0-9_]+)*|.', paragraph):
            size = sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in token)
            # Keep fitting identifiers intact; oversized identifiers still wrap.
            chunks = list(token) if size > width else [token]
            for chunk in chunks:
                n = sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in chunk)
                if row and used + n > width:
                    result.append(row.rstrip())
                    row, used = '', 0
                if not row and chunk.isspace():continue
                row += chunk
                used += n
        result.append(row)
    return result


def text_width(value, size=17):
    return max((sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in row)
                * size * .56 for row in str(value).split('\n')), default=0)


def nice_ticks(low, high, target=5):
    raw=(high-low)/target
    if raw<=0:return [low]
    power=10**math.floor(math.log10(raw))
    step=next(n for n in (1,2,2.5,5,10) if n>=raw/power)*power
    start=math.ceil(low/step-1e-9);end=math.floor(high/step+1e-9)
    return [0.0 if abs(i*step)<step*1e-9 else i*step for i in range(start,end+1)]


def item_color(items, item, index=0, color_map=None):
    """Preserve series identity unless the author explicitly selects a focus."""
    if any(v.get('emphasis') for v in items) and not item.get('emphasis'):
        return CONTEXT
    key = item.get('name', item.get('label', item.get('id', '')))
    color = item.get('color', (color_map or {}).get(key, COLORS[index % len(COLORS)]))
    if color not in COLORS:
        raise ValueError('color must be a ReadableDocs palette hex from drawing.md')
    return color


def series_items(d):
    items = [dict(v) if isinstance(v, dict) else {'name': str(v)} for v in d['series']]
    if not items or any(not v.get('name') for v in items):
        raise ValueError('series need nonempty names')
    return items


def box_rows(label, width=230, kind='box'):
    rows = lines(label, int(width/9) if kind != 'decision' else int(width/16))
    height = max(60, len(rows)*23+24) * (1.5 if kind == 'decision' else 1)
    return rows, height


def label_indices(d, count):
    selected = d.get('label_indices')
    if selected is None:
        return set(range(count)) if d.get('show_values') else {count-1}
    if not isinstance(selected, list) or any(type(i) is not int or not 0 <= i < count for i in selected):
        raise ValueError('label_indices must contain valid zero-based point indices')
    return set(selected)


class SVG:
    def __init__(self, width, height, title='', subtitle=''):
        self.width, self.height = width, height
        self.title, self.subtitle = str(title), str(subtitle)
        self.parts = []

    def text(self, x, y, value, size=BODY, anchor='middle', color=INK, weight='normal'):
        size = type_size(size)
        self.parts.append(f'<text x="{x:g}" y="{y:g}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color}">{esc(value)}</text>')

    def paragraph(self, x, y, value, width, size=BODY, color=INK, weight='normal', anchor='start'):
        size = type_size(size)
        rows = lines(value, max(4, int(width/(size*.56))))
        for i, row in enumerate(rows):
            self.text(x, y+i*size*1.4, row, size, anchor, color, weight)
        return len(rows)*size*1.4

    def rect(self, x, y, w, h, fill=PALE, stroke=GRID, radius=10):
        self.parts.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{radius:g}" fill="{fill}" stroke="{stroke}"/>')

    def path(self, points, arrow=False, color=MUTED, dash=False, weight=None):
        if weight is None:weight = STROKE_GRID if color == GRID else (STROKE_REFERENCE if dash else STROKE_NORMAL)
        coords = ' '.join(f'{x:g},{y:g}' for x, y in points)
        marker = 'arrow-'+color.lstrip('#')
        self.parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{weight:g}" stroke-linejoin="round" stroke-linecap="round"' + (f' marker-end="url(#{marker})"' if arrow else '') + (' stroke-dasharray="6 5"' if dash else '') + '/>')

    def circle(self, x, y, r=4, color=COLORS[0], ring=False):
        self.parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" fill="{color}"' + (' stroke="white" stroke-width="2"' if ring else '') + '/>')

    def box(self, x, y, label, width=230, kind='box', fill=PALE, emphasis=False):
        rows, height = box_rows(label, width, kind)
        stroke = ACCENT if emphasis else GRID
        fill = HIGHLIGHT if emphasis else fill
        if kind == 'decision':
            self.parts.append(f'<polygon points="{x},{y-height/2} {x+width/2},{y} {x},{y+height/2} {x-width/2},{y}" fill="{fill}" stroke="{stroke}"/>')
        else:
            self.rect(x-width/2, y-height/2, width, height, fill=fill, stroke=stroke, radius=height/2 if kind=='terminal' else 10)
        for i, row in enumerate(rows):
            self.text(x, y+(i-(len(rows)-1)/2)*23+6, row, weight='bold' if emphasis else 'normal')
        return height

    def end_labels(self, callouts, right, top, bottom, width=200):
        """Place (y, text, color, emphasis) labels with true endpoint leaders."""
        placed=[]
        for y,label,color,strong in sorted(callouts,key=lambda v:v[0]):
            height=max(24,len(lines(label,int(width/(LABEL*.56))))*LABEL*1.4)
            cy=max(top,y-height/2,placed[-1][1]+placed[-1][2]+12 if placed else top)
            placed.append([y,cy,height,label,color,strong])
        if placed and placed[-1][1]+placed[-1][2]>bottom:
            placed[-1][1]=bottom-placed[-1][2]
            for i in range(len(placed)-2,-1,-1):placed[i][1]=min(placed[i][1],placed[i+1][1]-placed[i][2]-12)
        if placed and placed[0][1]<top-10:raise ValueError('Endpoint labels too dense; shorten names or split into panels')
        for y,cy,h,label,color,strong in placed:
            self.path([(right,y),(right+14,cy+h/2),(right+24,cy+h/2)],color=color,weight=STROKE_GRID)
            self.paragraph(right+32,cy+LABEL,label,width,LABEL,INK,'bold' if strong else 'normal')

    def finish(self, caption=''):
        # Width can change during content layout; measure the header only now.
        title_rows = lines(self.title, max(10, int((self.width-80)/(TITLE*.56)))) if self.title else []
        sub_rows = lines(self.subtitle, max(10, int((self.width-80)/(LABEL*.56)))) if self.subtitle else []
        offset = max(0, len(title_rows)*34 + len(sub_rows)*23 + 20 - 78)
        captions = lines(caption, max(10, int((self.width-80)/8.5))) if caption else []
        total = self.height+offset+len(captions)*23+12
        head = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{total}" viewBox="0 0 {self.width} {total}" role="img">',
                f'<title>{esc(self.title)}</title><desc>{esc(self.subtitle)}</desc>',
                '<defs>' + ''.join(f'<marker id="{name}" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 Z" fill="{color}"/></marker>' for name,color in [('arrow-'+c.lstrip('#'),c) for c in dict.fromkeys([MUTED,ACCENT,*COLORS,GRID])]) + '</defs>',
                '<rect width="100%" height="100%" fill="white"/>',
                '<rect x="28" y="22" width="5" height="30" rx="2" fill="#187e75"/>']
        content = self.parts
        self.parts = []
        y = 46
        for row in title_rows:
            self.text(48, y, row, TITLE, 'start', INK, 'bold'); y += 34
        for row in sub_rows:
            self.text(48, y-5, row, LABEL, 'start', MUTED); y += 23
        head += self.parts
        head.append(f'<g transform="translate(0,{offset})">')
        head += content
        self.parts = []
        for i, row in enumerate(captions):
            self.text(32, self.height+10+i*23, row, 15, 'start', MUTED)
        return '\n'.join(head+self.parts+['</g></svg>'])
