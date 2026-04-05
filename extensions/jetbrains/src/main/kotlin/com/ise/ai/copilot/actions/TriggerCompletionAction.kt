package com.ise.ai.copilot.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import com.intellij.openapi.ui.Messages
import com.ise.ai.copilot.service.ISEAIService

/**
 * Action to trigger AI code completion at cursor position.
 */
class TriggerCompletionAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        val document = editor.document
        val caretModel = editor.caretModel
        val offset = caretModel.offset
        
        val service = ISEAIService.getInstance()
        
        // Get text before and after cursor
        val prefix = document.text.substring(0, offset)
        val suffix = document.text.substring(offset)
        
        // Show completion in background task
        ProgressManager.getInstance().run(object : Task.Backgroundable(
            project, 
            "Getting AI Completion...", 
            true
        ) {
            override fun run(indicator: ProgressIndicator) {
                indicator.isIndeterminate = true
                indicator.text = "Requesting AI completion..."
                
                try {
                    val completion = service.getCompletion(prefix, suffix)
                    
                    if (!completion.isNullOrEmpty()) {
                        // Apply completion on EDT
                        com.intellij.openapi.application.ApplicationManager.getApplication().invokeLater {
                            com.intellij.openapi.command.WriteCommandAction.runWriteCommandAction(project) {
                                document.insertString(offset, completion)
                            }
                        }
                    } else {
                        com.intellij.openapi.application.ApplicationManager.getApplication().invokeLater {
                            Messages.showInfoMessage(
                                project,
                                "No completion available",
                                "ISE AI Copilot"
                            )
                        }
                    }
                } catch (ex: Exception) {
                    com.intellij.openapi.application.ApplicationManager.getApplication().invokeLater {
                        Messages.showErrorDialog(
                            project,
                            "Error getting completion: ${ex.message}",
                            "ISE AI Copilot"
                        )
                    }
                }
            }
        })
    }
    
    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabledAndVisible = editor != null
    }
}
