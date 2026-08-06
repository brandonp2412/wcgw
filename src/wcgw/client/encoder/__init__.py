import math
from typing import Protocol, TypeVar

T = TypeVar("T")

CHARS_PER_TOKEN = 3


class EncoderDecoder(Protocol[T]):
    def encoder(self, text: str) -> list[T]: ...

    def decoder(self, tokens: list[T]) -> str: ...


def estimate_tokens(text: str) -> int:
    """Estimate token count assuming ~3 characters per token."""
    return math.ceil(len(text) / CHARS_PER_TOKEN)


class CharCountEncoder:
    """Character based token estimator (~3 chars per token).

    Each estimated token encodes a chunk of the original text, so truncating
    the token list and decoding it back yields a valid truncated text.
    """

    def encoder(self, text: str) -> list[int]:
        n = len(text)
        ntokens = estimate_tokens(text)
        if ntokens == 0:
            return []
        base, remainder = divmod(n, ntokens)
        tokens: list[int] = []
        i = 0
        for t in range(ntokens):
            size = base + (1 if t < remainder else 0)
            chunk = text[i : i + size]
            i += size
            # Prefix a non-zero byte so the byte length is unambiguously
            # recoverable from the int value.
            tokens.append(int.from_bytes(b"\x01" + chunk.encode("utf-8"), "big"))
        return tokens

    def decoder(self, tokens: list[int]) -> str:
        parts: list[str] = []
        for token in tokens:
            nbytes = (token.bit_length() + 7) // 8
            parts.append(
                token.to_bytes(nbytes, "big")[1:].decode("utf-8", errors="replace")
            )
        return "".join(parts)


def get_default_encoder() -> EncoderDecoder[int]:
    return CharCountEncoder()