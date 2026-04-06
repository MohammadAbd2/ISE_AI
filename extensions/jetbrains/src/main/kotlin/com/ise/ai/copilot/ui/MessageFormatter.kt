package com.ise.ai.copilot.ui

import javax.swing.text.html.HTMLDocument
import javax.swing.text.html.HTMLEditorKit

/**
 * Utility class for markdown and code formatting
 */
object MessageFormatter {
    
    fun formatMarkdown(text: String): String {
        var html = escapeHtml(text)
        
        // Code blocks (```language...```)
        html = html.replace(Regex("```([a-z]*)\n(.*?)\n```", RegexOption.DOT_MATCHES_ALL)) { match ->
            val language = match.groupValues[1].takeIf { it.isNotEmpty() } ?: "plaintext"
            val code = match.groupValues[2]
            "<pre style='background-color: #f5f5f5; padding: 12px; border-radius: 4px; font-family: monospace; overflow-x: auto;'>" +
                    "<span style='color: #999; font-size: 0.9em;'>$language</span><br>" +
                    code +
                    "</pre>"
        }
        
        // Inline code (`code`)
        html = html.replace(Regex("`([^`]+)`")) { match ->
            "<code style='background-color: #f0f0f0; padding: 2px 4px; border-radius: 2px; font-family: monospace;'>${match.groupValues[1]}</code>"
        }
        
        // Bold (**text** or __text__)
        html = html.replace(Regex("\\*\\*([^*]+)\\*\\*")) { match ->
            "<b>${match.groupValues[1]}</b>"
        }
        html = html.replace(Regex("__([^_]+)__")) { match ->
            "<b>${match.groupValues[1]}</b>"
        }
        
        // Italic (*text* or _text_)
        html = html.replace(Regex("\\*([^*]+)\\*")) { match ->
            "<i>${match.groupValues[1]}</i>"
        }
        html = html.replace(Regex("_([^_]+)_")) { match ->
            "<i>${match.groupValues[1]}</i>"
        }
        
        // Headers (# Header)
        html = html.replace(Regex("^# (.+)$", RegexOption.MULTILINE)) { match ->
            "<h2 style='margin-top: 12px; margin-bottom: 8px;'>${match.groupValues[1]}</h2>"
        }
        html = html.replace(Regex("^## (.+)$", RegexOption.MULTILINE)) { match ->
            "<h3 style='margin-top: 10px; margin-bottom: 6px;'>${match.groupValues[1]}</h3>"
        }
        html = html.replace(Regex("^### (.+)$", RegexOption.MULTILINE)) { match ->
            "<h4 style='margin-top: 8px; margin-bottom: 4px;'>${match.groupValues[1]}</h4>"
        }
        
        // Lists (- item or * item)
        html = html.replace(Regex("^- (.+)$", RegexOption.MULTILINE)) { match ->
            "• ${match.groupValues[1]}"
        }
        html = html.replace(Regex("^\\* (.+)$", RegexOption.MULTILINE)) { match ->
            "• ${match.groupValues[1]}"
        }
        
        // Links ([text](url))
        html = html.replace(Regex("\\[([^]]+)]\\(([^)]+)\\)")) { match ->
            "<a href='${match.groupValues[2]}' style='color: #0066cc;'>${match.groupValues[1]}</a>"
        }
        
        // Line breaks
        html = html.replace("\n", "<br>")
        
        return "<html><body style='font-family: system, -apple-system, sans-serif; line-height: 1.6; color: #333;'>$html</body></html>"
    }
    
    fun formatCode(code: String, language: String = "plaintext"): String {
        val html = escapeHtml(code)
        return "<html><body style='background-color: #f5f5f5; padding: 12px; font-family: monospace; line-height: 1.4;'>" +
                "<span style='color: #999;'>$language</span><br>" +
                html.replace("\n", "<br>").replace(" ", "&nbsp;") +
                "</body></html>"
    }
    
    private fun escapeHtml(text: String): String {
        return text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&#39;")
    }
    
    fun createHTMLEditorPane(content: String): javax.swing.JEditorPane {
        return javax.swing.JEditorPane().apply {
            contentType = "text/html"
            text = formatMarkdown(content)
            isEditable = false
            isOpaque = false
        }
    }
}
