"""ReadableDocs SVG primitives and shared visual style (Python standard library)."""
import html
import math
import unicodedata

INK = '#203449'
MUTED = '#5a6e80'
GRID = '#d8e2ea'
PALE = '#f1f6fa'
COLORS = ['#28679b', '#187e75', '#96703a', '#8668a4', '#b75654', '#667b90']
FONT = 'PingFang SC,Noto Sans CJK SC,Microsoft YaHei,Arial,sans-serif'


def esc(value):
    return html.escape(str(value), quote=True)


def lines(value, width=24):
    result = []
    for paragraph in str(value).split('\n'):
        row, used = '', 0
        for char in paragraph:
            size = 2 if unicodedata.east_asian_width(char) in 'WF' else 1
            if row and used + size > width:
                result.append(row)
                row, used = '', 0
            row += char
            used += size
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


class SVG:
    def __init__(self, width, height, title='', subtitle=''):
        self.width, self.height = width, height
        self.title, self.subtitle = str(title), str(subtitle)
        title_rows = lines(title, max(10, int((width-80)/15))) if title else []
        sub_rows = lines(subtitle, max(10, int((width-80)/9))) if subtitle else []
        self.offset = max(0, len(title_rows)*34 + len(sub_rows)*23 + 20 - 78)
        self.header = (title_rows, sub_rows)
        self.parts = []

    def text(self, x, y, value, size=17, anchor='middle', color=INK, weight='normal'):
        self.parts.append(f'<text x="{x:g}" y="{y:g}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color}">{esc(value)}</text>')

    def paragraph(self, x, y, value, width, size=17, color=INK, weight='normal', anchor='start'):
        rows = lines(value, max(4, int(width/(size*.56))))
        for i, row in enumerate(rows):
            self.text(x, y+i*size*1.4, row, size, anchor, color, weight)
        return len(rows)*size*1.4

    def rect(self, x, y, w, h, fill=PALE, stroke=GRID, radius=10):
        self.parts.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{radius:g}" fill="{fill}" stroke="{stroke}"/>')

    def path(self, points, arrow=False, color=MUTED, dash=False):
        coords = ' '.join(f'{x:g},{y:g}' for x, y in points)
        self.parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"' + (' marker-end="url(#arrow)"' if arrow else '') + (' stroke-dasharray="6 5"' if dash else '') + '/>')

    def circle(self, x, y, r=4, color=COLORS[0]):
        self.parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" fill="{color}"/>')

    def box(self, x, y, label, width=230, kind='box', fill=PALE):
        rows = lines(label, int(width/9))
        height = max(60, len(rows)*23+24)
        if kind == 'decision':
            self.parts.append(f'<polygon points="{x},{y-height/2} {x+width/2},{y} {x},{y+height/2} {x-width/2},{y}" fill="#faf3e5" stroke="#b3925a"/>')
        else:
            self.rect(x-width/2, y-height/2, width, height, fill=fill, radius=height/2 if kind=='terminal' else 10)
        for i, row in enumerate(rows):
            self.text(x, y+(i-(len(rows)-1)/2)*23+6, row)
        return height

    def finish(self, caption=''):
        captions = lines(caption, max(10, int((self.width-80)/8.5))) if caption else []
        total = self.height+self.offset+len(captions)*23+12
        head = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{total}" viewBox="0 0 {self.width} {total}" role="img">',
                f'<title>{esc(self.title)}</title><desc>{esc(self.subtitle)}</desc>',
                '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#5a6e80"/></marker></defs>',
                '<rect width="100%" height="100%" fill="white"/>',
                '<rect x="28" y="22" width="5" height="30" rx="2" fill="#187e75"/>']
        content = self.parts
        self.parts = []
        y = 46
        for row in self.header[0]:
            self.text(48, y, row, 27, 'start', INK, 'bold'); y += 34
        for row in self.header[1]:
            self.text(48, y-5, row, 16, 'start', MUTED); y += 23
        head += self.parts
        head.append(f'<g transform="translate(0,{self.offset})">')
        head += content
        self.parts = []
        for i, row in enumerate(captions):
            self.text(32, self.height+10+i*23, row, 15, 'start', MUTED)
        return '\n'.join(head+self.parts+['</g></svg>'])
