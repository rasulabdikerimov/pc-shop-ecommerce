import os
from django.core.exceptions import ValidationError


ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def validate_image_upload(file_obj):
    """Validate uploaded image extension and file size."""
    if not file_obj:
        return
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file extension '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}."
        )
    if hasattr(file_obj, 'size') and file_obj.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("Image file size cannot exceed 5 MB.")

