import base64
from pathlib import Path

ALLOWED_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class InvalidImageError(Exception):
    pass


def _looks_like_image(data: bytes, mime_type: str) -> bool:
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")

    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")

    if mime_type == "image/webp":
        is_riff = data[0:4] == b"RIFF"
        is_webp = data[8:12] == b"WEBP"
        return is_riff and is_webp

    return False


def image_to_data_url(image_path: str | None, max_mb: int) -> str:
    if not image_path:
        raise InvalidImageError("Please upload a diagram image.")

    file_path = Path(image_path)
    if not file_path.is_file():
        raise InvalidImageError("The uploaded file could not be found.")

    suffix = file_path.suffix.lower()
    mime_type = ALLOWED_TYPES.get(suffix)
    if mime_type is None:
        allowed = ", ".join(ALLOWED_TYPES)
        raise InvalidImageError(
            f"Unsupported file type '{suffix}'. Use one of: {allowed}."
        )

    size_bytes = file_path.stat().st_size
    if size_bytes == 0:
        raise InvalidImageError("The uploaded file is empty.")

    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        size_mb = size_bytes / (1024 * 1024)
        raise InvalidImageError(f"Image is {size_mb:.1f} MB. The limit is {max_mb} MB.")

    data = file_path.read_bytes()
    if not _looks_like_image(data, mime_type):
        raise InvalidImageError("The file content does not match its extension.")

    encoded = base64.b64encode(data).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"
    return data_url