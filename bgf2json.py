# bgf2json.py — BGF (header + gzip/zlib/raw Smile) → JSON (pure Python, no Java)

import sys, json, gzip, zlib, struct
from pathlib import Path

SMILE_MAGIC = b':)\n'
FEATURE_SHARED_NAMES = 0x01
FEATURE_SHARED_VALUES = 0x02
FEATURE_RAW_BINARY = 0x04


def decompress_if_needed(b: bytes) -> bytes:
    if b.startswith(b'\x1f\x8b'):
        return gzip.decompress(b)
    if b.startswith((b'\x78\x01', b'\x78\x9c', b'\x78\xda')):
        return zlib.decompress(b)
    return b


def read_bgf(path: Path):
    """Return (header_dict, smile_bytes) from a BGBlitz .bgf file."""
    with path.open('rb') as f:
        header = json.loads(f.readline().decode('utf-8'))
        tail = f.read()
    payload = decompress_if_needed(tail)
    if not payload.startswith(SMILE_MAGIC):
        raise ValueError("Payload is not Smile (missing b':)\\n' magic).")
    return header, payload


class _SmileDecoder:
    def __init__(self, data: bytes):
        assert data[:3] == SMILE_MAGIC
        self.buf = data
        self.pos = 4
        self.features = data[3]
        self.shared_names = bool(self.features & FEATURE_SHARED_NAMES)
        self.name_table: list[str] = []

    # ── low-level I/O ───────────────────────────────────────────────────────

    def _rb(self) -> int:
        if self.pos >= len(self.buf):
            raise EOFError("Unexpected end of Smile stream")
        b = self.buf[self.pos]
        self.pos += 1
        return b

    def _read(self, n: int) -> bytes:
        end = self.pos + n
        if end > len(self.buf):
            raise EOFError(f"Need {n} bytes at pos {self.pos}")
        chunk = self.buf[self.pos:end]
        self.pos = end
        return chunk

    # ── VInt (ZigZag, big-endian 6-bit groups, bit-7 = stop) ────────────────

    @staticmethod
    def _zigzag(n: int) -> int:
        return (n >> 1) ^ -(n & 1)

    def _vint(self) -> int:
        acc = 0
        while True:
            b = self._rb()
            acc = (acc << 6) | (b & 0x3F)
            if b & 0x80:
                return self._zigzag(acc)

    # ── 10-byte "safe" double ───────────────────────────────────────────────

    def _safe_double(self) -> float:
        r = self._read(10)
        bits = (
            (r[0] & 0x7F) << 57 | (r[1] & 0x7F) << 50 | (r[2] & 0x7F) << 43 |
            (r[3] & 0x7F) << 36 | (r[4] & 0x7F) << 29 | (r[5] & 0x7F) << 22 |
            (r[6] & 0x7F) << 15 | (r[7] & 0x7F) <<  8 | (r[8] & 0x7F) <<  1 |
            ((r[9] & 0x7F) >> 6)
        )
        return struct.unpack('>d', struct.pack('>Q', bits))[0]

    # ── key ─────────────────────────────────────────────────────────────────

    def _read_key(self) -> str | None:
        b = self._rb()

        if b in (0xFB, 0xFF):          # end-object / end-of-content
            return None

        # Short shared back-reference: 0x40–0x7F → index 0–63
        if 0x40 <= b <= 0x7F:
            return self.name_table[b - 0x40]

        # Raw inline key: 0x80–0xBF → length 1–64
        if 0x80 <= b <= 0xBF:
            key = self._read((b & 0x3F) + 1).decode('utf-8', errors='replace')
            if self.shared_names:
                self.name_table.append(key)
            return key

        # Long shared back-reference: 0x30 + next-byte → index = next-byte (for indices ≥ 64)
        if b == 0x30:
            return self.name_table[self._rb()]

        raise ValueError(f"Unknown Smile key token 0x{b:02x} at pos {self.pos - 1}")

    # ── value ────────────────────────────────────────────────────────────────

    _END_ARRAY  = object()
    _END_OBJECT = object()

    def _read_value(self):
        b = self._rb()

        if b == 0xFA: return self._parse_object()
        if b == 0xF8: return self._parse_array()
        if b == 0xF9: return self._END_ARRAY
        if b == 0xFB: return self._END_OBJECT
        if b == 0xFF: return self._END_ARRAY   # end-of-content

        if b == 0x20: return ''
        if b == 0x21: return None
        if b == 0x22: return False
        if b == 0x23: return True
        if b == 0x24: return self._vint()          # VInt32
        if b == 0x25: return self._vint()          # VLong64
        if b == 0x28: return struct.unpack('>f', self._read(4))[0]   # float32
        if b == 0x29: return self._safe_double()                      # float64 (10-byte safe)

        # Short ASCII string: 0x40–0x5F → length 1–32
        if 0x40 <= b <= 0x5F:
            return self._read(b - 0x3F).decode('ascii')

        # Short Unicode string: 0x60–0x7F → length 2–33
        if 0x60 <= b <= 0x7F:
            return self._read(b - 0x5E).decode('utf-8', errors='replace')

        # Small integer: 0xC0–0xDF → ZigZag(b - 0xC0)
        if 0xC0 <= b <= 0xDF:
            return self._zigzag(b - 0xC0)

        # Long string (ASCII 0xE0–0xE3, Unicode 0xE4–0xE7): terminated by 0xFC
        if 0xE0 <= b <= 0xEF:
            parts = bytearray()
            while True:
                ch = self._rb()
                if ch == 0xFC:
                    break
                parts.append(ch)
            return parts.decode('utf-8' if (b & 0x04) else 'ascii', errors='replace')

        raise ValueError(f"Unknown Smile value token 0x{b:02x} at pos {self.pos - 1}")

    # ── containers ──────────────────────────────────────────────────────────

    def _parse_object(self) -> dict:
        obj: dict = {}
        while True:
            key = self._read_key()
            if key is None:
                return obj
            obj[key] = self._read_value()

    def _parse_array(self) -> list:
        arr: list = []
        while True:
            val = self._read_value()
            if val is self._END_ARRAY:
                return arr
            arr.append(val)

    # ── entry point ──────────────────────────────────────────────────────────

    def decode(self):
        b = self._rb()
        if b == 0xFA:
            return self._parse_object()
        if b == 0xF8:
            return self._parse_array()
        self.pos -= 1
        return self._read_value()


def decode_smile(smile_bytes: bytes):
    """Decode a Smile-encoded payload (as emitted by BGBlitz) to a Python object."""
    return _SmileDecoder(smile_bytes).decode()


def decode_bgf(path: Path):
    """Read a .bgf file and return the decoded data as a Python object."""
    header, smile_bytes = read_bgf(path)
    return decode_smile(smile_bytes)


def main():
    if len(sys.argv) < 2:
        print("Usage: python bgf2json.py input.bgf [output.json]", file=sys.stderr)
        sys.exit(1)

    infile = Path(sys.argv[1])
    outfile = Path(sys.argv[2]) if len(sys.argv) > 2 else infile.with_suffix('.json')

    header, smile_bytes = read_bgf(infile)
    data = decode_smile(smile_bytes)

    json_text = json.dumps(data, indent=2, ensure_ascii=False)
    outfile.write_text(json_text, encoding='utf-8')
    print(f"Wrote {outfile}", file=sys.stderr)


if __name__ == '__main__':
    main()
