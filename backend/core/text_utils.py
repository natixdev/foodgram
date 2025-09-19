from .constants import PREVIEW_LENGTH


def truncate_with_ellipsis(text: str, max_length: int = PREVIEW_LENGTH) -> str:
    """
    Обрезает текст по длине max_length.

    В конце строки добавляется многоточие если текст был обрезан.
    """
    return (
        text if len(text) <= max_length else f'{text[:max_length]}...'
    )
