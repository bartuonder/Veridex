from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    index: int
    character_start: int
    text: str


def split_document(
    document_text: str,
    chunk_characters: int,
    overlap_characters: int,
) -> list[DocumentChunk]:
    if overlap_characters >= chunk_characters:
        raise ValueError("overlap_characters must be smaller than chunk_characters")

    chunks: list[DocumentChunk] = []
    step = chunk_characters - overlap_characters
    text_length = len(document_text)
    start = 0
    index = 0

    while start < text_length:
        chunks.append(
            DocumentChunk(
                index=index,
                character_start=start,
                text=document_text[start : start + chunk_characters],
            )
        )
        if start + chunk_characters >= text_length:
            break
        start += step
        index += 1

    return chunks


def locate_chunk_index(chunks: list[DocumentChunk], character_position: int) -> int:
    for chunk in reversed(chunks):
        if chunk.character_start <= character_position:
            return chunk.index
    return 0
