from dataclasses import dataclass
import re


@dataclass(slots=True)
class TaskIntent:
    kind: str
    confidence: float
    use_agent: bool = False
    use_visualization: bool = False
    use_research: bool = False
    use_project_context: bool = False
    use_filesystem: bool = False


class IntentClassifier:
    """Central request classifier shared by chat and orchestration layers."""

    VISUAL_TERMS = (
        "chart", "diagram", "graph", "plot", "visualize", "visualise", "2d", "3d",
        "map", "globe", "scatter", "bar chart", "line chart", "salary data",
        "profit data", "revenue data", "excel", "spreadsheet",
    )
    VISUAL_CODE_TERMS = (
        "component", "file", "code", "react", "jsx", "tsx", "python", "api",
        "endpoint", "build the chart", "create chart component", "write chart code",
    )
    RESEARCH_TERMS = (
        "search", "search the", "search for", "search on", "find on the web",
        "latest", "recent", "today", "news", "research", "look up",
        "sources", "compare", "citation",
    )
    PROJECT_TERMS = (
        "project", "repo", "repository", "zip", "archive", "codebase", "folder",
        "analyze files", "analyse files", "read the project", "inspect files",
    )
    FILESYSTEM_TERMS = (
        "how many files", "how many folders", "how many directories",
        "count files", "count folders", "count directories",
        "list files", "list folders", "list directories",
        "files in", "folders in", "directories in",
        "what files", "what folders", "what directories",
        "show files", "show folders", "show directories",
        "file structure", "folder structure", "directory structure",
        "tests folder", "tests directory", "tests folder",
        "src folder", "src directory", "src folder",
        "backend folder", "backend directory", "backend folder",
        "frontend folder", "frontend directory", "frontend folder",
        "content of", "read file", "display the content",
        "search in files", "search for", "find in files",
        "replace in files", "search and replace", "find and replace",
        "file tree", "project tree", "directory tree",
    )
    CODING_TERMS = (
        "create file", "write file", "save to", "edit file", "update file", "delete file",
        "modify", "fix", "debug", "refactor", "implement", "add endpoint", "add route",
        "install", "run tests", "write tests", "create component", "update component",
        "create a file", "write a file", "make a file", "new file",
    )
    CHAT_TERMS = (
        "what is", "explain", "tell me", "describe", "why", "how does", "review this",
        "analyze this", "analyse this", "show in chat", "just answer",
    )

    def classify(self, message: str, mode: str = "auto") -> TaskIntent:
        lower = message.lower().strip()

        if mode == "agent":
            return TaskIntent(kind="coding", confidence=1.0, use_agent=True)
        if mode == "chat":
            return self._classify_auto(lower, force_chat=True)
        return self._classify_auto(lower, force_chat=False)

    def _classify_auto(self, lower: str, force_chat: bool) -> TaskIntent:
        if self._is_visualization(lower):
            return TaskIntent(
                kind="visualization",
                confidence=0.88,
                use_visualization=True,
            )

        # Check filesystem queries FIRST (highest priority for file counting/listing)
        if self._is_filesystem_query(lower):
            return TaskIntent(
                kind="filesystem",
                confidence=0.92,
                use_project_context=True,
                use_filesystem=True,
            )

        if any(term in lower for term in self.RESEARCH_TERMS):
            return TaskIntent(kind="research", confidence=0.8, use_research=True)

        if any(term in lower for term in self.PROJECT_TERMS):
            return TaskIntent(
                kind="project_analysis",
                confidence=0.82,
                use_project_context=True,
            )

        if not force_chat and self._is_coding(lower):
            return TaskIntent(kind="coding", confidence=0.84, use_agent=True)

        if any(term in lower for term in self.CHAT_TERMS):
            return TaskIntent(kind="chat", confidence=0.76)

        if re.search(r"(frontend|backend|src|app|components|utils|api)/[\w/\.-]+", lower):
            return TaskIntent(kind="coding", confidence=0.85, use_agent=True)

        return TaskIntent(kind="chat", confidence=0.55)

    def _is_visualization(self, lower: str) -> bool:
        return any(term in lower for term in self.VISUAL_TERMS) and not any(
            term in lower for term in self.VISUAL_CODE_TERMS
        )

    def _is_filesystem_query(self, lower: str) -> bool:
        return any(term in lower for term in self.FILESYSTEM_TERMS)

    def _is_coding(self, lower: str) -> bool:
        return any(term in lower for term in self.CODING_TERMS)


_classifier: IntentClassifier | None = None


def get_intent_classifier() -> IntentClassifier:
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier
