from absl import app
from collections import defaultdict
import gf_upstream
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse
import yaml


_DENY_REPO_URLS = {
    "https://github.com/TypeNetwork/Alegreya",  # prompts for auth
    "https://github.com/googlefonts/glory",  # prompts for auth
}


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


def main(argv):
    for stale_file in failure_dir().iterdir():
        stale_file.unlink()

    gf_repo = gf_upstream.repo()
    upstream_files = gf_upstream.ls()
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
                if maybe_archive is not None and maybe_archive.startswith(
                    "https://github.com"
                ):
                    failures.append(
                        (
                            "github_archive_no_repo_url",
                            upstream_file.relative_to(gf_repo),
                        )
                    )
                    repo_path = "/".join(
                        urlparse(upstream["archive"]).path.split("/")[:2]
                    )
                    upstream["repository_url"] = "https://github.com/" + repo_path
                else:
                    failures.append(("no_repo_url", upstream_file.relative_to(gf_repo)))
                    continue

        if upstream.get("repository_url", "") in _DENY_REPO_URLS:
            failures.append(("denylisted_repo_url", upstream_file.relative_to(gf_repo)))
            continue

        clone_dir = repo_dir(upstream_file)
        if (clone_dir / ".git").is_dir():
            git_cmd = ("git", "-C", clone_dir, "pull")
        else:
            # do a faster shallow clone; `git fetch --unshallow` to get full repo
            git_cmd = ("git", "clone", "--depth=1", upstream["repository_url"], clone_dir)

        print(" ".join(str(c) for c in git_cmd))
        git_result = subprocess.run(git_cmd, capture_output=True)
        if git_result.returncode != 0:
            failures.append(
                (
                    "git_fail",
                    upstream_file.relative_to(gf_repo),
                    " ".join(str(c) for c in git_cmd),
                    "\n" + git_result.stdout.decode("utf-8"),
                )
            )

    count_by_type = defaultdict(int)
    for failure in failures:
        count_by_type[failure[0]] += 1
        with open(failure_file(failure[0]), "a") as f:
            f.write(" ".join(str(f) for f in failure[1:]))
            f.write("\n")

    print(f"{len(upstream_files)} upstream.yaml files")
    for fail_type, count in sorted(count_by_type.items()):
        print(
            f"{count}/{len(upstream_files)} {fail_type} ({failure_file(fail_type).relative_to(Path(__file__).parent)})"
        )

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    app.run(main)
