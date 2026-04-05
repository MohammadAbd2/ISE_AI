package com.ise.ai.copilot.completion

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.editor.Document
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.editor.event.DocumentEvent
import com.intellij.openapi.editor.event.DocumentListener
import com.ise.ai.copilot.service.ISEAIService
import kotlinx.coroutines.*
import javax.swing.Timer

/**
 * Provides AI-powered code completions as user types.
 */
class ISEAICompletionProvider(
    private val editor: Editor,
    private val service: ISEAIService
) : DocumentListener {
    
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var debounceTimer: Timer? = null
    private var lastCompletion: String = ""
    
    companion object {
        private const val DEBOUNCE_DELAY_MS = 500
        private const val MIN_PREFIX_LENGTH = 3
    }
    
    override fun documentChanged(event: DocumentEvent) {
        // Debounce completion requests
        debounceTimer?.stop()
        
        debounceTimer = Timer(DEBOUNCE_DELAY_MS) {
            requestCompletion(event.document, event.offset)
        }.apply {
            isRepeats = false
            start()
        }
    }
    
    private fun requestCompletion(document: Document, offset: Int) {
        val text = document.text
        if (offset < MIN_PREFIX_LENGTH) return
        
        val prefix = text.substring(0, offset)
        val suffix = text.substring(offset)
        
        // Only request if there's meaningful prefix
        if (prefix.trim().length < MIN_PREFIX_LENGTH) return
        
        scope.launch {
            try {
                val completion = withContext(Dispatchers.IO) {
                    service.getCompletion(prefix, suffix)
                }
                
                if (!completion.isNullOrEmpty()) {
                    lastCompletion = completion
                    // Show completion as ghost text (future enhancement)
                    // For now, just log it
                    println("AI Completion: $completion")
                }
            } catch (e: Exception) {
                // Silently ignore completion errors
            }
        }
    }
    
    fun dispose() {
        debounceTimer?.stop()
        scope.cancel()
    }
}
