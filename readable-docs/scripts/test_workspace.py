import json
from pathlib import Path
import tempfile
import unittest

from workspace import assemble, compare, index, manifest, pair, snapshot, split


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.body = '# 示例\n\n## 第一章\n\n原文。\n\n```md\n## 这是代码\n```\n\n## 第二章\n\n结束。\n'
        (self.source / 'draft.md').write_text('# 写作依据\n目的：解释。\n\n# 文档草稿\n' + self.body)

    def test_roundtrip_and_order(self):
        self.assertEqual(split(self.source / 'draft.md')['chapters'], 2)
        self.assertEqual(assemble(self.source).read_text(), self.body)
        with self.assertRaises(ValueError):split(self.source / 'draft.md')
        data = json.loads((self.source / 'chapters.json').read_text())
        data['chapters'].reverse()
        (self.source / 'chapters.json').write_text(json.dumps(data))
        assembled = assemble(self.source).read_text()
        self.assertLess(assembled.index('第二章'), assembled.index('第一章'))
        self.assertNotIn('目的：', assembled)

    def test_introduction_is_reviewable(self):
        draft = self.source / 'draft.md'
        draft.write_text('# 文档草稿\n# 标题\n\n这是必要的导语。\n\n## 正文\n内容。\n')
        self.assertEqual(split(draft)['chapters'], 2)
        self.assertIn('必要的导语', (self.source / '00.md').read_text())
        self.assertEqual(assemble(self.source).read_text(), draft.read_text().split('# 文档草稿\n', 1)[1])

    def test_immutable_pairs_and_stage_assets(self):
        split(self.source / 'draft.md')
        snapshot(self.source, self.root / 'stages' / 'text')
        pair(self.source, '01', self.root / 'pairs', 'before')
        figures = self.source / 'figures'
        figures.mkdir()
        (figures / '图.svg').write_text('<svg/>')
        (figures / '图.json').write_text('{"title":"图"}')
        chapter = self.source / '01.md'
        chapter.write_text('## 第一章\n\n![图](figures/图.svg)\n')
        pair(self.source, '01', self.root / 'pairs', 'after')
        self.assertEqual((self.root / 'pairs/01/after/figures/图.json').read_text(), '{"title":"图"}')
        (figures / '图.svg').write_text('<svg>新图</svg>')
        pair(self.source, '01', self.root / 'pairs', 'rev01')
        self.assertEqual((self.root / 'pairs/01/after/figures/图.svg').read_text(), '<svg/>')
        self.assertIn('新图', (self.root / 'pairs/01/rev01.diff').read_text())
        self.assertEqual((self.root / 'stages/text/document.md').read_text(), self.body)
        with self.assertRaises(ValueError):pair(self.source, '01', self.root / 'pairs', 'after')
        with self.assertRaises(ValueError):snapshot(self.source, self.source / 'recursive')
        with self.assertRaises(ValueError):pair(self.source, '02', self.root / 'pairs', 'after')
        index(self.source, self.root / 'index.md')
        self.assertIn('source/01.md', (self.root / 'index.md').read_text())

    def test_invalid_paths_and_resources(self):
        split(self.source / 'draft.md')
        chapter = self.source / '01.md'
        chapter.write_text('## 一\n![丢失](figures/missing.svg)')
        with self.assertRaises(ValueError):pair(self.source, '01', self.root / 'pairs', 'before')
        self.assertFalse((self.root / 'pairs/01/before').exists())
        data = json.loads((self.source / 'chapters.json').read_text())
        data['chapters'][0]['id'] = '../escape'
        (self.source / 'chapters.json').write_text(json.dumps(data))
        with self.assertRaises(ValueError):manifest(self.source)
        with self.assertRaises(ValueError):compare(self.root / 'absent', self.source)


if __name__ == '__main__':unittest.main()
