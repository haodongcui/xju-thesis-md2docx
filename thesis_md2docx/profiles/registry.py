from __future__ import annotations

from .base import ThesisProfile
from .xju_undergraduate_thesis import XjuUndergraduateThesisProfile


DEFAULT_PROFILE_NAME = "xju-undergraduate-thesis"
PROFILES: tuple[ThesisProfile, ...] = (XjuUndergraduateThesisProfile(),)
PROFILE_BY_NAME: dict[str, ThesisProfile] = {profile.name: profile for profile in PROFILES}


def profile_names() -> list[str]:
    return [profile.name for profile in PROFILES]


def get_profile(name: str | ThesisProfile | None = None) -> ThesisProfile:
    if isinstance(name, ThesisProfile):
        return name
    normalized = (name or DEFAULT_PROFILE_NAME).strip().lower()
    profile = PROFILE_BY_NAME.get(normalized)
    if profile is None:
        raise ValueError(f"unknown thesis profile: {name}")
    return profile
