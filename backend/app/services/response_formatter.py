"""
Professional Response Formatter

Creates human-like, professional responses similar to ChatGPT, Claude, and Codex.

Key improvements:
- Natural, conversational tone
- Well-structured with clear sections
- Professional formatting (not robotic)
- Contextual explanations
- Actionable summaries
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ResponseSection:
    """A section of the response."""
    title: str
    content: str
    icon: str = ""


class ProfessionalResponseFormatter:
    """
    Formats agent responses to be professional and human-like.
    
    Inspired by ChatGPT, Claude, and professional documentation.
    """
    
    def __init__(self):
        self.sections = []
        self.summary = ""
        self.action_items = []
    
    def add_section(self, title: str, content: str, icon: str = ""):
        """Add a section to the response."""
        self.sections.append(ResponseSection(title, content, icon))
    
    def set_summary(self, summary: str):
        """Set the main summary/conclusion."""
        self.summary = summary
    
    def add_action_item(self, item: str):
        """Add an action item or next step."""
        self.action_items.append(item)
    
    def format(self) -> str:
        """Format the complete response."""
        parts = []
        
        # Summary first (if exists)
        if self.summary:
            parts.append(self.summary)
            parts.append("")
        
        # Sections
        for section in self.sections:
            icon = section.icon + " " if section.icon else ""
            parts.append(f"**{icon}{section.title}**")
            parts.append("")
            parts.append(section.content)
            parts.append("")
        
        # Action items
        if self.action_items:
            parts.append("**📌 Next Steps:**")
            parts.append("")
            for i, item in enumerate(self.action_items, 1):
                parts.append(f"{i}. {item}")
            parts.append("")
        
        return "\n".join(parts)
    
    @classmethod
    def from_task_result(cls, task: str, result: dict) -> 'ProfessionalResponseFormatter':
        """Create a professional response from a task result."""
        formatter = cls()
        
        # Determine response type and format accordingly
        if result.get("type") == "code_generation":
            formatter._format_code_generation(task, result)
        elif result.get("type") == "question_answer":
            formatter._format_question_answer(task, result)
        elif result.get("type") == "debug_analysis":
            formatter._format_debug_analysis(task, result)
        elif result.get("type") == "explanation":
            formatter._format_explanation(task, result)
        else:
            formatter._format_generic_task(task, result)
        
        return formatter
    
    def _format_code_generation(self, task: str, result: dict):
        """Format code generation response."""
        files_modified = result.get("files_modified", [])
        code_snippet = result.get("code_snippet", "")
        explanation = result.get("explanation", "")
        
        # Summary
        self.set_summary(
            f"تم إنشاء الكود بنجاح! " if len(files_modified) > 0 else "Here's what I created:"
        )
        
        # Files section
        if files_modified:
            files_content = "\n".join([f"• `{f}`" for f in files_modified])
            self.add_section(
                "📁 Files Created/Modified",
                files_content,
                "📁"
            )
        
        # Code explanation
        if explanation:
            self.add_section(
                "💡 How It Works",
                explanation,
                "💡"
            )
        
        # Code snippet (if provided)
        if code_snippet:
            self.add_section(
                "📝 Code Preview",
                f"```\n{code_snippet[:500]}{'...' if len(code_snippet) > 500 else ''}\n```",
                "📝"
            )
        
        # Usage example
        self.add_action_item("Review the generated code")
        self.add_action_item("Test the functionality")
        if len(files_modified) > 1:
            self.add_action_item("Check that imports are correctly set up")
    
    def _format_question_answer(self, task: str, result: dict):
        """Format Q&A response (like ChatGPT style)."""
        answer = result.get("answer", "")
        key_points = result.get("key_points", [])
        examples = result.get("examples", [])
        
        # Direct answer first
        if answer:
            self.set_summary(answer)
        
        # Key points
        if key_points:
            points_formatted = "\n".join([f"{i+1}. {point}" for i, point in enumerate(key_points)])
            self.add_section(
                "النقاط الرئيسية" if any(ord(c) > 127 for c in points_formatted) else "Key Points",
                points_formatted,
                "📊"
            )
        
        # Examples
        if examples:
            examples_formatted = "\n\n".join([f"```{ex}```" for ex in examples])
            self.add_section(
                "أمثلة" if any(ord(c) > 127 for c in examples_formatted) else "Examples",
                examples_formatted,
                "💡"
            )
    
    def _format_debug_analysis(self, task: str, result: dict):
        """Format debug/error analysis response."""
        error_type = result.get("error_type", "Error")
        error_location = result.get("location", "Unknown")
        explanation = result.get("explanation", "")
        solution = result.get("solution", "")
        
        # Summary
        self.set_summary(f"❌ Found {error_type} in {error_location}")
        
        # Error details
        self.add_section(
            "🔍 Error Analysis",
            explanation,
            "🔍"
        )
        
        # Solution
        self.add_section(
            "✅ Solution",
            solution,
            "✅"
        )
        
        # Action items
        self.add_action_item("Review the error location")
        self.add_action_item("Apply the suggested fix")
        self.add_action_item("Run tests to verify")
    
    def _format_explanation(self, task: str, result: dict):
        """Format detailed explanation response."""
        content = result.get("content", "")
        sections = result.get("sections", [])
        
        # Main content
        self.set_summary(content)
        
        # Additional sections
        for section in sections:
            self.add_section(
                section.get("title", "Details"),
                section.get("content", ""),
                section.get("icon", "📌")
            )
    
    def _format_generic_task(self, task: str, result: dict):
        """Format generic task response."""
        # Simple professional format
        summary = result.get("summary", f"✅ Task completed: {task}")
        details = result.get("details", "")
        
        self.set_summary(summary)
        
        if details:
            self.add_section("Details", details, "📋")


def format_chat_response(message: str, context: dict) -> str:
    """
    Format a chat response to be more conversational and professional.
    
    Similar to how ChatGPT/Claude respond.
    """
    formatter = ProfessionalResponseFormatter()
    
    # Detect response type
    if any(word in message.lower() for word in ["create", "write", "generate", "implement"]):
        # Code generation task
        formatter.set_summary("✅ تم الإنشاء بنجاح!" if any(ord(c) > 127 for c in message) else "✅ Successfully created!")
        
        formatter.add_section(
            "What I Did",
            message,
            "🔨"
        )
    else:
        # Regular conversation
        formatter.set_summary(message)
    
    return formatter.format()


# Quick formatting functions for common scenarios

def format_file_created(file_path: str, description: str = "") -> str:
    """Format 'file created' response."""
    return f"""
✅ **File Created Successfully**

📁 **Location:** `{file_path}`

{description if description else "The file has been created with the requested functionality."}

**Next Steps:**
1. Review the generated code
2. Import it where needed
3. Test the functionality
"""


def format_file_modified(file_path: str, changes: list[str]) -> str:
    """Format 'file modified' response."""
    changes_list = "\n".join([f"• {change}" for change in changes])
    
    return f"""
✏️ **File Updated**

📁 **File:** `{file_path}`

**Changes Made:**
{changes_list}

**Next Steps:**
1. Review the changes
2. Test that existing functionality still works
3. Commit the changes if satisfied
"""


def format_error_found(error_type: str, location: str, solution: str) -> str:
    """Format error analysis response."""
    return f"""
🔍 **Error Analysis**

❌ **Error Type:** {error_type}
📍 **Location:** {location}

**What's Wrong:**
The error occurs because of a mismatch in the expected behavior.

**✅ Solution:**
{solution}

**Next Steps:**
1. Apply the fix above
2. Run your code to verify
3. Add tests to prevent regression
"""


def format_explanation_response(topic: str, content: str, key_points: list[str]) -> str:
    """Format explanation/Q&A response (ChatGPT style)."""
    points = "\n".join([f"{i+1}. {point}" for i, point in enumerate(key_points)])
    
    return f"""
💡 **{topic}**

{content}

**📊 Key Points:**

{points}

---

*Need more details? Feel free to ask follow-up questions!*
"""


def format_code_with_explanation(code: str, explanation: str, language: str = "python") -> str:
    """Format code with explanation."""
    return f"""
💡 **Implementation**

{explanation}

**📝 Code:**

```{language}
{code}
```

**How to Use:**
1. Copy the code above
2. Paste it into your project
3. Adjust as needed for your specific use case
"""
