"""Helps find sources.

Ex, designspaces for VFs with small glyph counts:

python find_source.py --vf_only | sort | head -64
"""
from absl import app
from absl import flags
from lxml import etree
from pathlib import Path
import sys


FLAGS = flags.FLAGS


flags.DEFINE_bool("vf_only", False, "Only display VFs")
flags.DEFINE_bool("mapped_only", False, "Only results where axis/map input != output")


def main(argv):
    sources = Path(__file__).parent / "sources"
    ds_files = sources.rglob("*.designspace")

    for ds_file in ds_files:
        ds = etree.parse(str(ds_file))
        ufos = [ds_file.parent / e.attrib["filename"] for e in ds.xpath("//source")]
        if not ufos:
            continue
        num_glyphs = min(len(list((ufo / "glyphs").glob("*.glif"))) for ufo in ufos)
        if FLAGS.vf_only:
            axes = [(e.attrib["minimum"], e.attrib["default"], e.attrib["maximum"]) for e in ds.xpath("//axis")]
            if not any(axis for axis in axes if len(set(axis)) > 1):
                continue
        if FLAGS.mapped_only:
            mappings = [(e.attrib["input"], e.attrib["output"]) for e in ds.xpath("//axis/map")]
            if not any(m for m in mappings if m[0] != m[1]):
                continue
        print(f"{num_glyphs:>5} {ds_file.relative_to(sources.parent)}")

if __name__ == "__main__":
    app.run(main)
