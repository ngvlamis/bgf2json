# bgf2json

Convert [BGBlitz](https://www.bgblitz.com/) `.bgf` match files to JSON. Pure Python, no Java required.

## Install

```bash
pip install git+https://github.com/ngvlamis/bgf2json.git
```

Or just copy `bgf2json.py` — it has no dependencies beyond the standard library.

## CLI

```bash
python bgf2json.py match.bgf            # prints JSON to stdout
python bgf2json.py match.bgf out.json   # writes to file
```

After `pip install`, the `bgf2json` command is also available:

```bash
bgf2json match.bgf out.json
```

## Library

```python
from pathlib import Path
from bgf2json import read_bgf, decode_smile

header, smile_bytes = read_bgf(Path("match.bgf"))
data = decode_smile(smile_bytes)
# data is now a plain Python dict/list
```

`read_bgf` returns a `(header, smile_bytes)` tuple where `header` is the parsed JSON metadata dict and `smile_bytes` is the raw Smile payload. `decode_smile` converts that payload to a Python object.

## BGF format

A `.bgf` file is a UTF-8 JSON header line followed by a gzip- or zlib-compressed [Smile](https://github.com/FasterXML/smile-format-specification) binary JSON payload. This library handles the decompression and Smile decoding automatically.

## Limitations

The Smile decoder covers the subset of the format emitted by BGBlitz. It is not a general-purpose Smile decoder and may not handle all tokens defined in the full Smile specification.

## License

MIT
