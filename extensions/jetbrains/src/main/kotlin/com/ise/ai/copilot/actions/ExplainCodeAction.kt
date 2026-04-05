package com.ise.ai.copilot.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.wm.ToolWindowManager
import com.ise.ai.copilot.service.ISEAIService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ExplainCodeAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val editor = e.getData(com.intellij.openapi.actionSystem.CommonDataKeys.EDITOR)
        val project = e.project ?: return
        
        val selectedText = editor?.selectionModel?.selectedText
        if (selectedText.isNullOrBlank()) {
            Messages.showWarningDialog(project, "Please select code to explain", "No Selection")
            return
        }
        
        val language = editor.virtualFile?.fileType?.name ?: "unknown"
        val prompt = "Explain this $language code:\n\n```\n$selectedText\n```"
        
        val service = ISEAIService.getInstance()
        val context = mapOf(
            "file" to editor.virtualFile?.path,
            "language" to language,
            "code" to editor.document.text,
            "selection" to selectedText
        )
        
        CoroutineScope(Dispatchers.Main).launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    service.sendRequest(prompt, context).await()
                }
                Messages.showInfoMessage(project, response, "Code Explanation")
            } catch (ex: Exception) {
                Messages.showErrorDialog(project, "Error: ${ex.message}", "Error")
            }
        }
    }
}
