"""Fetch the Noto sources.

Simon's https://gist.github.com/simoncozens/173c9d35e28c1c6e43e58405d0c4695b
modified slightly.

Ideally fetch_source.py would be all we need but at time of writing it helps
a great deal to rely on http://notofonts.github.io/noto.json file.
"""
import json
import urllib.request
import subprocess
import psutil
import tempfile
import os
import glob
import yaml
import re
from fontTools import designspaceLib
from glyphsLib import GSFont
from ufoLib2 import Font
import argparse

parser = argparse.ArgumentParser(description="Build all of Noto and time it.")
parser.add_argument(
    "--statics",
    action="store_true",
    help="build statics (default: build variable fonts)",
)

args = parser.parse_args()

with urllib.request.urlopen("http://notofonts.github.io/noto.json") as url:
    noto = json.loads(url.read().decode())

results = []


def get_font_stats(font_path):
    if font_path.endswith(".designspace"):
        ds = designspaceLib.DesignSpaceDocument.fromfile(font_path)
        glyphs = len(Font.open(ds.sources[0].path))
        masters = len(ds.sources)
        instances = len(ds.instances)
    elif font_path.endswith(".glyphs"):
        gs = GSFont(font_path)
        glyphs = len(gs.glyphs)
        masters = len(gs.masters)
        instances = len(gs.instances)
    return (masters, instances, glyphs)


def build_one_target(name, path):
    os.chdir(os.path.dirname(path))
    config = os.path.basename(path)
    config = yaml.load(open(config), Loader=yaml.FullLoader)
    sources = config["sources"]
    masters, instances, glyphs = get_font_stats(sources[0])

    # Just build the first
    fontmake_args = ["fontmake", "-o"]
    if args.statics:
        fontmake_args += ["ttf", "-i"]
    else:
        fontmake_args += ["variable"]

    time_args = (["/usr/bin/time", "-p", "-o", "/tmp/time"]
        + fontmake_args
        + [
            "--",
            sources[0],
        ]
    )
    print(f"  " + " ".join(time_args))
    rc = subprocess.run(time_args, capture_output=True)

    rv = { 
        "name": name,
        "real": 0.,
        "user": 0.,
        "sys": 0.,
        "format": os.path.splitext(sources[0])[-1][1:],
        "masters": masters,
        "instances": instances,
        "glyphs": glyphs,
    }

    if rc.returncode == 0:
        with open("/tmp/time") as f:
            # the last 3 should be real #.##, user #.##, sys #.##
            timings = [l.strip() for l in f.readlines()[-3:]]            
            for time in timings:
                time = time.split(" ")
                assert len(time) == 2, time
                rv[time[0]] = float(time[1])
    else:
        print(" ".join(fontmake_args), "FAILED", rc.stderr)

    rv["succeeded"] = rc.returncode == 0

    return rv


if os.path.exists("state.json"):
    state = json.load(open("state.json"))
else:
    state = {}


for repo, v in noto.items():
    url = v["repo_url"]
    print(f"{repo} {url}")

    repo_dir = repo.lower()

    git_cmd = ["git"]
    git_args = {"capture_output": True, "check": True}
    if os.path.isdir(repo_dir):
        pull_cmd = ["git", "pull", repo_dir]
        git_cmd += ["pull"]
        git_args["cwd"] = repo_dir
    else:
        git_cmd += ["clone", "--depth", "1", url, repo_dir]

    print(f"  " + " ".join(git_cmd), git_args)
    subprocess.run(git_cmd, **git_args)

    for font in glob.glob(repo_dir + "/sources/config*.yaml"):
        name = os.path.basename(font).replace("config-", "").replace(".yaml", "")
        if name in state:
            print(f"  {name} already built")
            continue
        before = os.getcwd()
        rv = build_one_target(name, font)
        os.chdir(before)

        results.append(rv)
        state[name] = rv
        json.dump(state, open("state.json", "w"), indent=4)

print(results)
