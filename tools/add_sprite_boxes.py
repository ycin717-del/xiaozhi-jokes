#!/usr/bin/env python3
"""Fill the 4th column of names.txt with each sprite's visible box (x,y,w,h inside the 96x96 PNG).

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
    cols = line.split('\t')
    im = Image.open(os.path.join(folder, f'{cols[0]}.png')).convert('RGBA')
    box = im.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox() or (0, 0, im.width, im.height)
    x0, y0, x1, y1 = box
    box_text = f'{x0},{y0},{x1 - x0},{y1 - y0}'
    if len(cols) > 3:
        cols[3] = box_text  # Keep later columns (evolution stages)
    else:
        cols.append(box_text)
    lines.append('\t'.join(cols))
with open(names_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('boxes added:', len(lines))
