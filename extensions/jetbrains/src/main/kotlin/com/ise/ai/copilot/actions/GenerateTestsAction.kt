package com.ise.ai.copilot.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.ui.Messages
import com.ise.ai.copilot.service.ISEAIService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class GenerateTestsAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val editor = e.getData(com.intellij.openapi.actionSystem.CommonDataKeys.EDITOR)
        val project = e.project ?: return
        
        val code = editor?.document?.text
        if (code.isNullOrBlank()) {
            Messages.showWarningDialog(project, "No code in current file", "Empty File")
            return
        }
        
        val language = editor.virtualFile?.fileType?.name ?: "unknown"
        val prompt = "Generate comprehensive unit tests for this $language code:\n\n```\n$code\n```"
        
        val service = ISEAIService.getInstance()
        val context = mapOf(
            "file" to editor.virtualFile?.path,
            "language" to language,
            "code" to code
        )
        
        CoroutineScope(Dispatchers.Default).launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    service.sendRequest(prompt, context)
                }
                Messages.showInfoMessage(project, response, "Generated Tests")
            } catch (ex: Exception) {
                Messages.showErrorDialog(project, "Error: ${ex.message}", "Error")
            }
        }
    }
}
