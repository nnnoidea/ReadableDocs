"""Checks meaning-preserving layouts, routing and reusable visual components."""
import copy
import unittest
import xml.etree.ElementTree as ET

from canvas import SVG, COLORS
from draw import render, load_template
from structures import connect, connect_objects, intersects, ports, group_plan, SYMBOLS, symbol

NS={'s':'http://www.w3.org/2000/svg'}


class Structures(unittest.TestCase):
    def test_connectors_avoid_unrelated_nodes_and_keep_endpoints(self):
        boxes={'a':(70,150,120,80),'b':(390,150,120,80),'obstacle':(230,130,100,150)}
        edges=[{'from':'a','to':'b','label':'发送','emphasis':True},
               {'from':'b','to':'a','from_side':'bottom','to_side':'bottom','dash':True},
               {'from':'a','to':'a','from_side':'left','to_side':'top'}]
        paths=connect(SVG(650,500),boxes,edges)
        self.assertEqual(len(paths),len(edges))
        for edge,path in zip(edges,paths):
            self.assertIn(path[0],ports(boxes[edge['from']]).values())
            self.assertIn(path[-1],ports(boxes[edge['to']]).values())
            for a,b in zip(path,path[1:]):
                for rect in boxes.values():self.assertFalse(intersects(a,b,rect))
            for a,b in zip(path[1:-1],path[2:-1]):
                for x,y,w,h in boxes.values():self.assertFalse(intersects(a,b,(x-6,y-6,w+12,h+12)))

    def test_symbol_connections_touch_glyphs_and_avoid_captions(self):
        nodes=[{'id':'a','label':'搜索','presentation':'symbol'},{'id':'b','label':'输出'}]
        rects={'a':(80,160,230,110),'b':(420,160,230,80)}
        paths=connect_objects(SVG(760,500),nodes,rects,[{'from':'a','to':'b'}])
        self.assertEqual(paths[0][0],(219,202))
        label=(96,232,198,38)
        self.assertTrue(all(not intersects(a,b,label) for a,b in zip(paths[0],paths[0][1:])))

    def test_branch_merge_and_feedback_have_correct_edges(self):
        d={'template':'flow','direction':'horizontal',
           'nodes':[{'id':i,'label':i,'symbol':'process'} for i in 'abcd'],
           'edges':[{'from':'a','to':'b'},{'from':'a','to':'c'},{'from':'b','to':'d'},
                    {'from':'c','to':'d'},{'from':'d','to':'a','dash':True,'label':'返工','color':COLORS[2]}]}
        root=ET.fromstring(render(d));edges=root.findall('.//s:polyline',NS)
        edges=[e for e in edges if e.get('marker-end')]
        self.assertEqual(len(edges),5)
        markers={m.get('id'):m.find('s:path',NS).get('fill') for m in root.findall('.//s:marker',NS)}
        for e in edges:self.assertEqual(markers[e.get('marker-end')[5:-1]],e.get('stroke'))

    def test_opposing_transitions_use_distinct_ports(self):
        boxes={'a':(170,140,160,80),'b':(170,330,160,80)}
        paths=connect(SVG(650,550),boxes,[{'from':'a','to':'b','label':'开始'},
                                        {'from':'b','to':'a','label':'返回'}])
        self.assertNotEqual(paths[0],list(reversed(paths[1])))
        self.assertEqual(paths[1][0],ports(boxes['b'])['right'])
        self.assertEqual(paths[1][-1],ports(boxes['a'])['right'])

    def test_template_does_not_fill_sample_column_content(self):
        with self.assertRaises(KeyError):
            render({'template':'aligned-process','rows':[{'label':'实际步骤','cells':['甲','乙','丙']}]})

    def test_group_rows_and_cycle_validation(self):
        group={'label':'分组','nodes':[{'id':x,'label':x} for x in 'abcd']}
        edges=[{'from':'a','to':'b'},{'from':'a','to':'c'},{'from':'b','to':'d'},{'from':'c','to':'d'}]
        _,_,_,boxes=group_plan(group,edges)
        self.assertEqual(boxes['b'][1],boxes['c'][1])
        self.assertLess(boxes['a'][1],boxes['b'][1]);self.assertLess(boxes['c'][1],boxes['d'][1])
        with self.assertRaises(ValueError):group_plan(group,edges+[{'from':'d','to':'a'}])
        group_plan(group,edges+[{'from':'d','to':'a','feedback':True}])
        with self.assertRaises(ValueError):group_plan({**group,'rows':[['a','b','c']]},edges)

    def test_shared_steps_align_long_cells_and_preserve_absence(self):
        data={'template':'aligned-process','title':'测试','columns':['甲','乙'],'rows':[
            {'label':'读取','cells':[{'label':'A0','detail':'需要完整保留的较长说明'*12},{'label':'B0'}]},
            {'label':'可选步骤','cells':[None,{'label':'B1'}]},
            {'label':'结果','cells':[{'label':'A2'},{'label':'B2'}]}]}
        root=ET.fromstring(render(data))
        text={e.text:float(e.get('y')) for e in root.findall('.//s:text',NS)}
        self.assertEqual(text['A0'],text['B0']);self.assertEqual(text['A2'],text['B2'])
        self.assertGreater(text['B1'],text['B0']+100)
        self.assertEqual(len(root.findall('.//s:polyline[@marker-end]',NS)),2)
        comparison=ET.fromstring(render({**data,'template':'structure-comparison'}))
        self.assertEqual(len(comparison.findall('.//s:polyline[@marker-end]',NS)),0)

    def test_embedded_diagrams_keep_unique_ids_and_explicit_targets(self):
        d=load_template('overview-detail');d['details'].append(copy.deepcopy(d['details'][0]))
        root=ET.fromstring(render(d));ids=[e.get('id') for e in root.iter() if e.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(len(root.findall('.//s:polyline[@stroke-dasharray]',NS)),2)
        d['details'][0]['target']='absent'
        with self.assertRaises(ValueError):render(d)

    def test_symbols_escape_labels_and_keep_explicit_results(self):
        for kind in SYMBOLS:
            s=SVG(200,180);symbol(s,50,100,kind);ET.fromstring(s.finish())
        d={'template':'flow','nodes':[{'id':'a','label':'<输入>&','symbol':'result','status':'fail'}]}
        self.assertIn('&lt;输入&gt;&amp;',render(d))
        with self.assertRaises(ValueError):render({**d,'nodes':[{'id':'a','label':'a','symbol':'unknown'}]})
        d=load_template('grouped-flow');d['edges'][0]['to']='missing'
        with self.assertRaises(ValueError):render(d)


if __name__=='__main__':unittest.main()
