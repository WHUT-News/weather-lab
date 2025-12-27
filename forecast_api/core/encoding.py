"""
Unicode text encoding/decoding utilities.

Supports multiple encodings for internationalization without compression.
"""

from typing import Tuple

# Supported encodings
SUPPORTED_ENCODINGS = {
    'utf-8': 'Universal (recommended for most languages)',
    'utf-16': 'Better for Asian languages (Chinese, Japanese, Korean)',
    'utf-32': 'Fixed-width unicode (less common)',
}


def encode_text(text: str, encoding: str = 'utf-8') -> Tuple[bytes, int, str]:
    """
    Encode text to bytes for storage with unicode support.

    Args:
        text: Unicode text string (supports all languages)
        encoding: Text encoding ('utf-8', 'utf-16', 'utf-32')

    Returns:
        Tuple of (encoded_bytes, size_bytes, encoding_used)

    Examples:
        >>> # English text
        >>> encode_text("Weather in Chicago: Sunny, 75°F")

        >>> # Spanish text with accents
        >>> encode_text("El clima en México: Soleado, 24°C")

        >>> # Chinese text
        >>> encode_text("北京天气：晴朗，摄氏24度", encoding='utf-16')

        >>> # Japanese text
        >>> encode_text("東京の天気：晴れ、摂氏24度", encoding='utf-16')

        >>> # Emoji support
        >>> encode_text("Weather: ☀️ Sunny, 🌡️ 75°F")
    """
    # Validate encoding
    if encoding not in SUPPORTED_ENCODINGS:
        raise ValueError(
            f"Unsupported encoding: {encoding}. "
            f"Supported: {list(SUPPORTED_ENCODINGS.keys())}"
        )

    # Encode text to bytes with specified encoding
    try:
        text_bytes = text.encode(encoding)
    except UnicodeEncodeError as e:
        raise ValueError(
            f"Cannot encode text with {encoding}. "
            f"Consider using utf-8 or utf-16. Error: {e}"
        )

    size_bytes = len(text_bytes)

    return text_bytes, size_bytes, encoding


def decode_text(text_bytes: bytes, encoding: str = 'utf-8') -> str:
    """
    Decode text from storage with unicode support.

    Args:
        text_bytes: Binary data
        encoding: Text encoding used during encoding

    Returns:
        Decoded unicode text string

    Raises:
        UnicodeDecodeError: If encoding doesn't match stored encoding
    """
    # Decode with proper encoding
    try:
        return text_bytes.decode(encoding)
    except UnicodeDecodeError as e:
        # Fallback attempt with error handling
        try:
            return text_bytes.decode(encoding, errors='replace')
        except Exception:
            raise ValueError(
                f"Cannot decode text with {encoding}. "
                f"Data may be corrupted. Error: {e}"
            )


def detect_optimal_encoding(text: str) -> str:
    """
    Detect optimal encoding for given text.

    Args:
        text: Unicode text string

    Returns:
        Recommended encoding ('utf-8' or 'utf-16')

    Logic:
        - Most text: utf-8 (efficient for ASCII/Latin/Cyrillic)
        - Heavy CJK (Chinese/Japanese/Korean): utf-16 might be better
        - Mixed: utf-8 is universal
    """
    # Check for CJK characters
    cjk_count = sum(1 for char in text if '\u4e00' <= char <= '\u9fff' or  # Chinese
                                          '\u3040' <= char <= '\u309f' or  # Hiragana
                                          '\u30a0' <= char <= '\u30ff' or  # Katakana
                                          '\uac00' <= char <= '\ud7af')    # Hangul

    total_chars = len(text)

    # If >50% CJK characters, utf-16 might be more efficient
    if total_chars > 0 and (cjk_count / total_chars) > 0.5:
        return 'utf-16'

    # Default to utf-8 (universal)
    return 'utf-8'
