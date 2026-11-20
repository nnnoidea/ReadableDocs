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

    def test_focus_changes_appearance_without_changing_bar_values(self):
        data={'type':'bar','labels':['甲','乙','丙'],'values':[12,18,-5]}
        def bars(d):
            return [e for e in E.fromstring(render(d)).findall('.//s:rect',NS) if e.get('stroke')=='none']
        plain,focused=bars(data),bars({**data,'focus':['乙']})
        self.assertEqual(len(plain),3)
        for a,b in zip(plain,focused):
            self.assertEqual([a.get(k) for k in ('x','y','width','height')],[b.get(k) for k in ('x','y','width','height')])
            self.assertLessEqual(float(b.get('width')),48)
        self.assertNotEqual(focused[0].get('fill'),focused[1].get('fill'))
        self.assertEqual(focused[0].get('fill'),focused[2].get('fill'))
        with self.assertRaises(ValueError):render({**data,'focus':['不存在']})

    def test_simple_flow_orientation_preserves_edges_and_emphasis(self):
        data={'type':'flow','nodes':[{'id':'a','label':'输入'},{'id':'b','label':'处理','emphasis':True},{'id':'c','label':'输出'}],
              'edges':[{'from':'a','to':'b','emphasis':True},{'from':'b','to':'c'}]}
        auto=E.fromstring(render(data));vertical=E.fromstring(render({**data,'direction':'vertical'}))
        self.assertLess(float(auto.get('height')),float(vertical.get('height')))
        edges=[e for e in auto.findall('.//s:polyline',NS) if e.get('marker-end')]
        self.assertEqual(len(edges),2)
        self.assertNotEqual(edges[0].get('stroke'),edges[1].get('stroke'))
        with self.assertRaises(ValueError):render({**data,'direction':'sideways'})

    def test_selected_labels_keep_all_data_and_separate_close_endpoints(self):
        data={'type':'trend','x':[1,2,3],'series':[{'name':'甲','values':[1,2,3],'emphasis':True},{'name':'乙','values':[2,2.5,3.01]}],
              'references':[{'label':'目标','value':3.02}],'label_indices':[2]}
        root=E.fromstring(render(data));circles=root.findall('.//s:circle',NS)
        self.assertEqual(len(circles),6)
        # Near-identical endpoint values get separate callouts while their plotted Y coordinates stay near-identical.
        end_y=[float(circles[i].get('cy')) for i in (2,5)]
        self.assertLess(abs(end_y[0]-end_y[1]),3)
        labels=[e for e in root.findall('.//s:text',NS) if (e.text or '').startswith(('甲 ','乙 ','目标 '))]
        self.assertEqual(len(labels),3)
        ys=sorted(float(e.get('y')) for e in labels)
        self.assertTrue(all(b-a>=24 for a,b in zip(ys,ys[1:])))
        with self.assertRaises(ValueError):render({**data,'label_indices':[3]})

    def test_header_uses_final_chart_width(self):
        from canvas import text_width
        data={'type':'bar','title':'这是一个需要根据最终窄画布进行换行的较长中文图标题，用于检查文字不会溢出',
              'labels':['甲','乙'],'values':[1,2]}
        root=E.fromstring(render(data));width=float(root.get('width'))
        titles=[e for e in root.findall('s:text',NS) if e.get('font-size')=='27']
        self.assertGreater(len(titles),1)
        self.assertTrue(all(float(e.get('x'))+text_width(e.text,27)<=width-20 for e in titles))

    def test_horizontal_bar_negative_values_and_shared_color_map(self):
        data={'type':'bar','orientation':'horizontal','labels':['长名称类别甲','长名称类别乙'],
              'series':[{'name':'基线','y':[-2,4]},{'name':'当前','y':[3,6]}],
              'color_map':{'基线':'#187e75','当前':'#28679b'}}
        def bars(d):return [e for e in E.fromstring(render(d)).findall('.//s:rect',NS) if e.get('height')=='20']
        first=bars(data);second=bars({**data,'series':list(reversed(data['series']))})
        self.assertEqual([v.get('fill') for v in first],['#187e75','#28679b']*2)
        self.assertEqual([v.get('fill') for v in second],['#28679b','#187e75']*2)
        self.assertAlmostEqual(float(first[3].get('width')),float(first[1].get('width'))*2,delta=.002)
        self.assertLess(float(first[0].get('x')),float(first[1].get('x')))

    def test_focus_path_follows_only_existing_edges(self):
        data={'type':'flow','nodes':[{'id':'a','label':'输入'},{'id':'b','label':'处理'},{'id':'c','label':'输出'}],
              'edges':[{'from':'a','to':'b'},{'from':'b','to':'c'}],'focus_path':['a','b','c']}
        root=E.fromstring(render(data))
        self.assertTrue(all(e.get('stroke')=='#187e75' for e in root.findall('.//s:polyline',NS)))
        with self.assertRaises(ValueError):render({**data,'focus_path':['a','c']})

    def test_new_numeric_forms_keep_values_and_differences(self):
        root=E.fromstring(render({'type':'meter','value':120,'target':100,'unit':'条'}))
        self.assertIn('超过目标 20 条',''.join(root.itertext()))
        with self.assertRaises(ValueError):render({'type':'meter','value':1,'target':0})
        with self.assertRaises(ValueError):render({'type':'stat','value':float('nan'),'label':'结果'})
        root=E.fromstring(render({'type':'before-after','rows':[{'label':'甲','before':48,'after':31}]}))
        text=''.join(root.itertext());self.assertIn('48',text);self.assertIn('31',text);self.assertIn('-17',text)

    def test_gap_is_computed_from_named_values(self):
        d={'type':'trend','x':[1,2],'series':[{'name':'当前','values':[.6,.7]}],
           'references':[{'label':'目标','value':.8}],'gap':{'series':'当前','reference':'目标','display_scale':100,'unit':'百分点'}}
        text=''.join(E.fromstring(render(d)).itertext())
        self.assertIn('当前 − 目标 = -10 百分点',text)
        with self.assertRaises(ValueError):render({**d,'gap':{'series':'不存在','reference':'目标'}})

    def test_ordinary_line_uses_endpoint_leaders(self):
        d={'type':'line','series':[{'name':'甲','x':[1,2],'y':[1,3]},{'name':'乙','x':[1,2],'y':[2,3.01]}]}
        root=E.fromstring(render(d))
        labels=[e for e in root.findall('.//s:text',NS) if (e.text or '').startswith(('甲 ','乙 '))]
        self.assertEqual(len(labels),2)
        self.assertGreater(abs(float(labels[0].get('y'))-float(labels[1].get('y'))),24)

    def test_long_lane_steps_and_mapping_nodes_do_not_overlap(self):
        cases=[{'type':'swimlane','lanes':['执行方'],'steps':[{'lane':'执行方','text':'准备'},{'lane':'执行方','text':'含有较长说明的步骤'*18}]},
               {'type':'mapping','left':[{'id':'a','label':'短'},{'id':'b','label':'较长对象名称'*20}],
                'right':[{'id':'c','label':'输出'}],'links':[{'from':'a','to':'c'},{'from':'b','to':'c'}]}]
        for d in cases:
            root=E.fromstring(render(d));rects=root.findall('.//s:g/s:rect',NS)
            columns={}
            for r in rects:columns.setdefault(r.get('x'),[]).append(r)
            for col in columns.values():
                ordered=sorted(col,key=lambda r:float(r.get('y')))
                for a,b in zip(ordered,ordered[1:]):self.assertLess(float(a.get('y'))+float(a.get('height')),float(b.get('y')))
            self.assertLess(max(float(r.get('y'))+float(r.get('height')) for r in rects),float(root.get('height')))

    def test_tall_flow_node_connector_stays_in_inter_node_gap(self):
        d={'type':'flow','direction':'vertical','nodes':[{'id':'a','label':'长内容'*35},{'id':'b','label':'下一步'}],
           'edges':[{'from':'a','to':'b'}]}
        root=E.fromstring(render(d));edge=root.find('.//s:polyline',NS)
        points=[tuple(map(float,p.split(','))) for p in edge.get('points').split()]
        self.assertTrue(all(a[1]<=b[1] for a,b in zip(points,points[1:])))

    def test_wrapping_keeps_identifiers_intact_when_they_fit(self):
        from canvas import lines
        rows=lines('确认返回的 response_mapper 与 Stage2.row_id',24)
        self.assertTrue(any('response_mapper' in row for row in rows))
        self.assertTrue(any('Stage2.row_id' in row for row in rows))
        self.assertEqual(''.join(lines('a'*60,24)),'a'*60)
        self.assertTrue(all(len(row)<=24 for row in lines('a'*60,24)))


if __name__=='__main__':unittest.main()
