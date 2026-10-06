"""Create cleaned copies of files. The original file is never modified."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import piexif
from pypdf import PdfWriter

from . import containers, jpeg
from .core import Finding, UnsupportedFormatError, detect_format, scan_file
from .scanners.pdf import open_pdf
from .scanners.image import PNG_METADATA_CHUNKS, WEBP_METADATA_CHUNKS

_ORIENTATION_TAG = piexif.ImageIFD.Orientation


@dataclass
class CleanResult:
    """Outcome of cleaning one file."""

    source: Path
    output: Path
    before: list[Finding]
    after: list[Finding]


def output_path(src: Path, out_dir: Path | None = None) -> Path:
    """Pick a free path like 'photo_clean.jpg'; never an existing file."""
    folder = out_dir if out_dir is not None else src.parent
    candidate = folder / f"{src.stem}_clean{src.suffix}"
    counter = 2
    while candidate.exists():
        candidate = folder / f"{src.stem}_clean_{counter}{src.suffix}"
        counter += 1
    return candidate


def _clean_jpeg(src: Path, dst: Path) -> None:
    """Drop all metadata segments without re-compressing the picture."""
    segments, tail = jpeg.parse_jpeg(src.read_bytes())

    orientation = 1
    for seg in segments:
        if jpeg.is_exif(seg):
            try:
                orientation = piexif.load(seg.data)["0th"].get(_ORIENTATION_TAG, 1)
            except Exception:
                pass

    kept = [seg for seg in segments if not jpeg.is_metadata(seg)]
    if orientation != 1:
        # Keep only the rotation hint, otherwise the photo would show up sideways.
        minimal = piexif.dump({"0th": {_ORIENTATION_TAG: orientation}})
        position = 0
        while position < len(kept) and kept[position].marker == jpeg.APP0:
            position += 1
        kept.insert(position, jpeg.Segment(jpeg.APP1, minimal))
    dst.write_bytes(jpeg.build_jpeg(kept, tail))


def _clean_png(src: Path, dst: Path) -> None:
    """Drop text, EXIF and timestamp chunks; the pixel data is copied untouched."""
    chunks = containers.parse_png(src.read_bytes())
    dst.write_bytes(containers.build_png(
        [c for c in chunks if c.type not in PNG_METADATA_CHUNKS]))


_VP8X_EXIF_FLAG = 0x08
_VP8X_XMP_FLAG = 0x04


def _clean_webp(src: Path, dst: Path) -> None:
    """Drop EXIF and XMP chunks (and the matching VP8X flags); no re-encoding."""
    chunks = [c for c in containers.parse_webp(src.read_bytes())
              if c.fourcc not in WEBP_METADATA_CHUNKS]
    for chunk in chunks:
        if chunk.fourcc == b"VP8X" and chunk.body:
            flags = chunk.body[0] & ~(_VP8X_EXIF_FLAG | _VP8X_XMP_FLAG)
            chunk.body = bytes([flags]) + chunk.body[1:]
    dst.write_bytes(containers.build_webp(chunks))


HEIC_QUALITY = 95


def _clean_heic(src: Path, dst: Path) -> None:
    """Re-save the picture without metadata. This re-encodes it (HEIC is lossy)."""
    import pillow_heif
    from PIL import Image

    heif = pillow_heif.open_heif(str(src))
    image = heif.to_pillow()
    icc_profile = image.info.get("icc_profile")
    # Rebuild the image from raw pixels so no metadata can be carried over.
    # pillow-heif already applied the rotation while decoding.
    plain = Image.frombytes(image.mode, image.size, image.tobytes())
    pillow_heif.from_pillow(plain).save(
        str(dst), quality=HEIC_QUALITY, exif=None, xmp=None, icc_profile=icc_profile)


# Keys that can hold metadata on the catalog or on single pages.
_PDF_ROOT_KEYS = ("/Metadata", "/PieceInfo")
_PDF_PAGE_KEYS = ("/Metadata", "/PieceInfo", "/LastModified")


def _clean_pdf(src: Path, dst: Path) -> None:
    """Write a fresh PDF without info dictionary, XMP or document ID.

    Writing a new file also drops old revisions left over from incremental saves.
    """
    writer = PdfWriter(clone_from=open_pdf(src))
    writer.metadata = None  # removes the info dictionary and the trailer /ID
    for key in _PDF_ROOT_KEYS:
        writer._root_object.pop(key, None)
    for page in writer.pages:
        for key in _PDF_PAGE_KEYS:
            page.pop(key, None)
    with open(dst, "wb") as fh:
        writer.write(fh)


_CLEANERS = {"jpeg": _clean_jpeg, "png": _clean_png, "webp": _clean_webp, "heic": _clean_heic, "pdf": _clean_pdf}


def clean_file(src: str | Path, out_dir: str | Path | None = None) -> CleanResult:
    """Write a cleaned copy of `src` and scan it again.

    The copy is named '<name>_clean<ext>' and placed next to the original
    (or in `out_dir`). Raises UnsupportedFormatError for unknown formats.
    """
    src = Path(src)
    fmt = detect_format(src)
    if fmt not in _CLEANERS:
        raise UnsupportedFormatError(f"{src.name}: cleaning {fmt} is not supported yet")

    folder = Path(out_dir) if out_dir is not None else None
    if folder is not None:
        folder.mkdir(parents=True, exist_ok=True)
    dst = output_path(src, folder)
    if dst.resolve() == src.resolve():  # cannot happen with the naming scheme; be safe
        raise RuntimeError("refusing to overwrite the original file")

    before = scan_file(src)
    _CLEANERS[fmt](src, dst)
    return CleanResult(source=src, output=dst, before=before, after=scan_file(dst))
