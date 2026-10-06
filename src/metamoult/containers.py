"""Chunk readers/writers for PNG and WebP (RIFF) so we can edit them losslessly."""

from __future__ import annotations

import struct
from dataclasses import dataclass

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass
class PngChunk:
    type: bytes
    body: bytes
    raw: bytes  # the complete chunk (length + type + body + CRC), copied verbatim


def parse_png(data: bytes) -> list[PngChunk]:
    """Split a PNG into chunks, up to and including IEND. Data after IEND is ignored."""
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG file")
    chunks: list[PngChunk] = []
    pos = len(PNG_SIGNATURE)
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        end = pos + 12 + length
        if end > len(data):
            raise ValueError("corrupt PNG: chunk exceeds file size")
        chunk_type = data[pos + 4:pos + 8]
        chunks.append(PngChunk(chunk_type, data[pos + 8:pos + 8 + length], data[pos:end]))
        pos = end
        if chunk_type == b"IEND":
            return chunks
    raise ValueError("corrupt PNG: missing IEND chunk")


def build_png(chunks: list[PngChunk]) -> bytes:
    return PNG_SIGNATURE + b"".join(c.raw for c in chunks)


@dataclass
class RiffChunk:
    fourcc: bytes
    body: bytes


def parse_webp(data: bytes) -> list[RiffChunk]:
    """Split a WebP file into its RIFF chunks."""
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("not a WebP file")
    chunks: list[RiffChunk] = []
    pos = 12
    end = min(len(data), 8 + struct.unpack("<I", data[4:8])[0])
    while pos + 8 <= end:
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if pos + 8 + size > len(data):
            raise ValueError("corrupt WebP: chunk exceeds file size")
        chunks.append(RiffChunk(data[pos:pos + 4], data[pos + 8:pos + 8 + size]))
        pos += 8 + size + (size % 2)  # chunks are padded to an even size
    return chunks


def build_webp(chunks: list[RiffChunk]) -> bytes:
    body = b"WEBP"
    for chunk in chunks:
        body += chunk.fourcc + struct.pack("<I", len(chunk.body)) + chunk.body
        if len(chunk.body) % 2:
            body += b"\x00"
    return b"RIFF" + struct.pack("<I", len(body)) + body
