"""Finds images on a page and extracts EXIF metadata with smart filtering.

Layer 1 (EXIF found): the image is saved to disk and its GPS/device/date are reported.
Layer 2 (no EXIF): the image is discarded immediately, only its URL is logged.
"""

import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import ExifTags, Image

from cleantrace.verifier import USER_AGENT


def find_images(html: str, base_url: str) -> list[str]:
    """Returns the absolute URLs of every <img> on the page, in document order."""
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    urls = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        absolute = urljoin(base_url, src)
        if absolute not in seen:
            seen.add(absolute)
            urls.append(absolute)
    return urls


def process_page_images(page_url: str, html: str, images_dir: Path, timeout: int) -> list[dict]:
    """Downloads every image on the page and applies the EXIF layers to each."""
    return [
        _process_image(page_url, image_url, images_dir, timeout)
        for image_url in find_images(html, page_url)
    ]


def _process_image(page_url: str, image_url: str, images_dir: Path, timeout: int) -> dict:
    headers = {"User-Agent": USER_AGENT}
    tmp_path: Path | None = None
    try:
        try:
            response = requests.get(image_url, headers=headers, timeout=timeout)
        except requests.RequestException:
            return {"url": image_url, "status": "error"}

        if response.status_code != 200 or not response.content:
            return {"url": image_url, "status": "error"}

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_path = Path(tmp_file.name)

        try:
            with Image.open(tmp_path) as image:
                exif = image.getexif()
        except Exception:
            return {"url": image_url, "status": "error"}

        if not exif:
            return {"url": image_url, "status": "no_exif"}

        gps = _format_gps(exif.get_ifd(ExifTags.IFD.GPSInfo))
        device = _format_device(exif.get(ExifTags.Base.Make), exif.get(ExifTags.Base.Model))
        date = exif.get(ExifTags.Base.DateTimeOriginal) or exif.get(ExifTags.Base.DateTime)

        images_dir.mkdir(parents=True, exist_ok=True)
        dest = _unique_destination(images_dir, _image_filename(page_url, image_url))
        shutil.move(str(tmp_path), str(dest))
        tmp_path = None

        return {
            "url": image_url,
            "status": "exif",
            "gps": gps,
            "device": device,
            "date": date,
            "saved_path": str(dest),
        }
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def _format_gps(gps_ifd: dict | None) -> str | None:
    if not gps_ifd:
        return None
    try:
        lat = _to_decimal_degrees(gps_ifd[2])
        if gps_ifd[1] == "S":
            lat = -lat
        lon = _to_decimal_degrees(gps_ifd[4])
        if gps_ifd[3] == "W":
            lon = -lon
    except (KeyError, TypeError, ZeroDivisionError):
        return None
    lat_hemisphere = "N" if lat >= 0 else "S"
    lon_hemisphere = "E" if lon >= 0 else "W"
    return f"{abs(lat):.4f}{lat_hemisphere} {abs(lon):.4f}{lon_hemisphere}"


def _to_decimal_degrees(value: tuple) -> float:
    degrees, minutes, seconds = value
    return float(degrees) + float(minutes) / 60.0 + float(seconds) / 3600.0


def _format_device(make: str | None, model: str | None) -> str | None:
    parts = [part.strip() for part in (make, model) if part and part.strip()]
    return " ".join(parts) if parts else None


def _image_filename(page_url: str, image_url: str) -> str:
    domain = urlparse(page_url).netloc.split(":")[0].removeprefix("www.")
    domain_slug = re.sub(r"[^A-Za-z0-9_-]", "_", domain.split(".")[0]) if domain else "site"

    image_name = Path(urlparse(image_url).path).name or "image"
    stem = re.sub(r"[^A-Za-z0-9_-]", "_", Path(image_name).stem) or "image"
    suffix = Path(image_name).suffix or ".jpg"

    return f"{domain_slug}_{stem}{suffix}"


def _unique_destination(images_dir: Path, filename: str) -> Path:
    dest = images_dir / filename
    if not dest.exists():
        return dest
    stem, suffix = Path(filename).stem, Path(filename).suffix
    counter = 2
    while (candidate := images_dir / f"{stem}_{counter}{suffix}").exists():
        counter += 1
    return candidate
