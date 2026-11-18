#!/usr/bin/env python3
"""Add each sprite's visible box (x,y,w,h inside the 96x96 PNG) as a 4th column of names.txt.

The device uses it to scale every Pokémon to the same on-screen size and to centre it.
Usage: python tools/add_sprite_boxes.py <folder with 1.png..1025.png> pokedex/names.txt
Sprites: https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/<n>.png
"""
import os
import sys

from PIL import Image

folder, names_path = sys.argv[1], sys.argv[2]
lines = []
for line in open(names_path, encoding='utf-8').read().splitlines():
    cols = line.split('\t')[:3]
    im = Image.open(os.path.join(folder, f'{cols[0]}.png')).convert('RGBA')
    box = im.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox() or (0, 0, im.width, im.height)
    x0, y0, x1, y1 = box
    cols.append(f'{x0},{y0},{x1 - x0},{y1 - y0}')
    lines.append('\t'.join(cols))
with open(names_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('boxes added:', len(lines))
