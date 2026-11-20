#!/usr/bin/env python3
"""Convert a publication Markdown source to a portable, styled HTML file using Pandoc."""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import quote, unquote, urlsplit, urlunsplit

FORMAT = 'markdown-raw_html-raw_tex-smart'
STYLE = Path(__file__).resolve().parent.parent / 'assets' / 'document.css'


def pandoc_path():
    binary = shutil.which('pandoc')
    if binary:
        return binary
    try:
        import pypandoc
        return pypandoc.get_pandoc_path()
    except (ImportError, OSError):
        raise ValueError('Install Pandoc, or run: python3 -m pip install pypandoc_binary') from None


def run(binary, args, text=None):
    result = subprocess.run([binary, *args], input=text, capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise ValueError(result.stderr.strip() or 'Pandoc conversion failed')
    return result.stdout


def local_path(target, directory):
    url = urlsplit(target)
    if url.scheme == 'file' and url.netloc in ('', 'localhost'):
        return Path(unquote(url.path)).resolve()
    if not url.scheme and not url.netloc and url.path:
        return (directory / unquote(url.path)).resolve()
    return None


def prepare_resources(node, source_dir, output_dir, images):
    if isinstance(node, dict):
        if node.get('t') in ('Image', 'Link'):
            target = node['c'][-1][0]
            path = local_path(target, source_dir)
            if node['t'] == 'Image':
                if target.startswith('data:image/'):
                    images.append(target)
                elif path is None:
                    raise ValueError(f'Save this image in the source package before export: {target}')
                elif not path.is_file():
                    raise ValueError(f'Missing image: {path}')
                else:
                    node['c'][-1][0] = str(path)
                    images.append(str(path))
            elif path is not None and path.exists():
                url = urlsplit(target)
                relative = Path(os.path.relpath(path, output_dir)).as_posix()
                node['c'][-1][0] = urlunsplit(('', '', quote(relative, safe='/'), url.query, url.fragment))
        for value in node.values():
            prepare_resources(value, source_dir, output_dir, images)
    elif isinstance(node, list):
        for value in node:
            prepare_resources(value, source_dir, output_dir, images)


def export(source, output=None, title=None):
    source = Path(source).resolve()
    output = Path(output).resolve() if output else source.with_suffix('.html')
    if not source.is_file():
        raise ValueError(f'Missing Markdown source: {source}')
    if source == output:
        raise ValueError('HTML output must differ from the Markdown source')
    binary = pandoc_path()
    ast = json.loads(run(binary, [str(source), '--from', FORMAT, '--to', 'json', '--fail-if-warnings']))
    images = []
    prepare_resources(ast, source.parent, output.parent, images)
    # Process notes belong outside the publication Markdown, not in this exporter.
    args = ['--from=json', '--to=html5', '--standalone', '--embed-resources', '--mathml',
            '--toc', '--toc-depth=2', '--section-divs', '--fail-if-warnings',
            '--css', str(STYLE), '--metadata', 'pagetitle=' + (title or source.stem)]
    html = run(binary, args, json.dumps(ast, ensure_ascii=False))
    # Preserve heading text and links; emphasize existing chapter numbers in the sidebar.
    def sidebar(match):
        nav = re.sub(r'(<a\b[^>]*>)([0-9]{1,3})(\s+)',
                     r'\1<span class="toc-number">\2</span>\3', match[1])
        return '<aside class="toc-panel" aria-label="目录"><div class="toc-title">目录</div>' + nav + '</aside>'
    html = re.sub(r'(<nav id="TOC"[^>]*>.*?</nav>)', sidebar, html, count=1, flags=re.S)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep an existing readable export intact if conversion or resource loading fails.
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=output.parent, suffix='.html', delete=False) as temp:
        temp.write(html)
        staged = Path(temp.name)
    try:
        staged.replace(output)
    finally:
        staged.unlink(missing_ok=True)
    return {'output': str(output), 'images': len(images), 'bytes': output.stat().st_size}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Publication Markdown, with relative image references')
    parser.add_argument('output', type=Path, nargs='?', help='Default: the same filename with .html')
    parser.add_argument('--title', help='Browser tab title; document headings remain unchanged')
    args = parser.parse_args()
    try:
        result = export(args.input, args.output, args.title)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))
