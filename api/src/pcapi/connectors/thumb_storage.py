from pcapi import settings
from pcapi.core import object_storage
from pcapi.models import Model
from pcapi.utils.image_conversion import IMAGE_RATIO_PORTRAIT_DEFAULT
from pcapi.utils.image_conversion import process_original_image
from pcapi.utils.image_conversion import standardize_image


def create_thumb(
    model_with_thumb: Model,  # type: ignore [valid-type]
    image_as_bytes: bytes,
    image_index: int,
    crop_params: tuple = None,
    ratio: float = IMAGE_RATIO_PORTRAIT_DEFAULT,
    keep_ratio: bool = False,
) -> None:
    if keep_ratio:
        image_as_bytes = process_original_image(image_as_bytes)
    else:
        image_as_bytes = standardize_image(image_as_bytes, ratio=ratio, crop_params=crop_params)  # type: ignore [arg-type]

    object_storage.store_public_object(
        folder=settings.THUMBS_FOLDER_NAME,
        object_id=model_with_thumb.get_thumb_storage_id(image_index),  # type: ignore [attr-defined]
        blob=image_as_bytes,
        content_type="image/jpeg",
    )


def remove_thumb(
    model_with_thumb: Model,  # type: ignore [valid-type]
    image_index: int,
) -> None:
    object_storage.delete_public_object(
        folder="thumbs",
        object_id=model_with_thumb.get_thumb_storage_id(image_index),  # type: ignore [attr-defined]
    )
