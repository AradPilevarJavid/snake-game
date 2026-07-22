"""Strict, dependency-free semantic version handling."""

from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering
import re


_VERSION_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)


@total_ordering
@dataclass(frozen=True)
class Version:
    """A SemVer-compatible version used for update policy decisions."""

    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()

    @classmethod
    def parse(cls, value: str) -> "Version":
        match = _VERSION_RE.fullmatch(value.strip())
        if not match:
            raise ValueError(f"Invalid semantic version: {value!r}")
        prerelease = tuple((match.group("prerelease") or "").split("."))
        if prerelease == ("",):
            prerelease = ()
        return cls(
            int(match.group("major")),
            int(match.group("minor")),
            int(match.group("patch")),
            prerelease,
        )

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-" + ".".join(self.prerelease) if self.prerelease else base

    def _compare_prerelease(self, other: "Version") -> int:
        if not self.prerelease and not other.prerelease:
            return 0
        if not self.prerelease:
            return 1
        if not other.prerelease:
            return -1
        for left, right in zip(self.prerelease, other.prerelease):
            if left == right:
                continue
            left_numeric = left.isdigit()
            right_numeric = right.isdigit()
            if left_numeric and right_numeric:
                return -1 if int(left) < int(right) else 1
            if left_numeric != right_numeric:
                return -1 if left_numeric else 1
            return -1 if left < right else 1
        if len(self.prerelease) == len(other.prerelease):
            return 0
        return -1 if len(self.prerelease) < len(other.prerelease) else 1

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if core != other_core:
            return core < other_core
        return self._compare_prerelease(other) < 0
