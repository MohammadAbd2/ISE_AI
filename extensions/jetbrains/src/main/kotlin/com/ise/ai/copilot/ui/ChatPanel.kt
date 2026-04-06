package com.ise.ai.copilot.ui

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.fileChooser.FileChooser
import com.intellij.openapi.fileChooser.FileChooserDescriptor
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import com.intellij.ui.JBColor
import com.intellij.ui.components.JBScrollPane
import com.intellij.ui.components.JBTextArea
import com.intellij.ui.components.JBTextField
import com.intellij.util.ui.JBUI
import com.ise.ai.copilot.service.ISEAIService
import kotlinx.coroutines.*
import java.awt.*
import java.awt.event.ActionEvent
import java.awt.event.ActionListener
import javax.swing.*
import javax.swing.border.EmptyBorder
import javax.swing.border.CompoundBorder
import javax.swing.border.LineBorder
import javax.swing.text.SimpleAttributeSet
import javax.swing.text.StyleConstants

class ChatPanel(private val project: Project) {
    private val service = ISEAIService.getInstance()
    private val scope = CoroutineScope(Dispatchers.Main.immediate + SupervisorJob())
    
    val mainPanel: JPanel = JPanel(BorderLayout())
    private val chatScrollPane: JBScrollPane
    private val chatContainer = JPanel()
    private val messageInput = JBTextArea().apply {
        lineWrap = true
        wrapStyleWord = true
        border = BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(JBColor.border()),
            EmptyBorder(5, 5, 5, 5)
        )
    }
    private val sendButton = JButton("Send").apply {
        preferredSize = Dimension(80, 32)
    }
    private val cancelButton = JButton("Cancel").apply {
        isVisible = false
        preferredSize = Dimension(80, 32)
    }
    
    // Quick action buttons (like Copilot)
    private val explainButton = JButton("📖 Explain")
    private val refactorButton = JButton("✨ Refactor")
    private val testsButton = JButton("🧪 Tests")
    private val fixButton = JButton("🔧 Fix")
    private val optimizeButton = JButton("⚡ Optimize")
    private val docsButton = JButton("📝 Docs")
    
    // Settings controls
    private val modelSelector = JComboBox(arrayOf("Claude Haiku 4.5", "llama3", "llama2", "mistral")).apply {
        selectedItem = "Claude Haiku 4.5"
        preferredSize = Dimension(150, 24)
    }
    private val modeSelector = JComboBox(arrayOf("auto", "chat", "agent")).apply {
        selectedItem = "auto"
        preferredSize = Dimension(100, 24)
    }
    private val levelSelector = JComboBox(arrayOf("low", "medium", "high")).apply {
        selectedItem = "medium"
        preferredSize = Dimension(100, 24)
    }
    private val loadFileButton = JButton("Load File")
    private val loadProjectButton = JButton("Load Project")
    private val statusLabel = JLabel("Ready")
    
    private val chatLayout = BoxLayout(chatContainer, BoxLayout.Y_AXIS)
    private var currentMessageLabel: JEditorPane? = null
    private var isStreaming = false
    private var loadedContext: String = ""
    private var projectFiles: List<String> = emptyList()
    private var conversationHistory: MutableList<Pair<String, String>> = mutableListOf()

    init {
        setupUI()
        setupActions()
        indexProject()
    }

    private fun setupUI() {
        // Chat container with scroll
        chatContainer.layout = chatLayout
        chatContainer.border = EmptyBorder(10, 10, 10, 10)
        chatContainer.background = JBColor.background()
        
        chatScrollPane = JBScrollPane(chatContainer).apply {
            verticalScrollBarPolicy = JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED
            horizontalScrollBarPolicy = JScrollPane.HORIZONTAL_SCROLLBAR_NEVER
            border = null
        }

        // Quick actions panel
        val quickActionsPanel = JPanel(FlowLayout(FlowLayout.LEFT, 5, 5)).apply {
            border = EmptyBorder(5, 10, 5, 10)
            background = JBColor.background()
            
            add(JLabel("Quick Actions:"))
            add(explainButton)
            add(refactorButton)
            add(testsButton)
            add(fixButton)
            add(optimizeButton)
            add(docsButton)
        }

        // Settings panel
        val settingsPanel = JPanel(GridLayout(2, 3, 8, 5)).apply {
            border = EmptyBorder(10, 10, 5, 10)
            background = JBColor.background()
            
            add(JLabel("Model:"))
            add(modelSelector)
            add(loadFileButton)
            
            add(JLabel("Mode:").apply { horizontalAlignment = SwingConstants.RIGHT })
            add(modeSelector)
            add(loadProjectButton)
            
            add(JLabel("Level:").apply { horizontalAlignment = SwingConstants.RIGHT })
            add(levelSelector)
            add(JLabel(""))
        }

        // Status bar
        val statusPanel = JPanel(BorderLayout()).apply {
            border = EmptyBorder(5, 10, 5, 10)
            background = JBColor.background()
            add(statusLabel, BorderLayout.WEST)
            
            val fileCountLabel = JLabel("").apply {
                if (projectFiles.isNotEmpty()) {
                    text = "📁 ${projectFiles.size} files indexed"
                }
            }
            add(fileCountLabel, BorderLayout.EAST)
        }

        // Input panel
        val inputPanel = JPanel(BorderLayout(10, 0)).apply {
            border = EmptyBorder(10, 10, 10, 10)
            background = JBColor.background()
            
            val inputScrollPane = JBScrollPane(messageInput).apply {
                preferredSize = Dimension(0, 80)
            }
            
            add(inputScrollPane, BorderLayout.CENTER)
            
            val buttonPanel = JPanel(FlowLayout(FlowLayout.RIGHT, 5, 0)).apply {
                add(sendButton)
                add(cancelButton)
            }
            add(buttonPanel, BorderLayout.EAST)
        }

        // Top panel for title
        val topPanel = JPanel(BorderLayout()).apply {
            border = EmptyBorder(10, 10, 5, 10)
            background = JBColor.background()
            add(JLabel("ISE AI Copilot - Powered by Claude Haiku 4.5") {
                font = Font(font.name, Font.BOLD, 13)
            }, BorderLayout.WEST)
        }

        mainPanel.add(topPanel, BorderLayout.NORTH)
        mainPanel.add(chatScrollPane, BorderLayout.CENTER)
        mainPanel.add(settingsPanel, BorderLayout.NORTH)
        mainPanel.add(quickActionsPanel, BorderLayout.PAGE_START)
        mainPanel.add(statusPanel, BorderLayout.SOUTH)
        
        // Create a wrapper for input
        val bottomPanel = JPanel(BorderLayout())
        bottomPanel.add(inputPanel, BorderLayout.CENTER)
        mainPanel.add(bottomPanel, BorderLayout.SOUTH)
    }

    private fun setupActions() {
        sendButton.addActionListener {
            sendMessage()
        }

        cancelButton.addActionListener {
            service.cancelRequest()
            cancelButton.isVisible = false
            sendButton.isVisible = true
            isStreaming = false
            updateStatus("Cancelled")
        }

        messageInput.addKeyListener(object : java.awt.event.KeyAdapter() {
            override fun keyPressed(e: java.awt.event.KeyEvent) {
                if (e.keyCode == java.awt.event.KeyEvent.VK_ENTER && e.isControlDown && !isStreaming) {
                    sendMessage()
                    e.consume()
                }
            }
        })
        
        loadFileButton.addActionListener { loadFile() }
        loadProjectButton.addActionListener { loadProject() }
        
        explainButton.addActionListener {
            val selectedCode = getSelectedCode()
            if (selectedCode.isNotEmpty()) {
                sendMessage("Explain this code:\n```\n$selectedCode\n```")
            } else {
                updateStatus("Please select code to explain")
            }
        }
        
        refactorButton.addActionListener {
            val selectedCode = getSelectedCode()
            if (selectedCode.isNotEmpty()) {
                sendMessage("Refactor this code to be more efficient and maintainable:\n```\n$selectedCode\n```")
            } else {
                updateStatus("Please select code to refactor")
            }
        }
        
        testsButton.addActionListener {
            val selectedCode = getSelectedCode()
            if (selectedCode.isNotEmpty()) {
                sendMessage("Generate comprehensive tests for this code:\n```\n$selectedCode\n```")
            } else {
                updateStatus("Please select code to test")
            }
        }
        
        fixButton.addActionListener {
            val selectedCode = getSelectedCode()
            if (selectedCode.isNotEmpty()) {
                sendMessage("Fix any bugs or issues in this code:\n```\n$selectedCode\n```")
            } else {
                updateStatus("Please select code to fix")
            }
        }
        
        optimizeButton.addActionListener {
            val selectedCode = getSelectedCode()
            if (selectedCode.isNotEmpty()) {
                sendMessage("Optimize this code for performance:\n```\n$selectedCode\n```")
            } else {
                updateStatus("Please select code to optimize")
            }
        }
        
        docsButton.addActionListener {
            val selectedCode = getSelectedCode()
            if (selectedCode.isNotEmpty()) {
                sendMessage("Generate detailed documentation for this code:\n```\n$selectedCode\n```")
            } else {
                updateStatus("Please select code to document")
            }
        }
        
        modelSelector.addActionListener {
            val selected = modelSelector.selectedItem as String
            service.model = when (selected) {
                "Claude Haiku 4.5" -> "claude-haiku-4.5"
                else -> selected.lowercase()
            }
            updateStatus("Model: $selected")
        }
        
        modeSelector.addActionListener {
            service.mode = modeSelector.selectedItem as String
            updateStatus("Mode: ${service.mode}")
        }
        
        levelSelector.addActionListener {
            service.level = levelSelector.selectedItem as String
            updateStatus("Level: ${service.level}")
        }
    }
    
    private fun getSelectedCode(): String {
        val editor = com.intellij.openapi.fileEditor.FileEditorManager.getInstance(project).selectedTextEditor
        if (editor != null && editor.selectionModel.hasSelection()) {
            return editor.selectionModel.selectedText ?: ""
        }
        return ""
    }
    
    private fun indexProject() {
        val projectPath = project.basePath ?: return
        val projectFile = java.io.File(projectPath)
        projectFiles = mutableListOf()
        
        fun traverse(dir: java.io.File, depth: Int = 0) {
            if (depth > 5 || (projectFiles as? MutableList)?.size ?: 0 > 200) return
            
            dir.listFiles()?.forEach { file ->
                if (!file.name.startsWith(".")) {
                    if (file.isFile) {
                        (projectFiles as? MutableList)?.add(file.absolutePath)
                    } else if (file.isDirectory) {
                        traverse(file, depth + 1)
                    }
                }
            }
        }
        
        traverse(projectFile)
        loadedContext = "PROJECT_STRUCTURE: Indexed ${projectFiles.size} files"
    }
    
    private fun loadFile() {
        val descriptor = FileChooserDescriptor(true, false, false, false, false, false)
        descriptor.title = "Load File"
        val virtualFile = FileChooser.chooseFile(descriptor, project, null)
        
        if (virtualFile != null) {
            try {
                val content = String(virtualFile.contentsToByteArray())
                loadedContext = "FILE: ${virtualFile.name}\n```\n$content\n```"
                updateStatus("Loaded: ${virtualFile.name}")
                appendMessage("info", "📄 Loaded file: ${virtualFile.name}")
            } catch (e: Exception) {
                updateStatus("Error loading file: ${e.message}")
            }
        }
    }
    
    private fun loadProject() {
        val descriptor = FileChooserDescriptor(false, true, false, false, false, false)
        descriptor.title = "Load Project Folder"
        val virtualFile = FileChooser.chooseFile(descriptor, project, null)
        
        if (virtualFile != null) {
            try {
                val fileSummary = StringBuilder()
                fileSummary.append("PROJECT: ${virtualFile.name}\n")
                var fileCount = 0
                
                fun traverseFiles(vf: com.intellij.openapi.vfs.VirtualFile, indent: String = "") {
                    if (fileCount > 50) return
                    
                    if (!vf.isDirectory) {
                        fileSummary.append("$indent${vf.name}\n")
                        fileCount++
                    } else {
                        fileSummary.append("$indent${vf.name}/\n")
                        vf.children.forEach { child ->
                            if (!child.name.startsWith(".")) {
                                traverseFiles(child, "$indent  ")
                            }
                        }
                    }
                }
                
                traverseFiles(virtualFile)
                loadedContext = fileSummary.toString()
                updateStatus("Loaded project: ${virtualFile.name} ($fileCount files)")
                appendMessage("info", "📁 Loaded project: ${virtualFile.name}")
            } catch (e: Exception) {
                updateStatus("Error loading project: ${e.message}")
            }
        }
    }
    
    private fun updateStatus(text: String) {
        statusLabel.text = text
    }

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

        // Get editor context
        val context = getEditorContext()
        val requestModel = service.model
        val requestMode = service.mode
        val requestLevel = service.level

        // Send request using IDE's application thread context
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
                    service.streamRequest(message, context, requestModel, requestMode, requestLevel) { chunk ->
                        // Update UI on EDT
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
                ApplicationManager.getApplication().invokeLater {
                    appendMessage("info", "⏹️ Request cancelled")
                    sendButton.isVisible = true
                    cancelButton.isVisible = false
                    isStreaming = false
                    updateStatus("Cancelled")
                }
                throw e
            } catch (e: Exception) {
                ApplicationManager.getApplication().invokeLater {
                    appendMessage("error", "❌ Error: ${e.message ?: "Unknown error"}")
                    sendButton.isVisible = true
                    cancelButton.isVisible = false
                    isStreaming = false
                    updateStatus("Error: ${e.message}")
                }
            }
        }
    }

    private fun getEditorContext(): Map<String, Any?> {
        val context = mutableMapOf<String, Any?>()
        
        // Get current editor
        val editor = com.intellij.openapi.fileEditor.FileEditorManager.getInstance(project).selectedTextEditor
        if (editor != null) {
            context["file"] = editor.virtualFile?.path
            context["language"] = editor.virtualFile?.fileType?.name
            context["code"] = editor.document.text
            
            val selectionModel = editor.selectionModel
            if (selectionModel.hasSelection()) {
                context["selection"] = selectionModel.selectedText
            }
        }
        
        // Add loaded context if available
        if (loadedContext.isNotEmpty()) {
            context["loaded_context"] = loadedContext
        }
        
        // Add indexed project files
        if (projectFiles.isNotEmpty()) {
            context["project_files"] = projectFiles.joinToString("\n")
        }
        
        return context
    }

    private fun appendMessage(role: String, content: String) {
        val messagePanel = JPanel(BorderLayout()).apply {
            border = CompoundBorder(
                LineBorder(
                    when (role) {
                        "user" -> JBColor.BLUE
                        "assistant" -> JBColor.GREEN
                        "info" -> Color(100, 150, 200)
                        "error" -> JBColor.RED
                        else -> JBColor.border()
                    },
                    1
                ),
                EmptyBorder(8, 8, 8, 8)
            )
            background = when (role) {
                "user" -> Color(225, 240, 255)
                "assistant" -> Color(225, 250, 225)
                "info" -> Color(230, 240, 250)
                "error" -> Color(255, 230, 230)
                else -> JBColor.background()
            }
            maximumSize = Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE)
        }

        val editorPane = MessageFormatter.createHTMLEditorPane(content)
        editorPane.background = messagePanel.background
        editorPane.foreground = JBColor.foreground()
        
        val scrollPane = JScrollPane(editorPane).apply {
            border = null
            preferredSize = Dimension(400, 100)
        }

        messagePanel.add(scrollPane, BorderLayout.CENTER)
        chatContainer.add(messagePanel)
        chatContainer.add(Box.createVerticalStrut(5))
        
        // Auto-scroll to bottom
        SwingUtilities.invokeLater {
            chatScrollPane.verticalScrollBar.value = chatScrollPane.verticalScrollBar.maximum
        }
    }

    private fun streamAssistantChunk(chunk: String) {
        if (currentMessageLabel == null) {
            val panel = JPanel(BorderLayout()).apply {
                border = CompoundBorder(
                    LineBorder(JBColor.GREEN, 1),
                    EmptyBorder(8, 8, 8, 8)
                )
                background = Color(225, 250, 225)
                maximumSize = Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE)
            }
            
            currentMessageLabel = MessageFormatter.createHTMLEditorPane(chunk)
            currentMessageLabel!!.background = panel.background
            
            val scrollPane = JScrollPane(currentMessageLabel!!).apply {
                border = null
            }
            panel.add(scrollPane, BorderLayout.CENTER)
            chatContainer.add(panel)
        } else {
            currentMessageLabel?.text = MessageFormatter.formatMarkdown(
                (currentMessageLabel?.text?.removePrefix("<html><body style='font-family: system, -apple-system, sans-serif; line-height: 1.6; color: #333;'>")
                    ?.removeSuffix("</body></html>") ?: "") + chunk
            )
        }
        
        SwingUtilities.invokeLater {
            chatScrollPane.verticalScrollBar.value = chatScrollPane.verticalScrollBar.maximum
        }
    }

    private fun finishAssistantMessage(response: String) {
        currentMessageLabel = null
    }

    fun dispose() {
        scope.cancel()
    }
}
    
    private val chatLayout = BoxLayout(chatContainer, BoxLayout.Y_AXIS)
    private var currentMessageLabel: JLabel? = null
    private var isStreaming = false
    private var loadedContext: String = ""

    init {
        setupUI()
        setupActions()
    }

    private fun setupUI() {
        // Chat container with scroll
        chatContainer.layout = chatLayout
        chatContainer.border = EmptyBorder(10, 10, 10, 10)
        chatContainer.background = JBColor.background()
        
        val scrollPane = JBScrollPane(chatContainer).apply {
            verticalScrollBarPolicy = JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED
            horizontalScrollBarPolicy = JScrollPane.HORIZONTAL_SCROLLBAR_NEVER
            border = null
        }

        // Settings panel
        val settingsPanel = JPanel(GridLayout(2, 3, 5, 5)).apply {
            border = EmptyBorder(10, 10, 5, 10)
            background = JBColor.background()
            
            add(JLabel("Model:"))
            add(modelSelector)
            add(loadFileButton)
            
            add(JLabel("Mode:").apply { horizontalAlignment = SwingConstants.RIGHT })
            add(modeSelector)
            add(loadProjectButton)
            
            add(JLabel("Level:").apply { horizontalAlignment = SwingConstants.RIGHT })
            add(levelSelector)
            add(JLabel(""))
        }

        // Status bar
        val statusPanel = JPanel(BorderLayout()).apply {
            border = EmptyBorder(5, 10, 5, 10)
            add(statusLabel, BorderLayout.WEST)
        }

        // Input panel
        val inputPanel = JPanel(BorderLayout(10, 0)).apply {
            border = EmptyBorder(10, 10, 10, 10)
            
            val inputScrollPane = JBScrollPane(messageInput).apply {
                preferredSize = Dimension(0, 80)
            }
            
            add(inputScrollPane, BorderLayout.CENTER)
            
            val buttonPanel = JPanel(FlowLayout(FlowLayout.RIGHT, 5, 0)).apply {
                add(sendButton)
                add(cancelButton)
            }
            add(buttonPanel, BorderLayout.EAST)
        }

        mainPanel.add(scrollPane, BorderLayout.CENTER)
        mainPanel.add(settingsPanel, BorderLayout.NORTH)
        mainPanel.add(statusPanel, BorderLayout.SOUTH)
        
        // Create a wrapper for input and settings
        val bottomPanel = JPanel(BorderLayout())
        bottomPanel.add(inputPanel, BorderLayout.CENTER)
        mainPanel.add(bottomPanel, BorderLayout.SOUTH)
    }

    private fun setupActions() {
        sendButton.addActionListener {
            sendMessage()
        }

        cancelButton.addActionListener {
            service.cancelRequest()
            cancelButton.isVisible = false
            sendButton.isVisible = true
            isStreaming = false
            updateStatus("Cancelled")
        }

        messageInput.addKeyListener(object : java.awt.event.KeyAdapter() {
            override fun keyPressed(e: java.awt.event.KeyEvent) {
                if (e.keyCode == java.awt.event.KeyEvent.VK_ENTER && e.isControlDown && !isStreaming) {
                    sendMessage()
                    e.consume()
                }
            }
        })
        
        loadFileButton.addActionListener {
            loadFile()
        }
        
        loadProjectButton.addActionListener {
            loadProject()
        }
        
        modelSelector.addActionListener {
            service.model = modelSelector.selectedItem as String
            updateStatus("Model: ${service.model}")
        }
        
        modeSelector.addActionListener {
            service.mode = modeSelector.selectedItem as String
            updateStatus("Mode: ${service.mode}")
        }
        
        levelSelector.addActionListener {
            service.level = levelSelector.selectedItem as String
            updateStatus("Level: ${service.level}")
        }
    }
    
    private fun loadFile() {
        val descriptor = FileChooserDescriptor(true, false, false, false, false, false)
        descriptor.title = "Load File"
        val virtualFile = FileChooser.chooseFile(descriptor, project, null)
        
        if (virtualFile != null) {
            try {
                val content = String(virtualFile.contentsToByteArray())
                loadedContext = "FILE: ${virtualFile.name}\n```\n$content\n```"
                updateStatus("Loaded: ${virtualFile.name}")
                appendMessage("info", "Loaded file: ${virtualFile.name}")
            } catch (e: Exception) {
                updateStatus("Error loading file: ${e.message}")
            }
        }
    }
    
    private fun loadProject() {
        val descriptor = FileChooserDescriptor(false, true, false, false, false, false)
        descriptor.title = "Load Project Folder"
        val virtualFile = FileChooser.chooseFile(descriptor, project, null)
        
        if (virtualFile != null) {
            try {
                val fileSummary = StringBuilder()
                fileSummary.append("PROJECT: ${virtualFile.name}\n")
                var fileCount = 0
                
                fun traverseFiles(vf: com.intellij.openapi.vfs.VirtualFile, indent: String = "") {
                    if (fileCount > 50) return // Limit to prevent huge context
                    
                    if (!vf.isDirectory) {
                        fileSummary.append("$indent${vf.name}\n")
                        fileCount++
                    } else {
                        fileSummary.append("$indent${vf.name}/\n")
                        vf.children.forEach { child ->
                            if (!child.name.startsWith(".")) {
                                traverseFiles(child, "$indent  ")
                            }
                        }
                    }
                }
                
                traverseFiles(virtualFile)
                loadedContext = fileSummary.toString()
                updateStatus("Loaded project: ${virtualFile.name} ($fileCount files)")
                appendMessage("info", "Loaded project: ${virtualFile.name}")
            } catch (e: Exception) {
                updateStatus("Error loading project: ${e.message}")
            }
        }
    }
    
    private fun updateStatus(text: String) {
        statusLabel.text = text
    }

    fun sendMessage(text: String? = null) {
        val message = text ?: messageInput.text.trim()
        if (message.isEmpty() || isStreaming) return

        // Add user message
        appendMessage("user", message)
        
        if (text == null) {
            messageInput.text = ""
        }

        // Show cancel button
        sendButton.isVisible = false
        cancelButton.isVisible = true
        isStreaming = true
        updateStatus("Sending...")

        // Get editor context
        val context = getEditorContext()
        val requestModel = service.model
        val requestMode = service.mode
        val requestLevel = service.level

        // Send request using IDE's application thread context
        scope.launch(CoroutineExceptionHandler { _, exception ->
            ApplicationManager.getApplication().invokeLater {
                appendMessage("error", "Error: ${exception.message ?: "Unknown error"}")
                sendButton.isVisible = true
                cancelButton.isVisible = false
                isStreaming = false
                updateStatus("Error: ${exception.message}")
            }
        }) {
            try {
                var response = ""
                
                response = withContext(Dispatchers.IO) {
                    service.streamRequest(message, context, requestModel, requestMode, requestLevel) { chunk ->
                        // Update UI on EDT
                        ApplicationManager.getApplication().invokeLater {
                            streamAssistantChunk(chunk)
                        }
                    }
                }

                // Finalize message
                ApplicationManager.getApplication().invokeLater {
                    finishAssistantMessage(response)
                    sendButton.isVisible = true
                    cancelButton.isVisible = false
                    isStreaming = false
                    updateStatus("Ready")
                }
            } catch (e: CancellationException) {
                ApplicationManager.getApplication().invokeLater {
                    appendMessage("info", "Request cancelled")
                    sendButton.isVisible = true
                    cancelButton.isVisible = false
                    isStreaming = false
                    updateStatus("Cancelled")
                }
                throw e
            } catch (e: Exception) {
                ApplicationManager.getApplication().invokeLater {
                    appendMessage("error", "Error: ${e.message ?: "Unknown error"}")
                    sendButton.isVisible = true
                    cancelButton.isVisible = false
                    isStreaming = false
                    updateStatus("Error: ${e.message}")
                }
            }
        }
    }

    private fun getEditorContext(): Map<String, Any?> {
        val context = mutableMapOf<String, Any?>()
        
        // Get current editor
        val editor = com.intellij.openapi.fileEditor.FileEditorManager.getInstance(project).selectedTextEditor
        if (editor != null) {
            context["file"] = editor.virtualFile?.path
            context["language"] = editor.virtualFile?.fileType?.name
            context["code"] = editor.document.text
            
            val selectionModel = editor.selectionModel
            if (selectionModel.hasSelection()) {
                context["selection"] = selectionModel.selectedText
            }
        }
        
        // Add loaded project context if available
        if (loadedContext.isNotEmpty()) {
            context["loaded_context"] = loadedContext
        }
        
        return context
    }

    private fun appendMessage(role: String, content: String) {
        val messagePanel = JPanel(BorderLayout()).apply {
            border = CompoundBorder(
                LineBorder(
                    when (role) {
                        "user" -> JBColor.BLUE
                        "assistant" -> JBColor.GREEN
                        "info" -> JBColor.GRAY
                        "error" -> JBColor.RED
                        else -> JBColor.border()
                    },
                    2
                ),
                EmptyBorder(8, 8, 8, 8)
            )
            background = when (role) {
                "user" -> JBColor.namedColor("TextField.background", Color(240, 240, 240))
                "assistant" -> JBColor.namedColor("Panel.background", Color(245, 245, 245))
                "info" -> JBColor.namedColor("Panel.background", Color(240, 250, 240))
                "error" -> JBColor.namedColor("Component.errorFocusColor", Color(255, 230, 230))
                else -> JBColor.background()
            }
        }

        val textPane = JTextPane().apply {
            isEditable = false
            background = messagePanel.background
            styledDocument.apply {
                setParagraphAttributes(0, length, SimpleAttributeSet().apply {
                    StyleConstants.setLineSpacing(this, 1.5f)
                }, false)
            }
            
            text = content
        }

        messagePanel.add(JScrollPane(textPane).apply {
            border = null
        }, BorderLayout.CENTER)

        chatContainer.add(messagePanel)
        
        // Auto-scroll to bottom
        SwingUtilities.invokeLater {
            val parent = chatContainer.parent
            if (parent is JScrollPane) {
                parent.verticalScrollBar.value = parent.verticalScrollBar.maximum
            }
        }
    }

    private fun streamAssistantChunk(chunk: String) {
        if (currentMessageLabel == null) {
            val panel = JPanel(BorderLayout()).apply {
                border = CompoundBorder(
                    LineBorder(JBColor.GREEN, 2),
                    EmptyBorder(8, 8, 8, 8)
                )
                background = JBColor.namedColor("Panel.background", Color(245, 245, 245))
            }
            
            currentMessageLabel = JLabel().apply {
                text = chunk
                verticalAlignment = SwingConstants.TOP
            }
            
            panel.add(currentMessageLabel!!, BorderLayout.CENTER)
            chatContainer.add(panel)
        } else {
            currentMessageLabel?.text = currentMessageLabel?.text + chunk
        }
        
        SwingUtilities.invokeLater {
            val parent = chatContainer.parent
            if (parent is JScrollPane) {
                parent.verticalScrollBar.value = parent.verticalScrollBar.maximum
            }
        }
    }

    private fun finishAssistantMessage(response: String) {
        currentMessageLabel = null
    }

    fun dispose() {
        scope.cancel()
    }
}
