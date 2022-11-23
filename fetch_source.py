from absl import app
from absl import flags
from collections import defaultdict
from pathlib import Path
import sys
from urllib.parse import urlparse
import yaml


FLAGS = flags.FLAGS


flags.DEFINE_string("gf_repo", str(Path.home() / "oss" / "fonts"), "A local clone of https://github.com/google/fonts")


def source_dir(name):
    wd = Path(__file__).parent / "sources" / name
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def failure_dir():
    return source_dir("failures")


def failure_file(failure_type):
    return failure_dir() / (failure_type + ".txt")


def main(argv):
    gf_repo = Path(FLAGS.gf_repo)
    assert gf_repo.is_dir()

    status_dir = source_dir("status")
    for stale_file in failure_dir().iterdir():
        stale_file.unlink()

    upstream_files = list(gf_repo.rglob("upstream.yaml"))
    failures = []
    for upstream_file in upstream_files:
        with open(upstream_file) as f:
            try:
                upstream = yaml.safe_load(f)
            except yaml.YAMLError as e:
                failures.append(("bad_yaml", upstream_file.relative_to(gf_repo), e))
                continue

            if not "repository_url" in upstream:
                maybe_archive = upstream.get("archive", "")
                if maybe_archive is not None and maybe_archive.startswith("https://github.com"):
                    failures.append(("github_archive_no_repo_url", upstream_file.relative_to(gf_repo)))
                    repo_path = "/".join(urlparse(upstream["archive"]).path.split("/")[:2])
                    upstream["repository_url"] = "https://github.com/" + repo_path
                else:
                    failures.append(("no_repo_url", upstream_file.relative_to(gf_repo)))
                    continue

        status_file = status_dir / (upstream_file.stem + ".status")
        if status_file.is_file():
            continue

    count_by_type = defaultdict(int)
    for failure in failures:
        count_by_type[failure[0]] += 1
        with open(failure_file(failure[0]), "a") as f:
            f.write(" ".join(str(f) for f in failure[1:]))
            f.write("\n")

    print(f"{len(upstream_files)} upstream.yaml files")
    for fail_type, count in sorted(count_by_type.items()):
        print(f"{count}/{len(upstream_files)} {fail_type} ({failure_file(fail_type).relative_to(Path(__file__).parent)})")

    if failures:
        sys.exit(1)

if __name__ == "__main__":
    app.run(main)
