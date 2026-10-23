#!/usr/bin/env python3
"""Generate the release manifests and assets from a SIGNED app image (ADR-13, ADR-14).

Run by the public repository's publish workflow right after signing. Source of truth and tests:
tools/release/ of the private repository; the public repository runs a byte-identical copy (tools/
there, public_repo/tools/ in the private repository, compared by the private CI) together with
versions.py, so its workflow never runs code fetched from the private repository. Standard library
only.

Inputs: the signed app image, build/flasher_args.json (flash offsets: never hard-coded) and a
directory holding bootloader.bin, partition-table.bin and ota_data_initial.bin from the same build.

Output directory (must not exist, or be empty)::

    manifest.json                         device manifest, schema 1 (read by ota_manifest_parse)
    m5dial-kitchen-timer-<app>-<tag>.bin  the signed app, under its published name
    bootloader.bin, partition-table.bin, ota_data_initial.bin
    SHA256SUMS                            sha256sum -c format, for every file above
    webinstall/manifest.json              ESP Web Tools manifest (paths relative to the site root)
    webinstall/firmware/<tag>/...         the four flashed parts, copied into the Pages artifact

Refuses to produce anything when:
- the tag is not vX.Y.Z[-rc.N], or the image's esp_app_desc_t version differs from it;
- the image does not end with a valid Secure Boot v2 signature sector (an unsigned release image
  stops at boot, ADR-13), or the signed digest does not match the image;
- a flashed part overlaps another one or an NVS partition (an install without erase must keep
  settings, Wi-Fi and timers, ADR-14), or the app does not fit its OTA slot;
- the device manifest would be rejected by the device's own parser (same rules as ota_logic.c:
  field lengths, printable ASCII, https URL under the release prefix, size, <= 4096 bytes).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import shutil
import struct
import sys
import zlib
from pathlib import Path
from typing import NamedTuple, Optional

import versions

# ---- Device contract (components/ota/include/ota_logic.h) ----
MANIFEST_MAX = 4096          # OTA_MANIFEST_MAX
PROJECT_LEN = 32             # char project[32] (NUL included)
APP_LEN = 16
VERSION_LEN = 32             # OTA_VER_LEN
URL_LEN = 256                # OTA_URL_LEN
RELEASED_LEN = 16
NOTES_MAX = 512              # characters; notes are informative, the device skips them

APP_ASSET = "m5dial-kitchen-timer-{app}-{tag}.bin"
WEB_NAME = "Minuteur M5Dial"
WEB_CHIP_FAMILY = "ESP32-S3"
PARTS = ("bootloader.bin", "partition-table.bin", "ota_data_initial.bin")

# ---- ESP-IDF binary formats ----
IMAGE_MAGIC = 0xE9
IMAGE_HEADER_LEN = 24        # esp_image_header_t
SEGMENT_HEADER_LEN = 8       # esp_image_segment_header_t
APP_DESC_MAGIC = 0xABCD5432  # esp_app_desc_t, first thing in the first segment
APP_DESC_OFFSET = IMAGE_HEADER_LEN + SEGMENT_HEADER_LEN
SIG_SECTOR_LEN = 4096        # Secure Boot v2 signature sector, appended by espsecure sign-data
SIG_BLOCK_MAGIC = 0xE7
SIG_BLOCK_VERSION = 0x02     # RSA (ADR-13: RSA-3072); 0x03 would be ECDSA
SIG_BLOCK_CRC_OFFSET = 1196  # 1216-byte block: 1196 bytes of data, their CRC-32, 16 bytes of padding
PART_ENTRY_LEN = 32
PART_MAGIC = b"\xaa\x50"
PART_TYPE_APP = 0x00
PART_TYPE_DATA = 0x01
PART_SUBTYPE_NVS = 0x02

_REPO_RE = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", re.ASCII)
_APP_RE = re.compile(r"[a-z0-9_]{1,15}", re.ASCII)
_PRINTABLE_RE = re.compile(r"[\x20-\x7e]+", re.ASCII)
_URL_SUFFIX_RE = re.compile(r"[A-Za-z0-9._~+/-]+", re.ASCII)
_SHA256_RE = re.compile(r"[0-9a-f]{64}", re.ASCII)
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)


class ReleaseError(Exception):
    """A release input or output is not acceptable: nothing must be published."""


class AppDesc(NamedTuple):
    version: str
    project: str


class Partition(NamedTuple):
    type: int
    subtype: int
    offset: int
    size: int
    label: str


# ---- Image inspection ----

def _cstr(raw: bytes, what: str) -> str:
    text = raw.split(b"\0", 1)[0]
    try:
        return text.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ReleaseError(f"{what} is not ASCII: {text!r}") from exc


def read_app_desc(image: bytes) -> AppDesc:
    """version and project_name of the esp_app_desc_t that starts the first segment."""
    if len(image) < APP_DESC_OFFSET + 80 or image[0] != IMAGE_MAGIC:
        raise ReleaseError("not an ESP-IDF app image (bad header magic)")
    (magic,) = struct.unpack_from("<I", image, APP_DESC_OFFSET)
    if magic != APP_DESC_MAGIC:
        raise ReleaseError(f"esp_app_desc_t magic 0x{magic:08X} != 0x{APP_DESC_MAGIC:08X}")
    # magic(4) secure_version(4) reserv1[2](8) version[32] project_name[32]
    version = _cstr(image[APP_DESC_OFFSET + 16:APP_DESC_OFFSET + 48], "app version")
    project = _cstr(image[APP_DESC_OFFSET + 48:APP_DESC_OFFSET + 80], "project name")
    return AppDesc(version, project)


def check_signature_sector(image: bytes) -> None:
    """The image ends with a Secure Boot v2 RSA signature sector whose first block signs the rest.

    This does not verify the RSA signature itself (the workflow does it with espsecure and the
    committed public key); it catches an unsigned image, or a signature of other content.
    """
    if len(image) <= SIG_SECTOR_LEN or len(image) % SIG_SECTOR_LEN:
        raise ReleaseError("app image is not signed (size is not a multiple of 4096 with a signature sector)")
    block = image[-SIG_SECTOR_LEN:]
    if block[0] != SIG_BLOCK_MAGIC or block[1] != SIG_BLOCK_VERSION:
        raise ReleaseError("app image is not signed (no Secure Boot v2 signature block at the end)")
    (crc,) = struct.unpack_from("<I", block, SIG_BLOCK_CRC_OFFSET)
    if zlib.crc32(block[:SIG_BLOCK_CRC_OFFSET]) != crc:
        raise ReleaseError("signature block CRC mismatch")
    if block[4:36] != hashlib.sha256(image[:-SIG_SECTOR_LEN]).digest():
        raise ReleaseError("signature block digest does not match the image content")


def read_partitions(table: bytes) -> list[Partition]:
    """Entries of a binary partition table (stops at the MD5 entry or the 0xFF filler)."""
    parts = []
    for off in range(0, len(table) - PART_ENTRY_LEN + 1, PART_ENTRY_LEN):
        entry = table[off:off + PART_ENTRY_LEN]
        if entry[:2] != PART_MAGIC:
            break
        ptype, subtype, offset, size = struct.unpack_from("<BBII", entry, 2)
        label = entry[12:28].split(b"\0", 1)[0].decode("ascii", "replace")
        parts.append(Partition(ptype, subtype, offset, size, label))
    if not parts:
        raise ReleaseError("partition-table.bin holds no partition")
    return parts


def flash_files(flasher_args: dict) -> tuple[list[tuple[int, str]], str]:
    """(offset, basename) of every flashed file, sorted by offset, and the app's basename."""
    files = flasher_args.get("flash_files")
    if not isinstance(files, dict) or not files:
        raise ReleaseError("flasher_args.json has no flash_files")
    layout = sorted((int(off, 0), Path(path).name) for off, path in files.items())
    names = [name for _, name in layout]
    if len(set(names)) != len(names):
        raise ReleaseError(f"duplicate file names in flash_files: {names}")
    app = flasher_args.get("app", {}).get("file")
    app_name = Path(app).name if isinstance(app, str) else None
    if app_name not in names:
        raise ReleaseError("flasher_args.json does not name the app among flash_files")
    if sorted(n for n in names if n != app_name) != sorted(PARTS):
        raise ReleaseError(f"unexpected flashed files {names}: expected the app and {list(PARTS)}")
    return layout, app_name


# ---- Device manifest rules (port of ota_manifest_parse / the context-free ota_manifest_check) ----

def _check_str(m: dict, key: str, cap: int) -> str:
    value = m.get(key)
    if not isinstance(value, str) or not value or len(value) >= cap or not _PRINTABLE_RE.fullmatch(value):
        raise ReleaseError(f"manifest {key!r} must be 1..{cap - 1} printable ASCII characters: {value!r}")
    return value


def validate_device_manifest(m: dict, *, project: str, app: str, url_prefix: str, slot_size: int) -> None:
    """Raise ReleaseError unless the device would accept @p m (parse, then project/app/url/size)."""
    if type(m.get("schema")) is not int or m["schema"] != 1:
        raise ReleaseError("manifest schema must be the integer 1")
    for key, cap in (("project", PROJECT_LEN), ("app", APP_LEN), ("version", VERSION_LEN), ("url", URL_LEN),
                     ("released", RELEASED_LEN)):
        _check_str(m, key, cap)
    if versions.parse(m["version"]) is None:
        raise ReleaseError(f"manifest version does not parse: {m['version']!r}")
    if "min_version" in m:
        if versions.parse(_check_str(m, "min_version", VERSION_LEN)) is None:
            raise ReleaseError(f"manifest min_version does not parse: {m['min_version']!r}")
        if versions.compare_str(m["min_version"], m["version"]) > 0:
            raise ReleaseError("min_version is newer than the version itself")
    size = m.get("size")
    if type(size) is not int or not 1 <= size <= 0xFFFFFFFF:
        raise ReleaseError(f"manifest size must be a positive uint32: {size!r}")
    if not isinstance(m.get("sha256"), str) or not _SHA256_RE.fullmatch(m["sha256"]):
        raise ReleaseError("manifest sha256 must be 64 lower-case hex digits")
    if m["project"] != project or m["app"] != app:
        raise ReleaseError(f"manifest project/app {m['project']}/{m['app']} != {project}/{app}")
    url = m["url"]
    if not (url_prefix.startswith("https://") and url_prefix.endswith("/") and url.startswith(url_prefix)):
        raise ReleaseError(f"manifest url must be https and start with {url_prefix}")
    rest = url[len(url_prefix):]
    if not _URL_SUFFIX_RE.fullmatch(rest) or ".." in rest:
        raise ReleaseError(f"manifest url has characters the device refuses: {url}")
    if size > slot_size:
        raise ReleaseError(f"app image ({size} bytes) does not fit its OTA slot ({slot_size} bytes)")


def encode_manifest(m: dict) -> bytes:
    """UTF-8 JSON as published. ensure_ascii: notes become \\uXXXX escapes, which the device skips."""
    data = (json.dumps(m, indent=2, ensure_ascii=True) + "\n").encode("ascii")
    if len(data) > MANIFEST_MAX:
        raise ReleaseError(f"device manifest is {len(data)} bytes, the device reads at most {MANIFEST_MAX}")
    return data


def trim_notes(text: str) -> str:
    text = text.strip()
    if len(text) > NOTES_MAX:
        text = text[:NOTES_MAX - 1].rstrip() + "…"
    return text


# ---- Main ----

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _overlaps(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 < b1 and b0 < a1


def make(tag: str, app: str, app_bin: Path, flasher_args: Path, parts_dir: Path, repo: str, notes: Path,
         out: Path, min_version: Optional[str] = None, released: Optional[str] = None) -> dict:
    """Write everything into @p out and return the device manifest."""
    if not versions.is_release_tag(tag):
        raise ReleaseError(f"tag {tag!r} is not vX.Y.Z or vX.Y.Z-rc.N")
    if not _APP_RE.fullmatch(app):
        raise ReleaseError(f"app {app!r} must be 1..15 of [a-z0-9_]")
    if not _REPO_RE.fullmatch(repo):
        raise ReleaseError(f"repo {repo!r} must be owner/name")
    if min_version is not None and versions.parse(min_version) is None:
        raise ReleaseError(f"min-version {min_version!r} does not parse")
    if released is None:
        released = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    elif not _DATE_RE.fullmatch(released):
        raise ReleaseError(f"released {released!r} is not YYYY-MM-DD")
    else:
        datetime.date.fromisoformat(released)   # ValueError on an impossible date
    if out.exists() and any(out.iterdir()):
        raise ReleaseError(f"output directory {out} is not empty")

    image = app_bin.read_bytes()
    desc = read_app_desc(image)
    if desc.version != tag:
        raise ReleaseError(f"image version {desc.version!r} != tag {tag!r} (built from another commit?)")
    check_signature_sector(image)

    layout, app_name = flash_files(json.loads(flasher_args.read_text(encoding="utf-8")))
    asset = APP_ASSET.format(app=app, tag=tag)
    sources = {name: (app_bin if name == app_name else parts_dir / name) for _, name in layout}
    for name, src in sources.items():
        if not src.is_file():
            raise ReleaseError(f"missing {src}")
    sizes = {name: src.stat().st_size for name, src in sources.items()}

    # Flash map sanity: parts do not overlap each other nor any NVS partition; the app fits its slot.
    table = read_partitions(sources["partition-table.bin"].read_bytes())
    for i, (off, name) in enumerate(layout):
        end = off + sizes[name]
        if i + 1 < len(layout) and end > layout[i + 1][0]:
            raise ReleaseError(f"{name} (0x{off:X}..0x{end:X}) overlaps {layout[i + 1][1]}")
        for p in table:
            if p.type == PART_TYPE_DATA and p.subtype == PART_SUBTYPE_NVS and \
                    _overlaps(off, end, p.offset, p.offset + p.size):
                raise ReleaseError(f"{name} overlaps NVS partition {p.label!r}: an install would erase settings")
    app_offset = next(off for off, name in layout if name == app_name)
    slot = next((p for p in table if p.type == PART_TYPE_APP and p.offset == app_offset), None)
    if slot is None:
        raise ReleaseError(f"no app partition at the app offset 0x{app_offset:X}")

    manifest = {
        "schema": 1,
        "project": desc.project,
        "app": app,
        "version": tag,
        **({"min_version": min_version} if min_version is not None else {}),
        "url": f"https://github.com/{repo}/releases/download/{tag}/{asset}",
        "size": len(image),
        "sha256": hashlib.sha256(image).hexdigest(),
        "released": released,
        "notes": trim_notes(notes.read_text(encoding="utf-8-sig")),   # -sig: a BOM from a Windows editor
    }
    validate_device_manifest(manifest, project=desc.project, app=app,
                             url_prefix=f"https://github.com/{repo}/releases/download/", slot_size=slot.size)
    manifest_bytes = encode_manifest(manifest)

    # Release assets.
    out.mkdir(parents=True, exist_ok=True)
    published = {name: (asset if name == app_name else name) for _, name in layout}
    for name, src in sources.items():
        shutil.copyfile(src, out / published[name])
    (out / "manifest.json").write_bytes(manifest_bytes)
    sums = sorted([*published.values(), "manifest.json"])
    (out / "SHA256SUMS").write_text("".join(f"{_sha256(out / n)}  {n}\n" for n in sums),
                                    encoding="ascii", newline="\n")

    # ESP Web Tools: separate parts at the build's own offsets, never a merged image (its 0xFF
    # filler would erase NVS). The app part is the signed image.
    web_dir = out / "webinstall"
    fw_dir = web_dir / "firmware" / tag
    fw_dir.mkdir(parents=True)
    for name, src in sources.items():
        shutil.copyfile(src, fw_dir / published[name])
    web = {
        "name": WEB_NAME,
        "version": tag,
        "new_install_prompt_erase": True,
        "new_install_improv_wait_time": 0,
        "builds": [{
            "chipFamily": WEB_CHIP_FAMILY,
            "parts": [{"path": f"firmware/{tag}/{published[name]}", "offset": off} for off, name in layout],
        }],
    }
    (web_dir / "manifest.json").write_text(json.dumps(web, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8", newline="\n")
    return manifest


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tag", required=True, help="release tag, vX.Y.Z or vX.Y.Z-rc.N")
    ap.add_argument("--app", required=True, help="application id of the build (manifest 'app'), e.g. timer")
    ap.add_argument("--app-bin", required=True, type=Path, help="SIGNED app image")
    ap.add_argument("--flasher-args", required=True, type=Path, help="build/flasher_args.json")
    ap.add_argument("--parts-dir", required=True, type=Path, help="directory with " + ", ".join(PARTS))
    ap.add_argument("--repo", required=True, help="public repository owner/name")
    ap.add_argument("--notes", required=True, type=Path, help="release notes (Markdown)")
    ap.add_argument("--min-version", help="oldest running version allowed to install this one")
    ap.add_argument("--released", help="release date YYYY-MM-DD (default: today, UTC)")
    ap.add_argument("--out", required=True, type=Path, help="output directory (created; must be empty)")
    args = ap.parse_args(argv)
    try:
        m = make(args.tag, args.app, args.app_bin, args.flasher_args, args.parts_dir, args.repo, args.notes,
                 args.out, args.min_version, args.released)
    except (ReleaseError, OSError, ValueError) as exc:
        print(f"make_manifests: error: {exc}", file=sys.stderr)
        return 1
    print(f"make_manifests: {m['project']}/{m['app']} {m['version']}, {m['size']} bytes, sha256 {m['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
