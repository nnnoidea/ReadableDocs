#!/usr/bin/env python3
"""Render a generated SVG to PNG on macOS using Quick Look and Pillow."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as E
from PIL import Image


def preview(source, output):
    root=E.fromstring(source.read_text())
    x,y,w,h=map(float,root.attrib['viewBox'].split())
    side=max(w,h)
    # Quick Look crops rectangular SVG thumbnails on this host. Render a square,
    # then remove only the added canvas area, retaining all original content.
    root.set('viewBox',f'{x} {y} {side} {side}')
    root.set('width',str(side));root.set('height',str(side))
    with tempfile.TemporaryDirectory() as directory:
        temp=Path(directory)/'preview.svg'
        temp.write_bytes(E.tostring(root,encoding='utf-8'))
        subprocess.run(['qlmanage','-t','-s','1800','-o',directory,str(temp)],check=True,capture_output=True)
        image=Image.open(str(temp)+'.png').convert('RGB')
        scale=image.width/side
        image=image.crop((0,0,round(w*scale),round(h*scale)))
        output.parent.mkdir(parents=True,exist_ok=True);image.save(output)
    print(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();preview(a.input,a.output)
