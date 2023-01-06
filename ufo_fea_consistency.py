r"""Check if .designspace has consistent feature files.

Usage:
    python ufo_fea_consistency.py path/to/file.designspace
    find . -name '*.designspace' -exec python ufo_fea_consistency.py {} \;
"""

from absl import app
from absl import flags
import filecmp
from fontTools.designspaceLib import DesignSpaceDocument
from pathlib import Path
from typing import Tuple


def find_fea_files(ds_dir: Path, ds: DesignSpaceDocument) -> Tuple[Path, ...]:
    fea_files = {ds_dir / source.filename / "features.fea" for source in ds.sources}
    return tuple(f for f in fea_files if f.is_file())


def main(argv):
    for ds_file in argv[1:]:
        assert ds_file.endswith(".designspace"), f"Args should be .designspace files; what is {ds_file}"
        ds = DesignSpaceDocument.fromfile(ds_file)
        fea_files = find_fea_files(Path(ds_file).parent, ds)
        if not fea_files:
            print(ds_file, "has no features")
            continue
        for f2 in fea_files[1:]:
            if not filecmp.cmp(fea_files[0], f2, shallow=False):
                print(ds_file, "has INCONSISTENT features")
            else:
                print(ds_file, f"has {len(fea_files)} consistent feature files")

if __name__ == "__main__":
    app.run(main)