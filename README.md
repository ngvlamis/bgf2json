# bgf2json

Convert [BGBlitz](https://www.bgblitz.com/) `.bgf` match files to JSON. Pure Python, no Java required.

## Install

```bash
pip install git+https://github.com/ngvlamis/bgf2json.git
```

Or just copy `bgf2json.py` — it has no dependencies beyond the standard library.

## CLI

```bash
python bgf2json.py match.bgf            # writes match.json in the same folder
python bgf2json.py match.bgf out.json   # writes to a specific file
```

After `pip install`, the `bgf2json` command is also available:

```bash
bgf2json match.bgf
```

## Library

```python
from pathlib import Path
from bgf2json import decode_bgf

data = decode_bgf(Path("match.bgf"))
# data is a plain Python dict/list
```

Lower-level access if you need the header metadata too:

```python
from bgf2json import read_bgf, decode_smile

header, smile_bytes = read_bgf(Path("match.bgf"))
data = decode_smile(smile_bytes)
```

## BGF format

A `.bgf` file is a UTF-8 JSON header line followed by a gzip- or zlib-compressed [Smile](https://github.com/FasterXML/smile-format-specification) binary JSON payload. This library handles the decompression and Smile decoding automatically.

## Limitations

The Smile decoder covers the subset of the format emitted by BGBlitz. It is not a general-purpose Smile decoder and may not handle all tokens defined in the full Smile specification.

## License

MIT
