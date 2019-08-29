#!/usr/bin/env python3

import fontTools.agl

from fontTools.ttLib import TTFont

font = TTFont('SansBullshitSans.ttf')

gsub = font['GSUB'].table


def str2UnicodeNames(s):
    return [fontTools.agl.UV2AGL.get(ord(c), c) for c in s]


def unicodeNames2str(l):
    return ''.join([chr(fontTools.agl.AGL2UV.get(c, None)) for c in l])


# Based on https://github.com/googlefonts/nototools/blob/
#   bb309e87d273b3afd89b6c66c43b332899e74f5d/nototools/hb_input.py#L143
all_ligatures = dict()
ligature_glyphs = set()
multi_ligature_glyphs = set()
for lookup_index, lookup in enumerate(gsub.LookupList.Lookup):
    for st in lookup.SubTable:
        if lookup.LookupType == 4:
            for prefix, ligatures in st.ligatures.items():
                for ligature in ligatures:
                    s = unicodeNames2str([prefix] + list(ligature.Component))
                    print(f"{len(ligature.Component)+1} "
                          f"{ligature.LigGlyph} {s}")
                    # print(f"len={len(s)}, string={s}, "
                    # f"LigGlyph={ligature.LigGlyph}")
                    all_ligatures[s] = ligature.LigGlyph
                    if ligature.LigGlyph in ligature_glyphs:
                        multi_ligature_glyphs.add(ligature.LigGlyph)
                    ligature_glyphs.add(ligature.LigGlyph)
