from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...builders.elements import resolve_cover_assets_dir
from ...constants import DEFAULT_COVER_ASSETS_DIR
from ...math.converter import MathConverter
from ...media import MediaManager
from ..base import ThesisProfile
from .body import body_style_profile
from .document import build_document as build_profile_document


@dataclass(frozen=True)
class XjuUndergraduateThesisProfile(ThesisProfile):
    name: str = "xju-undergraduate-thesis"
    display_name: str = "Xinjiang University undergraduate thesis"
    default_cover_assets_dir: Path | None = DEFAULT_COVER_ASSETS_DIR

    def resolve_cover_assets_dir(
        self,
        markdown_path: Path,
        assets_dir: Path | None,
        *,
        use_cover_assets: bool,
    ) -> Path | None:
        return resolve_cover_assets_dir(
            markdown_path,
            assets_dir or self.default_cover_assets_dir,
            use_cover_assets=use_cover_assets,
        )

    def body_style_profile(self) -> dict[str, object]:
        return body_style_profile()

    def build_document(
        self,
        text: str,
        *,
        math_converter: MathConverter | None = None,
        reference_anchors: dict[str, str] | None = None,
        markdown_dir: Path | None = None,
        cover_assets_dir: Path | None = None,
        media_manager: MediaManager | None = None,
    ) -> tuple[list[str], str, str]:
        return build_profile_document(
            text,
            thesis_profile=self,
            math_converter=math_converter,
            reference_anchors=reference_anchors,
            markdown_dir=markdown_dir,
            cover_assets_dir=cover_assets_dir,
            media_manager=media_manager,
        )
