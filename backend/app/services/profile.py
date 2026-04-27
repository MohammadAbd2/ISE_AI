import asyncio
from dataclasses import dataclass
from functools import lru_cache
import re
import threading

from app.services.chroma_store import ChromaJSONStore


PROFILE_ID = "assistant_profile"


@dataclass(slots=True)
class MemoryIntent:
    action: str
    query: str | None = None
    entries: list[str] | None = None


def _normalize_lines(text: str) -> list[str]:
    """Store memory as trimmed, non-empty lines."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item.strip())
    return result


def _strip_command_suffix(value: str) -> str:
    cleaned = re.split(
        r"\b(remember|remeber|save|store|memorize|forever|for ever|please)\b",
        value,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return cleaned.strip(" .,:;!-")


def _clean_named_entity(value: str) -> str:
    cleaned = _strip_command_suffix(value)
    # Stop name extraction before the sentence shifts into another clause.
    cleaned = re.split(
        r"\b(?:and|but|while|from now on|also|please|to the memory|to memory|in the memory|in memory|into memory|not)\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return cleaned.strip(" .,:;!-")


def _normalize_intent_text(text: str) -> str:
    normalized = " ".join(text.split()).lower()
    replacements = {
        "displkay": "display",
        "remeber": "remember",
        "memroy": "memory",
        "long term memroy": "long term memory",
    }
    for wrong, correct in replacements.items():
        normalized = normalized.replace(wrong, correct)
    return normalized


def _memory_key(item: str) -> str | None:
    patterns = {
        r"^The user's name is .+$": "user_name",
        r"^The assistant's name is .+$": "assistant_name",
        r"^The assistant's nickname is .+$": "assistant_name",
        r"^The user's cat is named .+$": "user_cat_name",
        r"^The user works at .+$": "user_work_at",
        r"^The user works as .+$": "user_work_as",
        r"^The user prefers .+$": "user_preference",
    }
    for pattern, key in patterns.items():
        if re.match(pattern, item, flags=re.IGNORECASE):
            return key
    return None


class ProfileService:
    def __init__(self, chroma_path: str | None = None, collection_name: str | None = None) -> None:
        self._lock = threading.Lock()
        self._memory_profile = {"_id": PROFILE_ID, "custom_instructions": "", "memory": []}
        self.store = ChromaJSONStore("assistant_profile")

    async def get_profile(self) -> dict:
        return await asyncio.to_thread(self._get_profile_sync)

    def _get_profile_sync(self) -> dict:
        with self._lock:
            document = self.store.get(PROFILE_ID)
            if document is None:
                document = dict(self._memory_profile)
                self.store.upsert(PROFILE_ID, document)
            return document

    async def update_profile(self, custom_instructions: str, memory: str) -> dict:
        return await asyncio.to_thread(
            self._update_profile_sync,
            custom_instructions,
            memory,
        )

    def _update_profile_sync(self, custom_instructions: str, memory: str) -> dict:
        document = {
            "_id": PROFILE_ID,
            "custom_instructions": custom_instructions.strip(),
            "memory": _normalize_lines(memory),
        }
        with self._lock:
            self._memory_profile = document
            self.store.upsert(PROFILE_ID, document)
        return document

    async def remember(self, entry: str) -> None:
        await asyncio.to_thread(self._remember_sync, entry)

    def _remember_sync(self, entry: str) -> None:
        clean = entry.strip()
        if not clean:
            return
        profile = self._get_profile_sync()
        items = [item for item in profile.get("memory", []) if item.strip()]
        incoming_key = _memory_key(clean)
        if incoming_key:
            items = [item for item in items if _memory_key(item) != incoming_key]
        items.append(clean)
        normalized = _dedupe_keep_order(items)
        self._update_profile_sync(
            profile.get("custom_instructions", ""),
            "\n".join(normalized),
        )

    async def remember_many(self, entries: list[str]) -> list[str]:
        return await asyncio.to_thread(self._remember_many_sync, entries)

    def _remember_many_sync(self, entries: list[str]) -> list[str]:
        saved: list[str] = []
        for entry in entries:
            clean = entry.strip()
            if not clean:
                continue
            self._remember_sync(clean)
            saved.append(clean)
        return _dedupe_keep_order(saved)

    async def forget(self, query: str) -> bool:
        return await asyncio.to_thread(self._forget_sync, query)

    def _forget_sync(self, query: str) -> bool:
        profile = self._get_profile_sync()
        items = profile.get("memory", [])
        lowered = query.strip().lower()
        remaining = [item for item in items if lowered not in item.lower()]
        changed = len(remaining) != len(items)
        if changed:
            self._update_profile_sync(
                profile.get("custom_instructions", ""),
                "\n".join(remaining),
            )
        return changed

    async def forget_all(self) -> None:
        profile = await self.get_profile()
        await self.update_profile(profile.get("custom_instructions", ""), "")

    def storage_mode(self) -> str:
        return "chromadb" if self.store.is_persistent else "memory"


def detect_memory_command(text: str) -> tuple[str | None, str | None]:
    """Detect simple natural-language commands for memory management."""
    value = text.strip()
    lower = value.lower()
    if "forget everything" in lower or "forget all" in lower or "clear memory" in lower:
        return "forget_all", None

    remember_patterns = [
        r"remember that (.+)",
        r"remember this (.+)",
        r"save this (.+)",
        r"save that (.+)",
        r"store this (.+)",
        r"memorize this (.+)",
        r"please remember (.+)",
    ]
    for pattern in remember_patterns:
        match = re.search(pattern, lower)
        if match:
            start = match.start(1)
            return "remember", value[start:].strip(" .")

    forget_patterns = [
        r"forget that (.+)",
        r"forget this (.+)",
        r"forget (.+)",
        r"remove from memory (.+)",
    ]
    for pattern in forget_patterns:
        match = re.search(pattern, lower)
        if match:
            start = match.start(1)
            return "forget", value[start:].strip(" .")

    return None, None


def parse_memory_intent(text: str) -> MemoryIntent | None:
    """Extract higher-level memory intents from natural-language requests."""
    value = " ".join(text.split())
    lower = _normalize_intent_text(value)

    show_phrases = [
        "show memory",
        "display memory",
        "list memory",
        "show long term memory",
        "show the long term memory",
        "show me the long term memory",
        "display the memory",
        "display the memory for me",
        "display the long term memory",
        "display long term memory",
        "list the long term memory",
        "what do you remember",
        "what is in memory",
        "what's in memory",
        "show me the memory",
        "show me memory",
        "show me the long-term memory",
    ]
    if any(phrase in lower for phrase in show_phrases):
        return MemoryIntent(action="show")

    forget_patterns = [
        r"\bforget\s+(?:the memory about\s+|memory about\s+|that\s+|this\s+)?(.+)",
        r"\bdelete\s+(?:the memory about\s+|memory about\s+)?(.+)",
        r"\bremove\s+(?:from memory\s+|the memory about\s+)?(.+)",
    ]
    for pattern in forget_patterns:
        match = re.search(pattern, lower, flags=re.IGNORECASE)
        if match:
            query = _strip_command_suffix(match.group(1))
            if query and "memory" not in query.lower():
                return MemoryIntent(action="forget", query=query)

    clear_patterns = [
        r"^\s*clear(?: the)? memory\s*$",
        r"^\s*delete(?: the)? memory\s*$",
        r"^\s*erase memory\s*$",
        r"^\s*remove all memory\s*$",
        r"^\s*delete all memory\s*$",
        r"^\s*forget everything\s*$",
        r"^\s*forget all\s*$",
        r"^\s*delete all (?:the )?data in (?:the )?long[- ]term memory\s*$",
        r"^\s*clear all (?:the )?data in (?:the )?long[- ]term memory\s*$",
        r"^\s*delete everything in (?:the )?long[- ]term memory\s*$",
        r"^\s*clear (?:the )?long[- ]term memory\s*$",
        r"^\s*delete (?:the )?long[- ]term memory\s*$",
    ]
    if any(re.search(pattern, lower) for pattern in clear_patterns):
        return MemoryIntent(action="forget_all")

    remember_markers = ["remember", "remeber", "save", "store", "memorize"]
    if any(marker in lower for marker in remember_markers):
        entries = extract_helpful_memory(value)
        if not entries:
            proposition = _strip_command_suffix(value)
            proposition = re.sub(
                r"\b(please\s+)?(remember|remeber|save|store|memorize)(?:\s+(this|that))?\b",
                "",
                proposition,
                flags=re.IGNORECASE,
            ).strip(" .,:;!-")
            if proposition:
                entries = [proposition]
        if entries:
            return MemoryIntent(action="remember", entries=entries)

    return None


def is_confirmation(text: str) -> bool:
    return text.strip().lower() in {"yes", "y", "yes please", "confirm", "confirmed", "do it"}


def is_rejection(text: str) -> bool:
    return text.strip().lower() in {"no", "n", "cancel", "stop", "never mind", "nevermind"}


def extract_helpful_memory(text: str, existing_memory: list[str] | None = None) -> list[str]:
    """Capture a few useful profile facts without requiring explicit commands."""
    findings: list[str] = []
    existing_memory = existing_memory or []
    stripped = " ".join(text.split())

    name_match = re.search(
        r"\bmy name(?: is)?\s+([A-Za-z][A-Za-z\s'-]{0,60})",
        stripped,
        flags=re.IGNORECASE,
    )
    if name_match:
        raw_name = _clean_named_entity(name_match.group(1).split(",")[0].strip())
        if raw_name:
            findings.append(f"The user's name is {raw_name}.")

    assistant_name_match = re.search(
        r"\b(?:your name is(?: now)?|your new name is|your new name which is|your name now is|your name from now on is|you name now is|i will call you|i want to call you|you are now called)\s+([A-Za-z][A-Za-z\s'-]{0,60})",
        stripped,
        flags=re.IGNORECASE,
    )
    if assistant_name_match:
        raw_name = _clean_named_entity(assistant_name_match.group(1).split(",")[0].strip())
        if raw_name:
            findings.append(f"The assistant's name is {raw_name}.")

    assistant_nickname_match = re.search(
        r"\b(?:your nickname is|i will call you by the nickname|your nick name is)\s+([A-Za-z][A-Za-z\s'-]{0,60})",
        stripped,
        flags=re.IGNORECASE,
    )
    if assistant_nickname_match:
        raw_name = _clean_named_entity(assistant_nickname_match.group(1).split(",")[0].strip())
        if raw_name:
            findings.append(f"The assistant's nickname is {raw_name}.")

    cat_name_match = re.search(
        r"\bmy cat(?:'s)? name is\s+([A-Za-z][A-Za-z\s'-]{0,40})",
        stripped,
        flags=re.IGNORECASE,
    )
    if cat_name_match:
        raw_name = _clean_named_entity(cat_name_match.group(1).split(",")[0].strip())
        findings.append(f"The user's cat is named {raw_name}.")

    cat_name_change_match = re.search(
        r"\b(?:i have changed|i changed|change|updated?) (?:the )?cat(?:'s)? name (?:to be|to|is now)\s+([A-Za-z][A-Za-z\s'-]{0,40})",
        stripped,
        flags=re.IGNORECASE,
    )
    if cat_name_change_match:
        raw_name = _clean_named_entity(cat_name_change_match.group(1).split(",")[0].strip())
        findings.append(f"The user's cat is named {raw_name}.")

    cat_name_now_match = re.search(
        r"\bmy cat(?:'s)? name (?:is now|changed to|changed to be)\s+([A-Za-z][A-Za-z\s'-]{0,40})",
        stripped,
        flags=re.IGNORECASE,
    )
    if cat_name_now_match:
        raw_name = _clean_named_entity(cat_name_now_match.group(1).split(",")[0].strip())
        findings.append(f"The user's cat is named {raw_name}.")

    generic_cat_name_match = re.search(
        r"\b(?:the )?cat(?:'s)? name(?: is| to be| to| changed to| changed to be)?\s+([A-Za-z][A-Za-z\s'-]{0,40})",
        stripped,
        flags=re.IGNORECASE,
    )
    if generic_cat_name_match:
        raw_name = _clean_named_entity(generic_cat_name_match.group(1).split(",")[0].strip())
        findings.append(f"The user's cat is named {raw_name}.")

    pronoun_cat_name_match = re.search(
        r"\b(?:i have changed|i changed|change|updated?) (?:her|his) name (?:to be|to|is now)\s+([A-Za-z][A-Za-z\s'-]{0,40})",
        stripped,
        flags=re.IGNORECASE,
    )
    if pronoun_cat_name_match and any(_memory_key(item) == "user_cat_name" for item in existing_memory):
        raw_name = _clean_named_entity(pronoun_cat_name_match.group(1).split(",")[0].strip())
        findings.append(f"The user's cat is named {raw_name}.")

    structured_user_name_match = re.search(
        r"\bthe user's name is\s+([A-Za-z][A-Za-z\s'-]{0,60})",
        stripped,
        flags=re.IGNORECASE,
    )
    if structured_user_name_match:
        raw_name = _clean_named_entity(structured_user_name_match.group(1).split(",")[0].strip())
        if raw_name:
            findings.append(f"The user's name is {raw_name}.")

    structured_assistant_name_match = re.search(
        r"\bthe assistant's name is\s+([A-Za-z][A-Za-z\s'-]{0,60})",
        stripped,
        flags=re.IGNORECASE,
    )
    if structured_assistant_name_match:
        raw_name = _clean_named_entity(structured_assistant_name_match.group(1).split(",")[0].strip())
        if raw_name:
            findings.append(f"The assistant's name is {raw_name}.")

    structured_cat_name_match = re.search(
        r"\bthe user's cat is named\s+([A-Za-z][A-Za-z\s'-]{0,40})",
        stripped,
        flags=re.IGNORECASE,
    )
    if structured_cat_name_match:
        raw_name = _clean_named_entity(structured_cat_name_match.group(1).split(",")[0].strip())
        if raw_name:
            findings.append(f"The user's cat is named {raw_name}.")

    prefer_match = re.search(
        r"\bi prefer\s+([^.!?,\n]+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if prefer_match:
        findings.append(f"The user prefers {_strip_command_suffix(prefer_match.group(1).strip())}.")

    work_at_match = re.search(
        r"\bi work at\s+([^.!?,\n]+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if work_at_match:
        findings.append(f"The user works at {_strip_command_suffix(work_at_match.group(1).strip())}.")

    work_as_match = re.search(
        r"\bi work as\s+([^.!?,\n]+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if work_as_match:
        findings.append(f"The user works as {_strip_command_suffix(work_as_match.group(1).strip())}.")

    use_match = re.search(
        r"\bi use\s+([^.!?,\n]+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if use_match:
        findings.append(f"The user uses {_strip_command_suffix(use_match.group(1).strip())}.")

    favorite_match = re.search(
        r"\bmy favorite\s+([^.!?,\n]+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if favorite_match:
        findings.append(f"The user's favorite {_strip_command_suffix(favorite_match.group(1).strip())}.")

    return _dedupe_keep_order(findings)


@lru_cache
def get_profile_service() -> ProfileService:
    """Reuse one profile service instance across requests."""
    return ProfileService()
