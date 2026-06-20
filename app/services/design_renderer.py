"""Render design template ``design_data`` to a PNG image using Pillow."""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# Google Fonts download cache
FONT_CACHE_DIR = Path(os.environ.get("FONT_CACHE_DIR", "/tmp/souvenirx_fonts"))
FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

CUSTOM_FONT_DIR = Path(os.environ.get("CUSTOM_FONT_DIR", "/app/uploads/fonts"))


class DesignRenderer:
    """Render a design canvas with text, shape, and image layers."""

    def __init__(self, width: int = 1000, height: int = 1000):
        self.width = width
        self.height = height

    def render(
        self,
        design_data: dict[str, Any],
        output_format: str = "PNG",
        quality: int = 90,
    ) -> bytes:
        """Render design_data to PNG bytes."""
        canvas = design_data.get("canvas", {})
        width = canvas.get("width", self.width)
        height = canvas.get("height", self.height)
        background = canvas.get("background", "#ffffff")

        img = Image.new("RGBA", (width, height), self._parse_color(background))
        draw = ImageDraw.Draw(img)

        layers = sorted(
            design_data.get("layers", []),
            key=lambda layer: layer.get("properties", {}).get("zIndex", 0),
        )

        for layer in layers:
            if not layer.get("visible", True):
                continue
            try:
                self._render_layer(img, draw, layer, width, height)
            except Exception:
                # Skip layers that fail to render so the whole image doesn't break
                continue

        buffer = io.BytesIO()
        if output_format.upper() == "JPEG":
            # Convert to RGB for JPEG
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3])
            rgb_img.save(buffer, format="JPEG", quality=quality)
        else:
            img.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def _parse_color(color: str | None) -> tuple[int, int, int, int]:
        if not color:
            return (255, 255, 255, 255)
        color = color.strip()
        if color.startswith("#"):
            color = color[1:]
            if len(color) == 3:
                color = "".join(c * 2 for c in color)
            if len(color) == 6:
                r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
                return (r, g, b, 255)
            if len(color) == 8:
                r = int(color[0:2], 16)
                g = int(color[2:4], 16)
                b = int(color[4:6], 16)
                a = int(color[6:8], 16)
                return (r, g, b, a)
        return (255, 255, 255, 255)

    def _render_layer(
        self,
        img: Image.Image,
        draw: ImageDraw.Draw,
        layer: dict[str, Any],
        canvas_width: int,
        canvas_height: int,
    ) -> None:
        layer_type = layer.get("type", "text")
        content = layer.get("content", "")
        props = layer.get("properties", {})
        opacity = props.get("opacity", 1.0)
        rotation = props.get("rotation", 0)
        x = props.get("x", canvas_width / 2)
        y = props.get("y", canvas_height / 2)

        if layer_type == "text":
            self._render_text_layer(img, content, props, x, y, opacity, rotation)
        elif layer_type == "icon":
            self._render_icon_layer(img, content, props, x, y, opacity, rotation)
        elif layer_type == "shape":
            self._render_shape_layer(img, draw, content, props, x, y, opacity, rotation)
        elif layer_type == "image":
            self._render_image_layer(img, content, props, x, y, opacity, rotation)

    def _render_text_layer(
        self,
        img: Image.Image,
        content: str,
        props: dict[str, Any],
        x: int,
        y: int,
        opacity: float,
        rotation: float,
    ) -> None:
        font_size = props.get("fontSize", 48)
        font_family = props.get("fontFamily", "Inter")
        color = self._parse_color(props.get("color", "#000000"))
        align = props.get("textAlign", "center")
        weight = props.get("fontWeight", "normal")
        italic = props.get("fontStyle", "normal") == "italic"
        letter_spacing = props.get("letterSpacing", 0)

        font = self._load_font(font_family, font_size, weight, italic)

        # Measure text
        lines = content.split("\n")
        max_width = 0
        total_height = 0
        line_heights = []
        for line in lines:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0] if bbox else 0
            line_height = bbox[3] - bbox[1] if bbox else font_size
            if letter_spacing:
                line_width += int(letter_spacing * (len(line)))
            max_width = max(max_width, line_width)
            line_heights.append(line_height)
            total_height += line_height

        # Create text image
        text_img = Image.new("RGBA", (max_width + 20, total_height + 20), (255, 255, 255, 0))
        text_draw = ImageDraw.Draw(text_img)

        current_y = 10
        for i, line in enumerate(lines):
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0] if bbox else 0
            if align == "center":
                line_x = (text_img.width - line_width) // 2
            elif align == "right":
                line_x = text_img.width - line_width - 10
            else:
                line_x = 10

            if letter_spacing and len(line) > 1:
                # Draw each char with spacing
                char_x = line_x
                for char in line:
                    text_draw.text((char_x, current_y), char, font=font, fill=color)
                    char_bbox = font.getbbox(char)
                    char_width = char_bbox[2] - char_bbox[0] if char_bbox else 0
                    char_x += char_width + int(letter_spacing)
            else:
                text_draw.text((line_x, current_y), line, font=font, fill=color)
            current_y += line_heights[i]

        if opacity < 1.0:
            alpha = text_img.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity))
            text_img.putalpha(alpha)

        if rotation:
            text_img = text_img.rotate(
                -rotation, expand=True, resample=Image.Resampling.BICUBIC
            )

        paste_x = int(x - text_img.width / 2)
        paste_y = int(y - text_img.height / 2)
        img.paste(text_img, (paste_x, paste_y), text_img)

    def _render_icon_layer(
        self,
        img: Image.Image,
        content: str,
        props: dict[str, Any],
        x: int,
        y: int,
        opacity: float,
        rotation: float,
    ) -> None:
        """Render an emoji icon using a system emoji font if available."""
        size = props.get("size", 80)

        icon_img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        icon_draw = ImageDraw.Draw(icon_img)

        font = self._load_emoji_font(size)

        try:
            bbox = icon_draw.textbbox((0, 0), content, font=font)
            text_width = bbox[2] - bbox[0] if bbox else size
            text_height = bbox[3] - bbox[1] if bbox else size
            text_x = (size - text_width) // 2 - bbox[0] if bbox else 0
            text_y = (size - text_height) // 2 - bbox[1] if bbox else 0
            icon_draw.text((text_x, text_y), content, font=font, embedded_color=True)
        except Exception:
            # Fallback: draw a simple circle with the emoji codepoint
            try:
                icon_draw.text((size // 4, size // 4), content, font=font)
            except Exception:
                return

        if opacity < 1.0:
            alpha = icon_img.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity))
            icon_img.putalpha(alpha)

        if rotation:
            icon_img = icon_img.rotate(
                -rotation, expand=True, resample=Image.Resampling.BICUBIC
            )

        paste_x = int(x - icon_img.width / 2)
        paste_y = int(y - icon_img.height / 2)
        img.paste(icon_img, (paste_x, paste_y), icon_img)

    def _load_emoji_font(self, size: int):
        """Try to find a system emoji font; fall back to the default font."""
        candidates = [
            "/System/Library/Fonts/Apple Color Emoji.ttc",
            "/System/Library/Fonts/Apple Color Emoji.ttf",
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
            "/usr/share/fonts/truetype/noto/NotoColorEmoji-Regular.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        try:
            return ImageFont.truetype(str(FONT_CACHE_DIR / "Inter-Regular.ttf"), size)
        except Exception:
            return ImageFont.load_default()

    def _render_shape_layer(
        self,
        img: Image.Image,
        draw: ImageDraw.Draw,
        content: str,
        props: dict[str, Any],
        x: int,
        y: int,
        opacity: float,
        rotation: float,
    ) -> None:
        fill_color = self._parse_color(props.get("color", "#000000"))
        stroke_color = self._parse_color(props.get("strokeColor", "#000000"))
        stroke_width = props.get("strokeWidth", 0)
        width = props.get("width", 100)
        height = props.get("height", 100)
        radius = props.get("radius", 50)
        size = props.get("size", 40)

        shape_img = Image.new("RGBA", (width + 20, height + 20), (255, 255, 255, 0))
        shape_draw = ImageDraw.Draw(shape_img)

        if content == "circle":
            bbox = [10, 10, 10 + radius * 2, 10 + radius * 2]
            shape_draw.ellipse(bbox, fill=fill_color, outline=stroke_color, width=stroke_width)
        elif content == "rectangle":
            bbox = [10, 10, 10 + width, 10 + height]
            shape_draw.rectangle(bbox, fill=fill_color, outline=stroke_color, width=stroke_width)
        elif content == "line":
            shape_draw.line(
                [(10, 10 + height // 2), (10 + width, 10 + height // 2)],
                fill=fill_color,
                width=stroke_width or 2,
            )
        elif content == "heart":
            self._draw_heart(shape_draw, x=shape_img.width // 2, y=shape_img.height // 2, size=size, fill=fill_color)
        else:
            # Default rectangle
            bbox = [10, 10, 10 + width, 10 + height]
            shape_draw.rectangle(bbox, fill=fill_color, outline=stroke_color, width=stroke_width)

        if opacity < 1.0:
            alpha = shape_img.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity))
            shape_img.putalpha(alpha)

        if rotation:
            shape_img = shape_img.rotate(
                -rotation, expand=True, resample=Image.Resampling.BICUBIC
            )

        paste_x = int(x - shape_img.width / 2)
        paste_y = int(y - shape_img.height / 2)
        img.paste(shape_img, (paste_x, paste_y), shape_img)

    @staticmethod
    def _draw_heart(draw: ImageDraw.Draw, x: int, y: int, size: int, fill: tuple) -> None:
        """Draw a heart shape using a polygon approximation."""
        points = []
        for i in range(100):
            t = i / 100.0 * 2 * math.pi
            # Parametric heart curve
            hx = size * 16 * math.sin(t) ** 3
            hy = -size * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            points.append((x + hx / 16, y + hy / 16))
        draw.polygon(points, fill=fill)

    def _render_image_layer(
        self,
        img: Image.Image,
        content: str,
        props: dict[str, Any],
        x: int,
        y: int,
        opacity: float,
        rotation: float,
    ) -> None:
        if not content:
            return
        try:
            image_url = content
            if image_url.startswith("/uploads/"):
                base_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
                image_url = f"{base_url}{image_url}"

            req = urllib.request.Request(
                image_url,
                headers={"User-Agent": "SouvenirX-DesignRenderer/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                image_data = response.read()

            layer_img = Image.open(io.BytesIO(image_data)).convert("RGBA")
            width = props.get("width", layer_img.width)
            height = props.get("height", layer_img.height)
            layer_img = layer_img.resize((int(width), int(height)), Image.Resampling.LANCZOS)

            if opacity < 1.0:
                alpha = layer_img.split()[3]
                alpha = alpha.point(lambda p: int(p * opacity))
                layer_img.putalpha(alpha)

            if rotation:
                layer_img = layer_img.rotate(
                    -rotation, expand=True, resample=Image.Resampling.BICUBIC
                )

            paste_x = int(x - layer_img.width / 2)
            paste_y = int(y - layer_img.height / 2)
            img.paste(layer_img, (paste_x, paste_y), layer_img)
        except Exception:
            return

    def _load_font(
        self,
        font_family: str,
        font_size: int,
        weight: str = "normal",
        italic: bool = False,
    ) -> ImageFont.FreeTypeFont:
        """Load a font file from cache or download from Google Fonts."""
        font_family = font_family or "Inter"
        weight_num = self._weight_to_number(weight)
        style = "italic" if italic else "normal"
        cache_key = f"{font_family.replace(' ', '_')}_{weight_num}_{style}_{font_size}"
        cache_path = FONT_CACHE_DIR / f"{cache_key}.ttf"

        if cache_path.exists():
            return ImageFont.truetype(str(cache_path), font_size)

        # Try custom font directory
        custom_files = list(CUSTOM_FONT_DIR.glob("*.ttf")) + list(CUSTOM_FONT_DIR.glob("*.otf"))
        for custom_file in custom_files:
            if font_family.lower() in custom_file.name.lower():
                try:
                    return ImageFont.truetype(str(custom_file), font_size)
                except Exception:
                    continue

        # Try Google Fonts
        try:
            google_font = self._download_google_font(font_family, weight_num, italic)
            if google_font:
                return ImageFont.truetype(google_font, font_size)
        except Exception:
            pass

        # Fallback to default
        try:
            return ImageFont.truetype(str(FONT_CACHE_DIR / "Inter-Regular.ttf"), font_size)
        except Exception:
            return ImageFont.load_default()

    @staticmethod
    def _weight_to_number(weight: str) -> int:
        mapping = {
            "normal": 400,
            "bold": 700,
            "100": 100,
            "200": 200,
            "300": 300,
            "400": 400,
            "500": 500,
            "600": 600,
            "700": 700,
            "800": 800,
            "900": 900,
        }
        return mapping.get(str(weight).lower(), 400)

    @staticmethod
    def _download_google_font(font_family: str, weight: int, italic: bool) -> str | None:
        """Download a Google Font TTF file and cache it."""
        family_query = urllib.parse.quote(font_family)
        style = "italic" if italic else "normal"
        css_url = f"https://fonts.googleapis.com/css2?family={family_query}:wght@{weight}&display=swap"

        try:
            req = urllib.request.Request(
                css_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                css = response.read().decode("utf-8")
        except Exception:
            return None

        # Find font URL in CSS
        match = re.search(r"url\((https://[^)]+\.ttf)\)", css)
        if not match:
            return None

        font_url = match.group(1)
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", font_family)
        font_filename = f"{safe_name}_{weight}_{style}.ttf"
        font_path = FONT_CACHE_DIR / font_filename

        if not font_path.exists():
            try:
                urllib.request.urlretrieve(font_url, font_path)
            except Exception:
                return None

        return str(font_path)



def render_design_to_bytes(design_data: dict[str, Any]) -> bytes:
    """Convenience function to render design_data to PNG bytes."""
    renderer = DesignRenderer()
    return renderer.render(design_data)
