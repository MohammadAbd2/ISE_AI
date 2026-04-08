package com.ise.ai.copilot.ui

import javax.swing.text.html.HTMLDocument
import javax.swing.text.html.HTMLEditorKit
import com.intellij.ui.JBColor
import java.awt.Color

/**
 * Utility class for markdown and code formatting
 * IMPORTANT: Only escape HTML once! Backend sends plain text, not pre-escaped HTML
 */
object MessageFormatter {
    
    private val darkBg = "#1e1e1e"
    private val darkText = "#e0e0e0"
    private val codeBg = "#2d2d2d"
    private val codeText = "#d4d4d4"
    private val accentColor = "#0d66fd"
    private val langColor = "#808080"
    
    fun formatMarkdown(text: String): String {
        // CRITICAL: Don't decode - text should be plain text from backend
        // If it contains &amp;lt; etc., that means it was already escaped twice
        var html = if (isAlreadyEncoded(text)) {
            // Detect and prevent double encoding
            decodeHtml(text)
        } else {
            text
        }
        
        html = escapeHtml(html)
        
        // Code blocks (```language...```)
        html = html.replace(Regex("```([a-z]*)\n(.*?)\n```", RegexOption.DOT_MATCHES_ALL)) { match ->
            val language = match.groupValues[1].takeIf { it.isNotEmpty() } ?: "plaintext"
            val code = match.groupValues[2]
            "<pre style='background-color: $codeBg; color: $codeText; padding: 12px; border-radius: 4px; font-family: monospace; overflow-x: auto; border-left: 3px solid $accentColor;'>" +
                    "<span style='color: $langColor; font-size: 0.9em;'>$language</span><br>" +
                    code +
                    "</pre>"
        }
        
        // Inline code (`code`)
        html = html.replace(Regex("`([^`]+)`")) { match ->
            "<code style='background-color: $codeBg; color: $codeText; padding: 2px 4px; border-radius: 2px; font-family: monospace;'>${match.groupValues[1]}</code>"
        }
        
        // Bold (**text** or __text__)
        html = html.replace(Regex("\\*\\*([^*]+)\\*\\*")) { match ->
            "<b style='color: #ffffff;'>${match.groupValues[1]}</b>"
        }
        html = html.replace(Regex("__([^_]+)__")) { match ->
            "<b style='color: #ffffff;'>${match.groupValues[1]}</b>"
        }
        
        // Italic (*text* or _text_)
        html = html.replace(Regex("\\*([^*]+)\\*")) { match ->
            "<i style='color: #b0b0b0;'>${match.groupValues[1]}</i>"
        }
        html = html.replace(Regex("_([^_]+)_")) { match ->
            "<i style='color: #b0b0b0;'>${match.groupValues[1]}</i>"
        }
        
        // Headers (# Header)
        html = html.replace(Regex("^# (.+)$", RegexOption.MULTILINE)) { match ->
            "<h2 style='margin-top: 12px; margin-bottom: 8px; color: #ffffff;'>${match.groupValues[1]}</h2>"
        }
        html = html.replace(Regex("^## (.+)$", RegexOption.MULTILINE)) { match ->
            "<h3 style='margin-top: 10px; margin-bottom: 6px; color: #f0f0f0;'>${match.groupValues[1]}</h3>"
        }
        html = html.replace(Regex("^### (.+)$", RegexOption.MULTILINE)) { match ->
            "<h4 style='margin-top: 8px; margin-bottom: 4px; color: #e0e0e0;'>${match.groupValues[1]}</h4>"
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
            "<a href='${match.groupValues[2]}' style='color: $accentColor; text-decoration: none;'>${match.groupValues[1]}</a>"
        }
        
        // Line breaks
        html = html.replace("\n", "<br>")
        
        return "<html><body style='font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif; line-height: 1.6; color: $darkText; background-color: $darkBg;'>$html</body></html>"
    }
    
    fun formatCode(code: String, language: String = "plaintext"): String {
        val html = escapeHtml(code)
        return "<html><body style='background-color: $codeBg; color: $codeText; padding: 12px; font-family: monospace; line-height: 1.4; border-left: 3px solid $accentColor;'>" +
                "<span style='color: $langColor;'>$language</span><br>" +
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
    
    private fun isAlreadyEncoded(text: String): Boolean {
        // Check if text contains multiple levels of encoding
        return text.contains("&amp;lt;") || text.contains("&amp;gt;") || 
               text.contains("&amp;quot;") || text.contains("&amp;#39;") ||
               text.contains("&amp;amp;")
    }
    
    private fun decodeHtml(text: String): String {
        var decoded = text
        // Only decode once
        decoded = decoded.replace("&amp;", "&")
        decoded = decoded.replace("&lt;", "<")
        decoded = decoded.replace("&gt;", ">")
        decoded = decoded.replace("&quot;", "\"")
        decoded = decoded.replace("&#39;", "'")
        return decoded
    }
    
    fun createHTMLEditorPane(content: String): javax.swing.JEditorPane {
        return javax.swing.JEditorPane().apply {
            contentType = "text/html"
            text = formatMarkdown(content)
            isEditable = false
            isOpaque = true
            background = JBColor(Color(30, 30, 30), Color(30, 30, 30))
            foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
        }
    }
}
