"""Strict host decoder for CheckpointCaptureTransport's 64-byte frames.

This is a transport codec, not an FPGA driver or a claim of complete state.
Generated manifest/bank bindings must be independently audited for the image.
Do not publish a canonical image until the entire stream and host owners pass.
"""

from .banked import encode_banked, validate_binding
from .codec import natural, require
from .semantic import manifest_hash

MAGIC = int.from_bytes(b"FSMCKPT1", "little")
FRAME_BYTES = 64


def crc32c(data: bytes, previous: int = 0xffffffff) -> int:
    """Uncomplemented reflected CRC32C; complement once at stream end."""
    value = previous
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0x82f63b78 if value & 1 else 0)
    return value


def field(frame: int, offset: int, width: int) -> int:
    return (frame >> offset) & ((1 << width) - 1)


def decode_frames(raw: bytes, manifest: dict, binding: dict, expected_cycle: int) -> list[dict]:
    """Return ordered banked words only after complete integrity validation.

    Every expected word, selector, width, cycle, ordinal, reserved bit and the
    final checksum is checked before any state is returned to the caller.
    This implementation is Level-2 only; Level-1 has independent ownership.
    """
    validate_binding(manifest, binding)
    natural(expected_cycle)
    require(expected_cycle < 1 << 64, "target cycle exceeds hardware width")
    require(type(raw) is bytes, "transport requires bytes")
    count = sum(e["depth"] for e in binding["state"])
    require(len(binding["state"]) <= 65535 and count < 1 << 64, "transport inventory too large")
    require(len(raw) == (count + 2) * FRAME_BYTES, "truncated or extra transport frames")
    checksum = crc32c(raw[:-FRAME_BYTES]) ^ 0xffffffff
    header = int.from_bytes(raw[:FRAME_BYTES], "little")
    trailer = int.from_bytes(raw[-FRAME_BYTES:], "little")
    require(field(header, 80, 16) == 1 and field(header, 160, 64) == 0 and
            field(header, 224, 32) == len(binding["state"]) and
            field(header, 256, 256) == int(manifest_hash(manifest), 16),
            "incompatible transport manifest/header")
    require(field(trailer, 80, 16) == 3 and field(trailer, 160, 64) == count and
            field(trailer, 224, 32) == checksum and trailer >> 256 == 0,
            "transport trailer/checksum mismatch")
    beats = []
    ordinal = 0
    # Iterate the independently expected shape, never untrusted on-wire counts.
    for index, entry in enumerate(binding["state"]):
        for address in range(entry["depth"]):
            start = (ordinal + 1) * FRAME_BYTES
            frame = int.from_bytes(raw[start:start + FRAME_BYTES], "little")
            require(field(frame, 80, 16) == 2 and field(frame, 160, 64) == ordinal and
                    field(frame, 224, 32) == index and field(frame, 256, 32) == address and
                    field(frame, 288, 16) == entry["width"] and
                    field(frame, 304, 8) == entry["bank"] and
                    field(frame, 312, 16) == entry["slot"], "transport state order/selector mismatch")
            require(field(frame, 328, 8) == 0 and frame >> 400 == 0, "transport error/reserved bits")
            data = field(frame, 336, 64)
            require(data < 1 << entry["width"], "noncanonical transport data")
            beats.append(dict(entry=index, address=address, width=entry["width"], data=data,
                              error=0, last=int(ordinal == count - 1)))
            ordinal += 1
    # Include header and trailer in the independent common-field validation.
    for offset in range(0, len(raw), FRAME_BYTES):
        frame = int.from_bytes(raw[offset:offset + FRAME_BYTES], "little")
        require(field(frame, 0, 64) == MAGIC and field(frame, 64, 16) == 1 and
                field(frame, 96, 64) == expected_cycle, "transport magic/version/target cut mismatch")
    return beats


def encode_transport_semantic(raw: bytes, manifest: dict, binding: dict,
                              configuration: str, expected_cycle: int) -> bytes:
    return encode_banked(manifest, configuration, expected_cycle,
                         decode_frames(raw, manifest, binding, expected_cycle))
