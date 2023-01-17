"""Prints tokens found in .glyphs file(s)
"""
from absl import app
from absl import flags
import glyphsLib
from pathlib import Path
import re
import sys
from typing import Tuple


FLAGS = flags.FLAGS


def tok_type(tok):
    number_token_re = r"\$\{([^}]+)\}"
    glyph_predicate_re = r"\$\[([^\]]+)\]"
    bare_number_value_re = r"\$(\w+)\b"
    if re.match(number_token_re, tok):
        return "number"
    if re.match(glyph_predicate_re, tok):
        return "glyph"
    if re.match(bare_number_value_re, tok):
        return "bare_num"
    return "<unknown>"


def feature_tokens(font: glyphsLib.GSFont) -> Tuple[str,...]:
    def tokens(fea_type, features):
        result = []
        for fea in features:
            toks = re.findall(r"[$][^$ ;]+", fea.code)
            if not toks:
                continue
            for tok in toks:
                result.append((fea_type, tok_type(tok), tok))
        return tuple(result)

    return (tokens("prefix", font.featurePrefixes)
        + tokens("class", font.classes)
        + tokens("feature", font.features))


def main(argv):
    for source in argv[1:]:
        source = Path(source)
        font = glyphsLib.load(source)
        for fea_type, tok_type, tok in sorted(set(feature_tokens(font))):
            possible_values = []
            print(source.name, fea_type, tok_type, tok)#, " values:{" + ", ".join(possible_values) + "}")


if __name__ == "__main__":
    app.run(main)
