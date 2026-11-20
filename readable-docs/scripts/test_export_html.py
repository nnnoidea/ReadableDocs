"""Integration checks for the real Pandoc export. Requires Pandoc or pypandoc_binary."""
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from urllib.parse import unquote

from export_html import export


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.images = []
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        attrs = dict(attrs)
        if tag == 'img':self.images.append(attrs['src'])
        if tag == 'a':self.links.append(attrs['href'])


class Export(unittest.TestCase):
    def test_content_images_math_and_links_survive_portable_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / '源稿'
            source.mkdir()
            svg = source / '图 一.svg'
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80"><text x="10" y="40">重点</text></svg>')
            attachment = source / '材料.txt'
            attachment.write_text('附件内容')
            doc = source / 'document.md'
            original = '''# 阅读测试

## 01 开始

## 02 用于验证长目录标题换行之后仍保留章节编号以及正确的章节链接

![图的重点](<图 一.svg>)

| 条件 | 数值 |
| --- | --- |
| 已完成 | 42 |

```json
{"keep": "<original>"}
```

公式：$x^2 + y^2$。

[本地材料](材料.txt) 与 [外链](https://example.com/read)。

<script>alert("原始片段作为文本")</script>
'''
            doc.write_text(original)
            output = root / '阅读版' / 'document.html'
            result = export(doc, output)
            html = output.read_text()
            page = Page(html)
            self.assertEqual(result['images'], 1)
            self.assertEqual(html.count('class="toc-number"'), 2)
            self.assertTrue(page.images[0].startswith('data:image/svg+xml'))
            self.assertIn('table', page.tags)
            self.assertIn('pre', page.tags)
            self.assertIn('math', page.tags)
            self.assertIn('style', page.tags)
            self.assertNotIn('script', page.tags)
            self.assertNotIn('link', page.tags)
            self.assertIn('https://example.com/read', page.links)
            local = next(v for v in page.links if v.endswith('.txt'))
            self.assertEqual((output.parent / unquote(local)).resolve(), attachment.resolve())
            self.assertEqual(doc.read_text(), original)
            before = html
            svg.write_text(svg.read_text().replace('重点', '更新后的重点'))
            export(doc, output)
            self.assertNotEqual(before, output.read_text())

    def test_missing_image_preserves_existing_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / 'document.md'
            output = doc.with_suffix('.html')
            output.write_text('已有的可读版本')
            doc.write_text('# 文档\n\n![图](不存在.png)')
            with self.assertRaisesRegex(ValueError, 'Missing image'):
                export(doc)
            self.assertEqual(output.read_text(), '已有的可读版本')

    def test_remote_images_are_reported_and_source_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / 'document.md'
            doc.write_text('# 文档\n\n![图](https://example.com/image.png)')
            with self.assertRaisesRegex(ValueError, 'source package'):
                export(doc)
            with self.assertRaisesRegex(ValueError, 'must differ'):
                export(doc, doc)


if __name__ == '__main__':unittest.main()
