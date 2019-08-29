#!/usr/bin/env python3

import argparse
import collections
import json
import sys

import fontTools.agl

from fontTools.ttLib import TTFont

parser = argparse.ArgumentParser()
parser.add_argument('in_ttf', type=str,
                    help='Input TrueType font file (.ttf).')
parser.add_argument('-o', '--output', type=str, dest='out_ttf',
                    help='Output TrueType font file (.ttf).')
parser.add_argument('--write-glyphs-json', type=str, dest='glyphs_out')
parser.add_argument('--read-glyphs-json', type=str, dest='glyphs_in')
parser.add_argument('--read-word-list', nargs='?', dest='words_in',
                    type=argparse.FileType('r'),
                    default=None)
parser.add_argument('--write-word-list', nargs='?', dest='words_out',
                    type=argparse.FileType('w'),
                    default=None)
args = parser.parse_args()

if not args.in_ttf or (args.words_in and args.words_out) or\
        (args.glyphs_in and args.glyphs_out):
    parser.print_help()
    sys.exit()
font = TTFont(args.in_ttf)

gsub = font['GSUB'].table


def str2UnicodeNames(s):
    return [fontTools.agl.UV2AGL.get(ord(c), c) for c in s]


def unicodeNames2str(l):
    return ''.join([chr(fontTools.agl.AGL2UV.get(c, None)) for c in l])


# Based on https://github.com/googlefonts/nototools/blob/
#   bb309e87d273b3afd89b6c66c43b332899e74f5d/nototools/hb_input.py#L143
all_ligatures_by_comp = dict()
ligatures_by_glyph = collections.defaultdict(list)
ligature_glyphs = set()
multi_ligature_glyphs = set()
ligatures_subtable = None
for lookup_index, lookup in enumerate(gsub.LookupList.Lookup):
    for st in lookup.SubTable:
        if lookup.LookupType == 4:
            ligatures_subtable = st
            for prefix, ligatures in st.ligatures.items():
                for ligature in ligatures:
                    full_comp = [prefix] + list(ligature.Component)
                    s = unicodeNames2str(full_comp)
                    if args.words_out:
                        print(s, file=args.words_out)
                    ligatures_by_glyph[ligature.LigGlyph].append(s)
                    if ligature.LigGlyph in ligature_glyphs:
                        multi_ligature_glyphs.add(ligature.LigGlyph)
                    ligature_glyphs.add(ligature.LigGlyph)
                    all_ligatures_by_comp[tuple(full_comp)] = ligature.LigGlyph

min_lengths = {glyph: min(len(s) for s in ligatures_by_glyph[glyph])
               for glyph in multi_ligature_glyphs}
if args.glyphs_out:
    with open(args.glyphs_out, 'w') as outfile:
        json.dump(min_lengths, outfile)


if args.out_ttf and args.words_in:
    if args.glyphs_in:
        with open(args.glyphs_in) as json_file:
            min_lengths = json.load(json_file)
    wordlist = args.words_in.readlines()
    glyph_lookup = {v: k for k, v in min_lengths.items()}
    last_glyph = glyph_lookup[min(glyph_lookup.keys())]
    largest_glyph = glyph_lookup[max(glyph_lookup.keys())]
    for i in range(max(glyph_lookup.keys())):
        if i in glyph_lookup:
            last_glyph = glyph_lookup[i]
        else:
            glyph_lookup[i] = last_glyph

    glyphs_to_clear = min_lengths.keys()
    all_ligatures_by_comp = {k: v for k, v in all_ligatures_by_comp.items()
                             if v not in glyphs_to_clear}

    for word in wordlist:
        word = word.strip()
        all_ligatures_by_comp[tuple(str2UnicodeNames(word))] =\
            glyph_lookup.get(len(word), largest_glyph)

    ligatures_subtable.ligatures = all_ligatures_by_comp


if args.out_ttf:
    font.save(args.out_ttf)
