"""Firmware version rules shared by the device and the release pipeline (ADR-13).

Python port of ``ota_ver_parse`` / ``ota_ver_cmp`` (components/ota/src/ota_logic.c). Both are tested
against the same vectors, host_tests/vectors/versions.txt, so the release tools can never publish a
manifest whose version the device orders differently.

Grammar (exactly, ASCII digits only, no trailing newline)::

    v?MAJOR.MINOR.PATCH[-rc.N][-AHEAD-gHASH][-dirty]

with every number <= 65535, N and AHEAD >= 1, HASH 4 to 40 lower-case hex digits. Order:
``X.Y.Z-rc.N < X.Y.Z < X.Y.Z-AHEAD-gHASH``; rc numerically, then AHEAD; the hash and ``-dirty`` are
ignored.

Standard library only: the public repository's publish workflow runs a byte-identical copy of this
file next to make_manifests.py (tools/ there, public_repo/tools/ in the private repository, compared
by the private CI).
"""
from __future__ import annotations

import re
from typing import NamedTuple, Optional

NUM_MAX = 65535

# re.ASCII: \d would otherwise match any Unicode digit ("١.٢.٣"); fullmatch() rather than "$", which
# also matches before a trailing newline.
_VERSION_RE = re.compile(
    r"v?([0-9]+)\.([0-9]+)\.([0-9]+)(?:-rc\.([0-9]+))?(?:-([0-9]+)-g[0-9a-f]{4,40})?(-dirty)?",
    re.ASCII,
)

#: A release tag (what CI publishes): no git describe suffix, no -dirty.
RELEASE_TAG_RE = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?", re.ASCII)


class Version(NamedTuple):
    """Parsed version; field names mirror ota_ver_t."""

    major: int
    minor: int
    patch: int
    rc: int = 0       # 0: not a release candidate
    ahead: int = 0    # commits ahead of the tag (git describe)
    dirty: bool = False

    def sort_key(self) -> tuple:
        # A release (rc == 0) sorts after all of its candidates.
        rc_rank = self.rc if self.rc else NUM_MAX + 1
        return (self.major, self.minor, self.patch, rc_rank, self.ahead)


def parse(text: object) -> Optional[Version]:
    """Return the Version, or None when @p text is not in the grammar (like ota_ver_parse)."""
    if not isinstance(text, str):
        return None
    m = _VERSION_RE.fullmatch(text)
    if not m:
        return None
    major, minor, patch, rc, ahead, dirty = m.groups()
    nums = [int(major), int(minor), int(patch), int(rc or 0), int(ahead or 0)]
    if any(n > NUM_MAX for n in nums):
        return None
    if (rc is not None and nums[3] == 0) or (ahead is not None and nums[4] == 0):
        return None
    return Version(*nums, dirty=dirty is not None)


def compare(a: Version, b: Version) -> int:
    """-1, 0 or 1, like the sign of ota_ver_cmp."""
    ka, kb = a.sort_key(), b.sort_key()
    return (ka > kb) - (ka < kb)


def compare_str(a: str, b: str) -> int:
    """Compare two version strings; ValueError if either does not parse."""
    va, vb = parse(a), parse(b)
    if va is None or vb is None:
        raise ValueError(f"not a firmware version: {a!r}" if va is None else f"not a firmware version: {b!r}")
    return compare(va, vb)


def is_release_tag(tag: str) -> bool:
    """A tag CI may publish: vX.Y.Z or vX.Y.Z-rc.N, within the version grammar."""
    return isinstance(tag, str) and RELEASE_TAG_RE.fullmatch(tag) is not None and parse(tag) is not None


def is_final(tag: str) -> bool:
    """A final release (not a release candidate)."""
    v = parse(tag)
    return v is not None and v.rc == 0 and v.ahead == 0 and not v.dirty
