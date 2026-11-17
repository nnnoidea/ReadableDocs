"""Run with python3 -B scripts/test_draw.py. Tests geometry and data semantics."""
import copy
import json
import math
import unittest
import xml.etree.ElementTree as E
from pathlib import Path
from draw import render, TEMPLATES

NS={'s':'http://www.w3.org/2000/svg'}


class Figures(unittest.TestCase):
    def test_all_templates_are_valid_and_do_not_mutate_input(self):
        for path in TEMPLATES.glob('*.json'):
            with self.subTest(template=path.stem):
                data=json.loads(path.read_text());before=copy.deepcopy(data)
                root=E.fromstring(render(data))
                self.assertEqual(data,before)
                bounds=list(map(float,root.attrib['viewBox'].split()))
                self.assertTrue(all(math.isfinite(v) for v in bounds))
                self.assertGreater(bounds[2],0);self.assertGreater(bounds[3],0)
                self.assertNotIn('<script',E.tostring(root,encoding='unicode'))
                ids=[e.attrib['id'] for e in root.iter() if 'id' in e.attrib]
                self.assertEqual(len(ids),len(set(ids)))

    def test_template_name_never_supplies_sample_business_data(self):
        with self.assertRaises((ValueError,KeyError)):
            render({'template':'composition','title':'真实报告'})

    def test_template_preserves_quantity_layout_without_sample_values(self):
        root=E.fromstring(render({'template':'stacked-amount','series':['a'],'rows':[{'label':'x','values':[2]},{'label':'y','values':[4]}]}))
        widths=[float(e.get('width')) for e in root.findall('.//s:rect',NS) if e.get('height')=='38']
        self.assertEqual(widths,[310,620])

    def test_normalized_stacks_have_same_length_and_correct_ratio(self):
        root=E.fromstring(render({'type':'stacked','series':['a','b'],'rows':[{'label':'x','values':[3,1]},{'label':'y','values':[6,2]}]}))
        bars=[e for e in root.findall('.//s:rect',NS) if e.get('height')=='38']
        widths=[float(e.get('width')) for e in bars]
        self.assertEqual(widths,[465,155,465,155])

    def test_absolute_stacks_keep_common_numeric_scale(self):
        root=E.fromstring(render({'type':'stacked','normalize':False,'series':['a','b'],'rows':[{'label':'x','values':[3,1]},{'label':'y','values':[6,2]}]}))
        bars=[float(e.get('width')) for e in root.findall('.//s:rect',NS) if e.get('height')=='38']
        self.assertEqual(sum(bars[2:]),2*sum(bars[:2]))

    def test_zero_negative_and_nonfinite_stacks_fail(self):
        for values in ([0,0],[-1,2],[float('nan'),1]):
            with self.assertRaises(ValueError):render({'type':'stacked','series':['a','b'],'rows':[{'label':'x','values':values}]})

    def test_reference_is_included_in_trend_axis(self):
        data={'type':'trend','x':[1,2],'series':[{'name':'a','values':[2,3]}],'references':[{'label':'目标','value':10}]}
        root=E.fromstring(render(data));self.assertIn('目标 10',''.join(root.itertext()))
        with self.assertRaises(ValueError):render({**data,'y_max':5})
        with self.assertRaises(ValueError):render({**data,'x':[2,1]})

    def test_heatmap_missing_is_not_zero(self):
        root=E.fromstring(render({'type':'heatmap','rows':['a'],'columns':['x','y'],'values':[[None,0]]}))
        texts=[e.text for e in root.findall('.//s:text',NS)]
        self.assertIn('—',texts);self.assertIn('0',texts)
        with self.assertRaises(ValueError):render({'type':'heatmap','rows':['a'],'columns':['x'],'values':[[1,2]]})

    def test_wrapped_matrix_text_stays_inside_its_cells(self):
        root=E.fromstring(render({'type':'matrix','rows':['甲','乙'],'columns':['一','二'],'values':[['长中文标签自动换行'*5,'短'],['短','长中文标签自动换行'*3]]}))
        cells=[e for e in root.findall('.//s:rect',NS) if e.get('rx')=='4']
        left=min(float(e.get('x')) for e in cells);top=min(float(e.get('y')) for e in cells)
        for e in root.findall('.//s:g/s:text',NS):
            x,y=float(e.get('x')),float(e.get('y'))
            if x>=left and y>=top:
                self.assertTrue(any(float(c.get('x'))<=x<=float(c.get('x'))+float(c.get('width')) and float(c.get('y'))+12<=y<=float(c.get('y'))+float(c.get('height')) for c in cells))

    def test_set_membership_uses_exact_items(self):
        root=E.fromstring(render({'type':'sets','sets':[{'label':'A','items':['甲','同']},{'label':'B','items':['同','乙']}]}))
        texts=[e.text for e in root.findall('.//s:text',NS)]
        self.assertEqual(texts.count('同'),1)
        self.assertIn('甲',texts);self.assertIn('乙',texts)

    def test_gantt_duration_uses_actual_dates(self):
        root=E.fromstring(render({'type':'gantt','rows':[{'label':'a','start':'2026-01-01','end':'2026-01-03'},{'label':'b','start':'2026-01-01','end':'2026-01-05'}]}))
        widths=[float(e.get('width')) for e in root.findall('.//s:rect',NS) if e.get('height')=='34']
        self.assertEqual(widths[1],2*widths[0])
        with self.assertRaises(ValueError):render({'type':'gantt','rows':[{'label':'a','start':5,'end':2}]})

    def test_containment_children_stay_inside_parent(self):
        root=E.fromstring(render({'type':'containment','root':{'label':'整体','children':[{'label':'很长的中文名称用于确认自动换行后的框仍有足够空间'*3},{'label':'第二部分'}]}}))
        rects=[e for e in root.findall('.//s:g/s:rect',NS)]
        outer=rects[0];ox,oy,ow,oh=[float(outer.get(k)) for k in ('x','y','width','height')]
        for r in rects[1:]:
            x,y,w,h=[float(r.get(k)) for k in ('x','y','width','height')]
            self.assertGreaterEqual(x,ox);self.assertGreaterEqual(y,oy)
            self.assertLessEqual(x+w,ox+ow);self.assertLessEqual(y+h,oy+oh)

    def test_escaping_and_bad_mapping(self):
        data={'type':'mapping','left':[{'id':'a','label':'<script>&甲'}],'right':[{'id':'b','label':'乙'}],'links':[{'from':'a','to':'b'}]}
        self.assertIn('&lt;script&gt;',render(data))
        with self.assertRaises(ValueError):render({**data,'links':[{'from':'z','to':'b'}]})


if __name__=='__main__':unittest.main()
