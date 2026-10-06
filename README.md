<div align="center">

<img src="logo.svg" alt="metamoult logo" width="140">

# metamoult

**See and remove hidden metadata from photos, PDFs and Office files. Offline.**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

</div>

Files carry more than you can see: where a photo was taken, which camera (and its
serial number) took it, who wrote a document, and when. **metamoult** shows you
these hidden details, rates how risky each one is in plain language, and can
write a cleaned copy of the file.

*"Moult" means to shed old feathers or skin. metamoult sheds the metadata from
your files.* ("moult" is the British spelling; in American English it is
**"molt"**. Search for either: metadata remover, EXIF remover, strip metadata.)

## Features

- **`scan`** lists every metadata field found, with a traffic-light risk level
  (high / medium / low) and a short explanation anyone can understand.
- **`clean`** writes a cleaned **copy** (`name_clean.ext`) and scans it again so
  you can see the result. The original file is **never** overwritten.
- **Offline.** No network access, no telemetry. GPS coordinates are only shown
  as text, never looked up on a map.
- Command line and a small desktop window (Tkinter).

| Format | Scan | Clean |
| --- | --- | --- |
| JPEG | EXIF, GPS, XMP, IPTC, comments | Lossless (picture data is not re-compressed) |
| PNG | text, EXIF, XMP, timestamp | Lossless |
| WebP | EXIF, XMP | Lossless |
| HEIC | EXIF, XMP | Picture is re-saved (re-encoded, quality 95) |
| PDF | info dictionary, XMP, document ID | New file is written |
| DOCX / XLSX / PPTX | document properties, thumbnail, author names in comments and revisions | Properties blanked, thumbnail removed, names neutralised |

### Risk levels

| Level | Examples |
| --- | --- |
| 🔴 **high** | GPS coordinates, serial numbers, author / owner / copyright names |
| 🟡 **medium** | device make and model, date and time, software used, free-text comments, thumbnails |
| 🟢 **low** | other technical fields (exposure, resolution, ...) |

## Quickstart

You need Python 3.10 or newer.

```powershell
git clone <this repository>
cd metamoult
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install .                   # add ".[gui]" for drag-and-drop in the window

metamoult scan holiday.jpg
metamoult clean holiday.jpg                 # writes holiday_clean.jpg next to it
metamoult clean *.jpg --out cleaned         # writes all copies into ./cleaned
metamoult gui                               # opens the desktop window
```

Pre-built programs for Windows, macOS and Linux are attached to each tagged
release (no Python needed).

### Example output

```text
holiday.jpg [jpeg] - 11 findings (3 high, 6 medium, 2 low)
  HIGH   IFD0:Artist            Jane Example
                                This contains the name of a person (author, creator or rights holder).
  HIGH   EXIF:BodySerialNumber  SN123456
                                A serial number can link this file to your specific device.
  HIGH   GPS:Position           48.858400, -2.294444
                                This reveals where the file was created (GPS location).
  MEDIUM IFD0:Make              FakeCam
                                This reveals which device or lens was used.
  MEDIUM EXIF:DateTimeOriginal  2020:01:02 03:04:05
                                This reveals when the file was created or changed.
  ...

holiday.jpg [jpeg] - 11 findings (3 high, 6 medium, 2 low)
  Saved cleaned copy: holiday_clean.jpg
  Re-scan of the copy: no metadata found
```

(The values above are invented test data.)

## Limits - please read

metamoult is honest about what it does **not** do:

- It removes **metadata, not the visible content.** Faces, house numbers,
  license plates, text in the picture, or a recognisable view stay in the image.
- It has **not been forensically verified.** It cannot promise that nothing
  identifying is left, for example hidden watermarks, sensor noise patterns or
  data hidden on purpose. For high-stakes cases, re-scan the result and use
  additional tools.
- **File names and your own text are untouched.** A file called
  `Jane_passport.jpg` stays that way (plus `_clean`), and text inside documents
  is not edited.
- **Office files:** only the document properties, the preview thumbnail and
  author names in comments and tracked changes are cleaned. Pictures embedded in
  a document keep their own metadata, and the document text, comments,
  tracked-change text and hidden content are not touched.
- **HEIC** cleaning re-encodes the picture and keeps only the main image
  (no Live Photo video, depth maps or extra thumbnails).
- **PDF** cleaning writes a new file; digital signatures become invalid.
  Password-protected PDFs are not supported.
- **No video or audio** in version 1.
- **macOS is untested** by the author. Feedback is welcome.

## Development

```powershell
pip install -e ".[dev,gui]"
python -m pytest
```

Tests create their own artificial files with invented EXIF and GPS data, so no
real photos are in this repository. To try your own originals, put them in
`samples/private/` - that folder is ignored by git.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## What is maintained

This is a small project looked after by one person in their spare time.

- **Maintained:** the formats in the table above, the risk ratings and their
  explanations, the "original is never overwritten" rule, the offline guarantee,
  and the automated tests on Windows, Linux and macOS.
- **Welcome and looked at:** bug reports (especially metadata that survives
  `clean`, or a field rated too low), and reports from macOS users.
- **Not promised:** new formats, video/audio, response times, or support for
  every vendor-specific metadata block.

## License

[MIT](LICENSE)
