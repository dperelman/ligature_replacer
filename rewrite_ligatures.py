#!/usr/bin/env python3

import argparse
import collections
import json
import sys

import fontTools.agl

from fontTools.ttLib import TTFont


def str2UnicodeNames(s):
    return [fontTools.agl.UV2AGL.get(ord(c), c) for c in s]


def unicodeNames2str(l):
    return ''.join([chr(fontTools.agl.AGL2UV.get(c, None)) for c in l])


class LigatureRewriter:
    def __init__(self, in_ttf):
        self.font = TTFont(in_ttf)
        self._load_ligatures()

    def _load_ligatures(self):
        # Based on https://github.com/googlefonts/nototools/blob/
        #   bb309e87d273b3afd89b6c66c43b332899e74f5d/nototools/hb_input.py#L143
        self.all_ligatures_by_comp = dict()
        self.ligatures_by_glyph = collections.defaultdict(list)
        ligature_glyphs = set()
        self.multi_ligature_glyphs = set()
        self.ligatures_subtable = None
        self.wordlist = []
        gsub = self.font['GSUB'].table
        for lookup_index, lookup in enumerate(gsub.LookupList.Lookup):
            for st in lookup.SubTable:
                if lookup.LookupType == 4:
                    self.ligatures_subtable = st
                    for prefix, ligatures in st.ligatures.items():
                        for ligature in ligatures:
                            full_comp = [prefix] + list(ligature.Component)
                            s = unicodeNames2str(full_comp)
                            self.wordlist.append(s)
                            self.ligatures_by_glyph[ligature.LigGlyph]\
                                .append(s)
                            if ligature.LigGlyph in ligature_glyphs:
                                self.multi_ligature_glyphs\
                                    .add(ligature.LigGlyph)
                            ligature_glyphs.add(ligature.LigGlyph)
                            self.all_ligatures_by_comp[tuple(full_comp)]\
                                = ligature.LigGlyph

        self.min_lengths = {glyph: min(len(s)
                            for s in self.ligatures_by_glyph[glyph])
                            for glyph in self.multi_ligature_glyphs}

    def dump_wordlist(self, words_out):
        for (_, l) in self.ligatures_by_glyph:
            for s in l:
                print(s, file=args.words_out)

    def dump_glyphs(self, glyphs_out):
        with open(glyphs_out, 'w') as outfile:
            json.dump(self.min_lengths, outfile)

    def set_glyphs(self, min_lengths):
        self.min_lengths = min_lengths

    def read_glyphs(self, glyphs_in):
        with open(args.glyphs_in) as json_file:
            self.set_min_lengths(json.load(json_file))

    def read_wordlist(self, words_in):
        self.wordlist = args.words_in.readlines()

    def write_ligatures(self, out_ttf):
        glyph_lookup = {v: k for k, v in self.min_lengths.items()}
        last_glyph = glyph_lookup[min(glyph_lookup.keys())]
        largest_glyph = glyph_lookup[max(glyph_lookup.keys())]
        for i in range(max(glyph_lookup.keys())):
            if i in glyph_lookup:
                last_glyph = glyph_lookup[i]
            else:
                glyph_lookup[i] = last_glyph

        glyphs_to_clear = self.multi_ligature_glyphs
        self.all_ligatures_by_comp\
            = {k: v for k, v in self.all_ligatures_by_comp.items()
               if v not in glyphs_to_clear}

        for word in self.wordlist:
            word = word.strip()
            self.all_ligatures_by_comp[tuple(str2UnicodeNames(word))] =\
                glyph_lookup.get(len(word), largest_glyph)

        self.ligatures_subtable.ligatures = self.all_ligatures_by_comp

        self.font.save(out_ttf)


if __name__ == "__main__":
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

    rewriter = LigatureRewriter(args.in_ttf)

    if args.words_out:
        rewriter.dump_wordlist(args.words_out)
    if args.glyphs_out:
        rewriter.dump_glyphs(args.glyphs_out)
    if args.glyphs_in:
        rewriter.read_glyphs(args.glyphs_in)
    if args.words_in:
        rewriter.read_wordlist(args.words_in)
    if args.out_ttf:
        rewriter.write_ligatures(args.out_ttf)
