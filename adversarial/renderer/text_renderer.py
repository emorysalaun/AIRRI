"""Text-to-image rendering with per-line bounding box tracking.

Renders ground truth text into clean images while recording the exact
pixel coordinates of every visual line. Monospace font candidates are
resolved automatically.
"""

import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


@dataclass
class RenderedLine:
    """A single visual line in a rendered image."""

    text: str
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2), exclusive end
    line_index: int = 0


@dataclass
class RenderedImage:
    """A rendered image together with per-line metadata."""

    image: Image.Image
    lines: list[RenderedLine] = field(default_factory=list)
    full_text: str = ""
    image_name: str = ""


# Monospace fonts preferred on Linux platforms.
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/opentype/urw-base35/NimbusMonoPS-Regular.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _resolve_font(font_path: str | None, font_size: int) -> ImageFont.FreeTypeFont:
    """Return a PIL font object, trying the specified path first then fallbacks."""
    if font_path is not None:
        try:
            return ImageFont.truetype(font_path, font_size)
        except OSError:
            pass

    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, font_size)
        except OSError:
            continue

    return ImageFont.load_default()


class TextRenderer:
    """Render ground-truth text into a clean image with tracked line positions."""

    def __init__(
        self,
        font_path: str | None = None,
        font_size: int = 12,
        wrap_width: int = 90,
        margin_x: int = 15,
        margin_top: int = 16,
        margin_bottom: int = 17,
        line_padding: int = 5,
        bg_color: str = "white",
        text_color: str = "black",
    ):
        self.font = _resolve_font(font_path, font_size)
        self.wrap_width = wrap_width
        self.margin_x = margin_x
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom
        self.line_padding = line_padding
        self.bg_color = bg_color
        self.text_color = text_color

    def render(self, text: str, image_name: str = "render.png") -> RenderedImage:
        """Render text into an image and return a RenderedImage."""
        wrapped_lines = textwrap.wrap(text, width=self.wrap_width)

        if not wrapped_lines:
            img = Image.new(
                "RGB",
                (self.margin_x * 2, self.margin_top + self.margin_bottom),
                color=self.bg_color,
            )
            return RenderedImage(
                image=img, lines=[], full_text=text, image_name=image_name
            )

        # Measure dimensions
        dummy = Image.new("RGB", (1, 1), color=self.bg_color)
        draw_dummy = ImageDraw.Draw(dummy)

        line_heights: list[int] = []
        max_w = 0
        for line_text in wrapped_lines:
            bbox = draw_dummy.textbbox((0, 0), line_text, font=self.font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            max_w = max(max_w, w)
            line_heights.append(h)

        img_w = max_w + self.margin_x * 2
        img_h = (
            self.margin_top
            + sum(h + self.line_padding for h in line_heights)
            - self.line_padding
            + self.margin_bottom
        )

        # Draw and track coordinates
        img = Image.new("RGB", (img_w, img_h), color=self.bg_color)
        draw = ImageDraw.Draw(img)

        rendered_lines: list[RenderedLine] = []
        y_cursor = self.margin_top

        for idx, (line_text, line_h) in enumerate(
            zip(wrapped_lines, line_heights)
        ):
            x1 = self.margin_x
            y1 = y_cursor

            draw.text((x1, y1), line_text, fill=self.text_color, font=self.font)

            actual_bbox = draw.textbbox((x1, y1), line_text, font=self.font)
            x2 = actual_bbox[2]
            y2 = actual_bbox[3]

            rendered_lines.append(
                RenderedLine(text=line_text, bbox=(x1, y1, x2, y2), line_index=idx)
            )

            y_cursor += line_h + self.line_padding

        return RenderedImage(
            image=img,
            lines=rendered_lines,
            full_text=text,
            image_name=image_name,
        )

    def render_and_save(
        self, text: str, output_dir: Path, image_name: str = "render.png"
    ) -> RenderedImage:
        """Render text and save the image to output_dir / image_name."""
        rendered = self.render(text, image_name)
        output_dir.mkdir(parents=True, exist_ok=True)
        rendered.image.save(output_dir / image_name)
        return rendered
