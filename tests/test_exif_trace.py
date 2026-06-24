import io
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import ExifTags, Image

from cleantrace import exif_trace

HTML = """
<html>
  <body>
    <img src="/avatar.jpg">
    <img src="https://cdn.example.com/banner.png">
    <img src="/avatar.jpg">
  </body>
</html>
"""


def _jpeg_bytes(exif: Image.Exif | None = None) -> bytes:
    image = Image.new("RGB", (4, 4), color="red")
    buffer = io.BytesIO()
    if exif:
        image.save(buffer, format="JPEG", exif=exif)
    else:
        image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _exif_with_gps_and_device() -> Image.Exif:
    image = Image.new("RGB", (4, 4))
    exif = image.getexif()
    exif[ExifTags.Base.Make] = "Apple"
    exif[ExifTags.Base.Model] = "iPhone 12"
    exif[ExifTags.Base.DateTimeOriginal] = "2023:07:14 10:00:00"
    exif[ExifTags.IFD.GPSInfo] = {
        1: "N",
        2: (52.0, 18.0, 0.0),
        3: "E",
        4: (4.0, 54.0, 0.0),
    }
    return exif


def test_find_images_dedupes_and_resolves_relative_urls() -> None:
    urls = exif_trace.find_images(HTML, "https://example.com/profile")

    assert urls == [
        "https://example.com/avatar.jpg",
        "https://cdn.example.com/banner.png",
    ]


def test_format_gps() -> None:
    gps_ifd = {1: "N", 2: (52.0, 18.0, 0.0), 3: "E", 4: (4.0, 54.0, 0.0)}
    assert exif_trace._format_gps(gps_ifd) == "52.3000N 4.9000E"


def test_format_gps_missing() -> None:
    assert exif_trace._format_gps(None) is None
    assert exif_trace._format_gps({}) is None


def test_format_device() -> None:
    assert exif_trace._format_device("Apple", "iPhone 12") == "Apple iPhone 12"
    assert exif_trace._format_device(None, None) is None


def test_image_filename() -> None:
    name = exif_trace._image_filename(
        "https://example.com/profile", "https://example.com/img/photo.jpg"
    )
    assert name == "example_photo.jpg"


def test_process_page_images_saves_exif_and_drops_no_exif(tmp_path: Path) -> None:
    exif_bytes = _jpeg_bytes(_exif_with_gps_and_device())
    no_exif_bytes = _jpeg_bytes()

    def fake_get(url, headers, timeout):
        if "avatar" in url:
            return Mock(status_code=200, content=exif_bytes)
        if "banner" in url:
            return Mock(status_code=200, content=no_exif_bytes)
        return Mock(status_code=404, content=b"")

    images_dir = tmp_path / "someone_images"
    with patch("cleantrace.exif_trace.requests.get", side_effect=fake_get):
        results = exif_trace.process_page_images(
            "https://example.com/profile", HTML, images_dir, 10
        )

    by_url = {r["url"]: r for r in results}
    exif_result = by_url["https://example.com/avatar.jpg"]
    assert exif_result["status"] == "exif"
    assert exif_result["gps"] == "52.3000N 4.9000E"
    assert exif_result["device"] == "Apple iPhone 12"
    assert Path(exif_result["saved_path"]).exists()

    no_exif_result = by_url["https://cdn.example.com/banner.png"]
    assert no_exif_result["status"] == "no_exif"
    assert "saved_path" not in no_exif_result

    assert list(images_dir.glob("*")) == [Path(exif_result["saved_path"])]
    assert not list(tmp_path.glob("tmp*"))


def test_process_page_images_handles_download_failure(tmp_path: Path) -> None:
    with patch(
        "cleantrace.exif_trace.requests.get",
        return_value=Mock(status_code=404, content=b""),
    ):
        results = exif_trace.process_page_images(
            "https://example.com/profile", HTML, tmp_path / "images", 10
        )

    assert all(r["status"] == "error" for r in results)
    assert not (tmp_path / "images").exists()
