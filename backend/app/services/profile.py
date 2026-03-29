import asyncio
from functools import lru_cache
import re
import threading

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app.core.config import settings


PROFILE_ID = "assistant_profile"


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


class ProfileService:
    def __init__(self, mongo_uri: str, db_name: str) -> None:
        self._lock = threading.Lock()
        self._memory_profile = {
            "_id": PROFILE_ID,
            "custom_instructions": "",
            "memory": [],
        }
        self._mongo_available = True
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=1500)
            client.admin.command("ping")
            self.collection = client[db_name]["assistant_profile"]
        except PyMongoError:
            # Use the in-process profile when MongoDB is offline.
            self.collection = None
            self._mongo_available = False

    async def get_profile(self) -> dict:
        return await asyncio.to_thread(self._get_profile_sync)

    def _get_profile_sync(self) -> dict:
        if not self._mongo_available or self.collection is None:
            with self._lock:
                return dict(self._memory_profile)
        try:
            document = self.collection.find_one({"_id": PROFILE_ID})
            if document is None:
                document = dict(self._memory_profile)
                self.collection.insert_one(document)
            return document
        except PyMongoError:
            self._mongo_available = False
            return self._get_profile_sync()

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
        if not self._mongo_available or self.collection is None:
            with self._lock:
                self._memory_profile = document
            return document
        try:
            self.collection.update_one(
                {"_id": PROFILE_ID},
                {"$set": document},
                upsert=True,
            )
            return document
        except PyMongoError:
            self._mongo_available = False
            with self._lock:
                self._memory_profile = document
            return document

    async def remember(self, entry: str) -> None:
        await asyncio.to_thread(self._remember_sync, entry)

    def _remember_sync(self, entry: str) -> None:
        clean = entry.strip()
        if not clean:
            return
        profile = self._get_profile_sync()
        items = [item for item in profile.get("memory", []) if item.strip()]
        items.append(clean)
        normalized = _dedupe_keep_order(items)
        self._update_profile_sync(
            profile.get("custom_instructions", ""),
            "\n".join(normalized),
        )

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
        return "mongodb" if self._mongo_available and self.collection is not None else "memory"


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


def extract_helpful_memory(text: str) -> list[str]:
    """Capture a few useful profile facts without requiring explicit commands."""
    findings: list[str] = []
    stripped = " ".join(text.split())

    name_match = re.search(
        r"\bmy name is\s+([A-Za-z][A-Za-z\s'-]{0,40})",
        stripped,
        flags=re.IGNORECASE,
    )
    if name_match:
        raw_name = name_match.group(1).split(",")[0].strip()
        findings.append(f"The user's name is {raw_name}.")

    prefer_match = re.search(
        r"\bi prefer\s+([^.!?,\n]+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if prefer_match:
        findings.append(f"The user prefers {prefer_match.group(1).strip()}.")

    work_at_match = re.search(
        r"\bi work at\s+([^.!?,\n]+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if work_at_match:
        findings.append(f"The user works at {work_at_match.group(1).strip()}.")

    work_as_match = re.search(
        r"\bi work as\s+([^.!?,\n]+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if work_as_match:
        findings.append(f"The user works as {work_as_match.group(1).strip()}.")

    use_match = re.search(
        r"\bi use\s+([^.!?,\n]+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if use_match:
        findings.append(f"The user uses {use_match.group(1).strip()}.")

    favorite_match = re.search(
        r"\bmy favorite\s+([^.!?,\n]+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if favorite_match:
        findings.append(f"The user's favorite {favorite_match.group(1).strip()}.")

    return _dedupe_keep_order(findings)


@lru_cache
def get_profile_service() -> ProfileService:
    """Reuse one profile service instance across requests."""
    return ProfileService(
        mongo_uri=settings.mongo_uri,
        db_name=settings.mongo_db_name,
    )
