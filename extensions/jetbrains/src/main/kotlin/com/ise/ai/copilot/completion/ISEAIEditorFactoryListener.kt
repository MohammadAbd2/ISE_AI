package com.ise.ai.copilot.completion

import com.intellij.openapi.editor.Editor
import com.intellij.openapi.editor.EditorFactory
import com.intellij.openapi.editor.event.EditorFactoryEvent
import com.intellij.openapi.editor.event.EditorFactoryListener
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.ise.ai.copilot.service.ISEAIService

/**
 * Listener that attaches to editors to provide AI completions.
 */
class ISEAIEditorFactoryListener : EditorFactoryListener {
    override fun editorCreated(event: EditorFactoryEvent) {
        val editor = event.editor
        val project = editor.project ?: return
        
        val service = ISEAIService.getInstance()
        
        // Only enable for supported file types
        val virtualFile = FileDocumentManager.getInstance().getFile(editor.document)
        if (virtualFile == null || !isSupportedFile(virtualFile.name)) {
            return
        }
        
        // Add document listener for auto-completion
        val completionProvider = ISEAICompletionProvider(editor, service)
        editor.document.addDocumentListener(completionProvider)
    }
    
    override fun editorReleased(event: EditorFactoryEvent) {
        // Cleanup if needed
    }
    
    private fun isSupportedFile(fileName: String): Boolean {
        val supportedExtensions = setOf(
            "py", "js", "ts", "jsx", "tsx", 
            "java", "kt", "go", "rs", "cpp", "c", "h", "hpp"
        )
        val extension = fileName.substringAfterLast('.', "")
        return extension in supportedExtensions
    }
}
