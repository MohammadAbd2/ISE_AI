/**
 * Integration guide for using ProjectService with ChatPanel
 * 
 * This shows how to properly integrate project awareness into the chat panel
 */

package com.ise.ai.copilot.ui

import com.intellij.openapi.project.Project
import com.ise.ai.copilot.service.ProjectService
import com.ise.ai.copilot.service.ISEAIService

/**
 * Example: Update ChatPanel to use ProjectService
 * 
 * In ChatPanel class initialization:
 */

// Add to ChatPanel class
private val projectService = ProjectService(project)

// Update sendMessage() method to include project context:
/*
fun sendMessage(text: String? = null) {
    val message = text ?: messageInput.text.trim()
    if (message.isEmpty() || isStreaming) return

    // Add user message
    appendMessage("user", message)
    conversationHistory.add("user" to message)
    
    if (text == null) {
        messageInput.text = ""
    }

    // Show cancel button
    sendButton.isVisible = false
    cancelButton.isVisible = true
    isStreaming = true
    updateStatus("Sending...")

    // Get editor context + project context
    val editorContext = getEditorContext()
    val projectContext = projectService.getProjectContext()
    val mergedContext = editorContext + projectContext  // Merge contexts
    
    val requestModel = service.model
    val requestMode = service.mode
    val requestEffort = service.effort

    // Send request with project context
    scope.launch(CoroutineExceptionHandler { _, exception ->
        ApplicationManager.getApplication().invokeLater {
            appendMessage("error", "❌ Error: ${exception.message ?: "Unknown error"}")
            sendButton.isVisible = true
            cancelButton.isVisible = false
            isStreaming = false
            updateStatus("Error: ${exception.message}")
        }
    }) {
        try {
            var response = ""
            
            response = withContext(Dispatchers.IO) {
                service.streamRequest(
                    message, 
                    context = mergedContext,  // Pass merged context
                    model = requestModel, 
                    mode = requestMode, 
                    effort = requestEffort
                ) { chunk ->
                    ApplicationManager.getApplication().invokeLater {
                        streamAssistantChunk(chunk)
                    }
                }
            }

            // Finalize message
            ApplicationManager.getApplication().invokeLater {
                finishAssistantMessage(response)
                conversationHistory.add("assistant" to response)
                sendButton.isVisible = true
                cancelButton.isVisible = false
                isStreaming = false
                updateStatus("Ready")
            }
        } catch (e: CancellationException) {
            // ... error handling
        } catch (e: Exception) {
            // ... error handling
        }
    }
}
*/

/**
 * Example: Adding project analysis features to quick action buttons
 */

/*
// Add to setupUI() method, in quick actions panel setup:

val analyzeProjectButton = JButton("🔍 Analyze").apply {
    toolTipText = "Analyze current project"
}

analyzeProjectButton.addActionListener {
    val projectInfo = projectService.getProjectContext()
    val projectStats = projectService.getFileStats()
    
    val analysisPrompt = """
        Please analyze this project:
        
        Project: ${projectInfo["project_name"]}
        Path: ${projectInfo["project_path"]}
        
        Statistics:
        ${projectStats.toString()}
        
        What frameworks, languages, and patterns does this project use?
        What are potential improvements?
    """.trimIndent()
    
    sendMessage(analysisPrompt)
}

quickActionsPanel.add(analyzeProjectButton)
*/

/**
 * Example: File-specific operations
 */

/*
// In editor selection handler:

refactorButton.addActionListener {
    val selectedCode = getSelectedCode()
    val currentFile = FileEditorManager.getInstance(project).selectedTextEditor?.virtualFile
    
    if (selectedCode.isNotEmpty() && currentFile != null) {
        val fileContent = projectService.readFile(currentFile.path)
        
        val refactorPrompt = """
            File: ${currentFile.name}
            
            Current code section:
            ```
            $selectedCode
            ```
            
            Please refactor this to:
            - Be more efficient
            - Use better patterns
            - Improve readability
            - Add proper typing
        """.trimIndent()
        
        sendMessage(refactorPrompt)
    }
}
*/

/**
 * Example: Search functionality
 */

/*
// Add method to ChatPanel:

private fun searchAndShow(query: String) {
    val results = projectService.searchFiles(query)
    
    val searchResults = buildString {
        appendLine("Search results for: $query")
        appendLine("Found ${results.size} files:")
        results.forEach { file ->
            appendLine("- ${file["path"]} (${file["size"]} bytes)")
        }
    }
    
    appendMessage("info", searchResults)
    sendMessage("Here are the files matching '$query' in the project")
}
*/
