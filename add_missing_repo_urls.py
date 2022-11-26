"""Adds a repository_url if there is only an archive pointing at GH.

Context https://github.com/google/fonts/issues/4773#issuecomment-1328101047.
"""
from absl import app
import gf_upstream
from pathlib import Path
import sys
from urllib.parse import urlparse
import yaml


def main(argv):
    num_fixed = 0
    upstream_files = gf_upstream.ls()
    for upstream_file in upstream_files:
        with open(upstream_file) as f:
            try:
                upstream = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print("Failed to load", upstream_file, e)
                continue

        maybe_archive = upstream.get("archive", "")
        if maybe_archive is not None and maybe_archive.startswith("https://github.com"):
            repo_path = "/".join(urlparse(upstream["archive"]).path.split("/")[:3])
            expected_repo_url = "https://github.com" + repo_path

            actual_repo_url = upstream.get("repository_url", "")
            if "repository_url" not in upstream:
                # writing with yaml.dump purturbs other fields
                with open(upstream_file, "a") as f:
                    f.write(f"repository_url: {expected_repo_url}\n")
                num_fixed += 1
            elif expected_repo_url != actual_repo_url:
                print(f"{upstream_file} has unexpected repo url {actual_repo_url}")
    print(f"{num_fixed} repository_url's added")


if __name__ == "__main__":
    app.run(main)
