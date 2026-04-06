package com.ise.ai.copilot.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.lang.annotation.HighlightSeverity
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.ui.Messages
import com.ise.ai.copilot.service.ISEAIService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class FixErrorsAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val editor = e.getData(com.intellij.openapi.actionSystem.CommonDataKeys.EDITOR)
        val project = e.project ?: return
        val file = e.getData(com.intellij.openapi.actionSystem.CommonDataKeys.VIRTUAL_FILE)
        
        // Get errors in file
        val annotationHolder = com.intellij.codeInsight.daemon.impl.DaemonCodeAnalyzerEx.getInstanceEx(project)
        val errors = mutableListOf<String>()
        
        // Simplified error collection
        val code = editor?.document?.text
        if (code.isNullOrBlank()) {
            Messages.showWarningDialog(project, "No code in current file", "Empty File")
            return
        }
        
        val language = editor.virtualFile?.fileType?.name ?: "unknown"
        val prompt = "Fix these errors in the $language code:\n\n```\n$code\n```"
        
        val service = ISEAIService.getInstance()
        val context = mapOf(
            "file" to file?.path,
            "language" to language,
            "code" to code
        )
        
        CoroutineScope(Dispatchers.Main).launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    service.sendRequest(prompt, context)
                }
                Messages.showInfoMessage(project, response, "Fixed Code")
            } catch (ex: Exception) {
                Messages.showErrorDialog(project, "Error: ${ex.message}", "Error")
            }
        }
    }
}
