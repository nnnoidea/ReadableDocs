from pathlib import Path
import tempfile
import unittest

from check_document import check
from export_html import export


class IntegrityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / '图.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><text x="0" y="20">图</text></svg>')
        (self.source / '数据.txt').write_text('data')
        self.md = self.source / 'document.md'
        self.md.write_text('# 标题\n\n## 内容\n\n解释 $x^2$ 与[附件](数据.txt)和[跳转](#内容)。\n\n![图](图.svg)\n\n| 项目 | 数量 |\n| --- | --- |\n| 苹果 | 12 |\n\n```python\nprint("<&>")\n```\n\n脚注[^a]。\n\n[^a]: 注释。\n')
        self.html = self.root / 'out/document.html'
        export(self.md, self.html)
        self.good = self.html.read_text()

    def test_valid_conversion(self):
        result = check(self.md, self.html)
        self.assertEqual(result['errors'], [])
        self.assertEqual((result['images'], result['tables'], result['code_blocks']), (1, 1, 1))
        self.assertGreater(check(self.md)['local_resources'], 0)

    def test_tampered_text_code_table_and_link(self):
        for old, new, expected in [('苹果', '梨', 'Table cells or order differ'),
                                   ('print', 'wrong', 'Code blocks differ'),
                                   ('../source/', '../wrong/', 'Links or their order differ')]:
            with self.subTest(expected=expected):
                self.assertIn(old, self.good)
                self.html.write_text(self.good.replace(old, new))
                self.assertIn(expected, check(self.md, self.html)['errors'])

    def test_stale_and_missing_image(self):
        (self.source / '图.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.assertIn('Image 1 differs', check(self.md, self.html)['errors'])
        (self.source / '图.svg').unlink()
        with self.assertRaises(ValueError):check(self.md, self.html)


if __name__ == '__main__':unittest.main()
