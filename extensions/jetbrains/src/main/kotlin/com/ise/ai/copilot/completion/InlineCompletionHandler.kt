package com.ise.ai.copilot.completion

import com.intellij.openapi.editor.Editor
import com.intellij.openapi.editor.colors.EditorColorsManager
import com.intellij.openapi.editor.markup.InlayHint
import com.intellij.openapi.editor.markup.InlayHintsSink
import com.intellij.openapi.project.Project
import com.ise.ai.copilot.service.ISEAIService
import kotlinx.coroutines.*
import javax.swing.JLabel

/**
 * Handles inline code completions like GitHub Copilot
 */
class InlineCompletionHandler(private val project: Project) {
    private val service = ISEAIService.getInstance()
    private val scope = CoroutineScope(Dispatchers.Main.immediate + SupervisorJob())
    private var currentInlay: InlayHint? = null
    
    fun getCompletion(editor: Editor, offset: Int, context: String): String? {
        var result: String? = null
        
        scope.launch(Dispatchers.IO) {
            try {
                // Get surrounding code for context
                val document = editor.document
                val lineNumber = document.getLineNumber(offset)
                val lineStartOffset = document.getLineStartOffset(lineNumber)
                val lineEndOffset = document.getLineEndOffset(lineNumber)
                
                val prefix = document.getText(lineStartOffset until offset)
                val suffix = document.getText(offset until lineEndOffset)
                
                val completionPrompt = """Complete this code. Provide ONLY the completion that should come next, no explanations.
Prefix:
$prefix

Suffix:
$suffix

Completion:"""
                
                result = service.getCompletion(prefix, suffix)
            } catch (e: Exception) {
                // Silently fail for inline completions
            }
        }
        
        return result
    }
    
    fun showInlineCompletion(editor: Editor, offset: Int, completion: String) {
        try {
            val inlayModel = editor.inlayModel
            val inlay = inlayModel.addAfterLineEndElement(
                offset,
                false,
                JLabel(completion).apply {
                    foreground = EditorColorsManager.getInstance().globalScheme.getColor(
                        com.intellij.openapi.editor.colors.CodeInsightColors.INLINE_HINT_ATTRIBUTES
                    )?.foreground ?: java.awt.Color.GRAY
                    isOpaque = false
                    text = completion
                }
            )
            currentInlay = inlay
        } catch (e: Exception) {
            // Fail gracefully if inlay system not available
        }
    }
    
    fun dismissInlineCompletion() {
        currentInlay?.dispose()
        currentInlay = null
    }
    
    fun dispose() {
        dismissInlineCompletion()
        scope.cancel()
    }
}
