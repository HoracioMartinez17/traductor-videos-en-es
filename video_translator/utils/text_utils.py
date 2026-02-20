def split_text(text: str, max_length: int = 500) -> list[str]:
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]
