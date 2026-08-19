import re


def clean_for_speech(text: str, max_chars: int = 2000) -> str:
    """Strip non-prose content and markdown formatting. Speak text only."""
    # Remove code blocks and tables silently (no placeholders)
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`]+`", lambda m: m.group(0).strip("`") if len(m.group(0)) < 30 else "", text)
    text = re.sub(r"\|[^\n]+\|", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-|:]+\s*$", "", text, flags=re.MULTILINE)

    # Remove file paths
    text = re.sub(r"(/[\w./\-]+){3,}", "", text)

    # Remove URLs
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)

    # Strip markdown formatting (keep the text content)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"~~(.+?)~~", r"\1", text)

    # Strip list markers and blockquotes
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)

    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"  +", " ", text)
    text = text.strip()

    if len(text) > max_chars:
        cut = text[:max_chars].rsplit(". ", 1)
        text = cut[0] + "." if len(cut) > 1 else text[:max_chars]

    return text


def should_speak(text: str, max_chars: int = 2000) -> tuple[bool, str]:
    """Extract prose from a response and decide if there's enough to speak.

    Rules: speak all prose. Silently remove code and tables. If no prose remains, don't speak.
    """
    cleaned = clean_for_speech(text, max_chars=max_chars)
    if len(cleaned) < 10:
        return False, ""
    return True, cleaned


def detect_language(text: str) -> str:
    """Simple Spanish vs English detection. Defaults to Spanish (primary user language)."""
    t = f" {text.lower()} "
    spanish_chars = sum(1 for c in text if c in "áéíóúñ¿¡üÁÉÍÓÚÑ")
    spanish_words = sum(1 for w in [
        "está", "para", "como", "esto", "esta", "puede", "tiene", "desde",
        "pero", "también", "ahora", "todo", "bien", "hola", "listo",
        "quiero", "hacer", "vamos", "aquí", "algo", "solo", "nuevo",
        "porque", "cuando", "donde", "cómo", "qué", "más", "muy",
        "ya", "del", "las", "los", "una", "ese", "esa", "por",
    ] if f" {w} " in t)
    english_words = sum(1 for w in [
        "the", "is", "are", "was", "were", "have", "has", "this",
        "that", "with", "from", "your", "they", "would", "should",
        "could", "which", "their", "about", "been", "into",
    ] if f" {w} " in t)
    if spanish_chars > 0 or spanish_words > english_words:
        return "es"
    if english_words > 0:
        return "en"
    return "es"
