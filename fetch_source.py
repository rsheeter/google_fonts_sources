from absl import app
from absl import flags
from collections import defaultdict
from gftools import fonts_public_pb2
from google.protobuf import text_format
import gf_upstream
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlparse
import yaml


_DENY_REPO_URLS = {
    "https://github.com/TypeNetwork/Alegreya",  # prompts for auth
    "https://github.com/googlefonts/glory",  # prompts for auth
}


FLAGS = flags.FLAGS


flags.DEFINE_bool(
    "pull_existing",
    True,
    "Whether to run git pull if a local copy of the source exists.",
)


def source_dir(name):
    wd = Path(__file__).parent / "sources" / name
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def failure_dir():
    return source_dir("failures")


def repo_dir(upstream_file):
    lic = upstream_file.parent.parent.name
    assert lic in ("apache", "ofl", "ufl")
    return source_dir(lic + "/" + upstream_file.parent.name)


def failure_file(failure_type):
    return failure_dir() / (failure_type + ".txt")


def read_proto(proto, path):
  with open(path, 'r', encoding='utf-8') as f:
    proto = text_format.Parse(f.read(), proto)
    return proto


def ignore_venv(dir, contents):
    if "venv" in contents:
        print("skipping venv in", dir)
        return ["venv"]
    else:
        return []


def main(argv):
    for stale_file in failure_dir().iterdir():
        stale_file.unlink()

    gf_repo = gf_upstream.repo()
    metadata_files = gf_upstream.ls()
    failures = []

    local_repos = {}
    local_copies = 0

    for metadata_file in metadata_files:
        try:
            metadata = read_proto(fonts_public_pb2.FamilyProto(), metadata_file)
        except text_format.ParseError:
            failures.append(("unparseable_metadata_file", metadata_file.relative_to(gf_repo)))
            continue

        repo_url = set()
        archive_url = set()

        # does METADATA.pb have repo url and archive url?
        if metadata.source is not None:
            if metadata.source.repository_url:
                repo_url.add(metadata.source.repository_url)
            if metadata.source.archive_url:
                archive_url.add(metadata.source.archive_url)

        # does upstream.yaml have repo url and archive url
        upstream_file = metadata_file.parent / "upstream.yaml"
        if upstream_file.is_file():
            with open(upstream_file) as f:
                try:
                    upstream = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    failures.append(("bad_yaml", upstream_file.relative_to(gf_repo), e))
                    continue

            if upstream.get("archive", ""):
                archive_url.add(upstream.get("archive"))

            if upstream.get("repository_url", ""):
                repo_url.add(upstream.get("repository_url"))

        if len(repo_url) > 1:
            failures.append(("inconsistent_repo_urls", metadata_file.parent.relative_to(gf_repo)))
            continue

        if len(archive_url) > 1:
            failures.append(("inconsistent_archive_urls", metadata_file.parent.relative_to(gf_repo)))
            continue

        if not repo_url and not archive_url:
            failures.append(("no_source", metadata_file.parent.relative_to(gf_repo)))
            continue

        if not repo_url:
            failures.append(("archive_only", metadata_file.parent.relative_to(gf_repo)))
            continue

        repo_url = next(iter(repo_url))

        if repo_url in _DENY_REPO_URLS:
            failures.append(("denylisted_repo_url", metadata_file.parent.relative_to(gf_repo)))
            continue

        clone_dir = repo_dir(upstream_file)

        # some very slow repos are used repeatedly, e.g. https://github.com/googlefonts/plex
        if repo_url in local_repos:
            if clone_dir.is_dir():
                shutil.rmtree(clone_dir)
            print("copy", local_repos[repo_url], "to", clone_dir)
            shutil.copytree(local_repos[repo_url], clone_dir, ignore=ignore_venv)
            local_copies += 1
        else:
            if (clone_dir / ".git").is_dir():
                shell_cmd = ("git", "-C", clone_dir, "pull")
            else:
                # do a faster shallow clone; `git fetch --unshallow` to get full repo
                shell_cmd = ("git", "clone", "--depth=1", repo_url, clone_dir)

            if FLAGS.pull_existing or (shell_cmd[0], shell_cmd[-1]) != ("git", "pull"):
                print(" ".join(str(c) for c in shell_cmd))
                cmd_result = subprocess.run(shell_cmd, capture_output=True, shell=(shell_cmd[0] == "cp"))
                if cmd_result.returncode != 0:
                    failures.append(
                        (
                            "cmd_fail",
                            upstream_file.relative_to(gf_repo),
                            " ".join(str(c) for c in shell_cmd),
                            "\n" + cmd_result.stdout.decode("utf-8"),
                        )
                    )

        if repo_url not in local_repos:
            local_repos[repo_url] = clone_dir

    count_by_type = defaultdict(int)
    for failure in failures:
        count_by_type[failure[0]] += 1
        with open(failure_file(failure[0]), "a") as f:
            f.write(" ".join(str(f) for f in failure[1:]))
            f.write("\n")

    print(f"Acquired sources for {len(metadata_files) - len(failures)}/{len(metadata_files)} METADATA.pb files")
    print(f"{local_copies} use the same repository and were copied locally")
    print("failures:")
    for fail_type, count in sorted(count_by_type.items()):
        print(
            f"{count}/{len(metadata_files)} {fail_type} ({failure_file(fail_type).relative_to(Path(__file__).parent)})"
        )

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    app.run(main)
