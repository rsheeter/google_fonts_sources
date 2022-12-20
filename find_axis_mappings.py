"""Search all GF sources for 'Axis Mappings' custom parameter."""

import subprocess
from pprint import pprint
from pathlib import Path
import openstep_plist

CURRENT_DIR = Path(__file__).parent
SOURCES = CURRENT_DIR / "sources"


def group_sources_by_repo_url():
    result = {}
    for path in SOURCES.iterdir():
        if not path.is_dir() or path.name == "failures":
            continue
        assert path.name in ("apache", "ofl", "ufl"), (
            "Unexpected license subdir: %s" % path
        )
        for source in path.iterdir():
            if not (source / ".git").is_dir():
                continue
            git_result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                check=True,
                cwd=source,
            )
            repo_url = git_result.stdout.decode("utf-8")
            result.setdefault(repo_url, []).append(source)
    return result


def main():
    sources_by_repo_url = group_sources_by_repo_url()
    print("Total unique repo urls:", len(sources_by_repo_url))
    glyphs_file_count = 0
    all_axis_mappings = {}
    print("Searching for 'Axis Mappings' custom parameter... may take a while")
    for url, sources in sources_by_repo_url.items():
        source = sources[0]
        assert source.is_dir()
        for glyphs_file in source.rglob("*.glyphs"):
            glyphs_file_count += 1
            rel_path = glyphs_file.relative_to(CURRENT_DIR)
            # print("Parsing", rel_path)
            try:
                font = openstep_plist.load(glyphs_file.open("r", encoding="utf-8"))
            except Exception as e:
                print("Error parsing", rel_path, str(e)[:100])
                continue
            # get 'Axis Mappings' custom parameter
            custom_parameters = font.get("customParameters", [])
            raw_axis_mappings = next(
                (p["value"] for p in custom_parameters if p["name"] == "Axis Mappings"),
                None,
            )
            if raw_axis_mappings:
                axis_mappings = {
                    tag: {float(k): float(v) for k, v in raw_axis_mappings[tag].items()}
                    for tag in raw_axis_mappings
                }
                print(rel_path)
                pprint(axis_mappings)
                print()
                all_axis_mappings[rel_path] = axis_mappings
    print("Number of .glyphs files:", glyphs_file_count)
    print("Number of axis mappings:", len(all_axis_mappings))


if __name__ == "__main__":
    main()
