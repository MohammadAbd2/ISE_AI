package com.ise.ai.copilot.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.wm.ToolWindowManager
import com.ise.ai.copilot.service.ISEAIService
import com.ise.ai.copilot.ui.ChatPanel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class InlineChatAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val editor = e.getData(com.intellij.openapi.actionSystem.CommonDataKeys.EDITOR)
        
        val selectedText = editor?.selectionModel?.selectedText
        
        val message = Messages.showInputDialog(
            project,
            "Ask ISE AI:",
            "ISE AI Inline Chat",
            Messages.getQuestionIcon(),
            selectedText?.take(50),
            null
        )
        
        if (message != null && message.isNotBlank()) {
            // Open chat and send message
            val toolWindowManager = ToolWindowManager.getInstance(project)
            val toolWindow = toolWindowManager.getToolWindow("ISE AI Copilot")
            
            // Get context
            val context = mutableMapOf<String, Any?>()
            if (editor != null) {
                context["file"] = editor.virtualFile?.path
                context["language"] = editor.virtualFile?.fileType?.name
                context["code"] = editor.document.text
                if (selectedText != null) {
                    context["selection"] = selectedText
                }
            }
            
            // Send request to service
            val service = ISEAIService.getInstance()
            CoroutineScope(Dispatchers.Default).launch {
                try {
                    val response = withContext(Dispatchers.IO) {
                        service.sendRequest(message, context)
                    }
                    Messages.showInfoMessage(project, response, "ISE AI Response")
                } catch (ex: Exception) {
                    Messages.showErrorDialog(project, "Error: ${ex.message}", "Error")
                }
            }
        }
    }
}
