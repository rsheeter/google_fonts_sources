from absl import flags
from pathlib import Path
from typing import List


FLAGS = flags.FLAGS


flags.DEFINE_string("gf_repo", str(Path.home() / "oss" / "fonts"), "A local clone of https://github.com/google/fonts")


def repo() -> Path:
    gf_repo = Path(FLAGS.gf_repo)
    assert gf_repo.is_dir()
    return gf_repo


def ls() -> List[Path]:
    return list(repo().rglob("upstream.yaml"))