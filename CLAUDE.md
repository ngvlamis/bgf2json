# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the converter
python bgf2json.py match.bgf            # writes match.json in the same folder
python bgf2json.py match.bgf out.json   # explicit output path

# Install in editable mode (makes `bgf2json` CLI available)
uv pip install -e .

# No test suite exists yet
```

## Architecture

The entire library is a single file: `bgf2json.py`. No external dependencies.

**BGF file format:** A UTF-8 JSON header line followed by a gzip- or zlib-compressed [Smile](https://github.com/FasterXML/smile-format-specification) binary JSON payload.

**Decode pipeline:**

1. `read_bgf(path)` — reads the header line as JSON, reads the binary tail, decompresses it (gzip/zlib/raw passthrough), returns `(header_dict, smile_bytes)`.
2. `_SmileDecoder` — hand-written recursive-descent Smile decoder. Covers only the subset BGBlitz emits: VInt/VLong (ZigZag-encoded), 10-byte "safe" double, short/long ASCII and Unicode strings, small integers, booleans, null, arrays, and objects with optional shared-name back-references. Not a general-purpose Smile decoder.
3. `decode_smile(smile_bytes)` — public entry point into `_SmileDecoder`.
4. `decode_bgf(path)` — convenience wrapper combining steps 1–3; returns a plain Python dict/list.
5. `main()` — CLI entry point registered as the `bgf2json` console script.

When extending the Smile decoder, the token byte ranges are: `0x40–0x5F` short ASCII value, `0x60–0x7F` short Unicode value, `0xC0–0xDF` small integer, `0xE0–0xEF` long string (terminated by `0xFC`), `0x80–0xBF` inline key, `0x40–0x7F` short shared-name back-reference, `0x30` long shared-name back-reference.
