What if you wanted ALL the sources - not the binaries - for Google Fonts?

```shell
# setup a python3 virtual environment

pip install -r requirements.txt

# slow, sequentially fetches or updates lots of repos
python fetch_source.py

# find designspaces for VFs with low glyph counts, good for quick compile tests
python find_source.py --vf_only | sort | head -64
```