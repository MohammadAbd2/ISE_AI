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
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    
    val mainPanel: JPanel = JPanel(BorderLayout())
    private lateinit var chatScrollPane: JBScrollPane
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
    private val modelSelector = JComboBox(arrayOf("llama3", "llama3.2:3b", "qwen:7b", "qwen2.5:7b")).apply {
        selectedItem = "llama3"
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
    private var currentMessageText: String = ""
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
        chatContainer.background = JBColor(Color(30, 30, 30), Color(30, 30, 30))
        
        chatScrollPane = JBScrollPane(chatContainer).apply {
            verticalScrollBarPolicy = JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED
            horizontalScrollBarPolicy = JScrollPane.HORIZONTAL_SCROLLBAR_NEVER
            border = null
            background = JBColor(Color(30, 30, 30), Color(30, 30, 30))
            viewport.background = JBColor(Color(30, 30, 30), Color(30, 30, 30))
        }

        // Quick actions panel
        val quickActionsPanel = JPanel(FlowLayout(FlowLayout.LEFT, 5, 5)).apply {
            border = EmptyBorder(5, 10, 5, 10)
            background = JBColor(Color(40, 40, 40), Color(40, 40, 40))
            
            add(JLabel("Quick Actions:").apply {
                foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
                font = Font(font.name, Font.BOLD, 11)
            })
            
            arrayOf(explainButton, refactorButton, testsButton, fixButton, optimizeButton, docsButton).forEach { btn ->
                btn.apply {
                    background = JBColor(Color(60, 60, 60), Color(60, 60, 60))
                    foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
                    border = BorderFactory.createCompoundBorder(
                        BorderFactory.createLineBorder(JBColor(Color(80, 80, 80), Color(80, 80, 80))),
                        EmptyBorder(4, 8, 4, 8)
                    )
                    isContentAreaFilled = true
                }
                add(btn)
            }
        }

        // Settings panel
        val settingsPanel = JPanel(GridLayout(2, 3, 8, 5)).apply {
            border = EmptyBorder(10, 10, 5, 10)
            background = JBColor(Color(40, 40, 40), Color(40, 40, 40))
            
            add(JLabel("Model:").apply { foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224)) })
            add(modelSelector.apply {
                background = JBColor(Color(60, 60, 60), Color(60, 60, 60))
                foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
                border = BorderFactory.createLineBorder(JBColor(Color(80, 80, 80), Color(80, 80, 80)))
            })
            add(loadFileButton.apply {
                background = JBColor(Color(60, 60, 60), Color(60, 60, 60))
                foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
                border = BorderFactory.createCompoundBorder(
                    BorderFactory.createLineBorder(JBColor(Color(80, 80, 80), Color(80, 80, 80))),
                    EmptyBorder(4, 8, 4, 8)
                )
                isContentAreaFilled = true
            })
            
            add(JLabel("Mode:").apply { 
                foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
                horizontalAlignment = SwingConstants.RIGHT 
            })
            add(modeSelector.apply {
                background = JBColor(Color(60, 60, 60), Color(60, 60, 60))
                foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
                border = BorderFactory.createLineBorder(JBColor(Color(80, 80, 80), Color(80, 80, 80)))
            })
            add(loadProjectButton.apply {
                background = JBColor(Color(60, 60, 60), Color(60, 60, 60))
                foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
                border = BorderFactory.createCompoundBorder(
                    BorderFactory.createLineBorder(JBColor(Color(80, 80, 80), Color(80, 80, 80))),
                    EmptyBorder(4, 8, 4, 8)
                )
                isContentAreaFilled = true
            })
            
            add(JLabel("Effort:").apply { 
                foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
                horizontalAlignment = SwingConstants.RIGHT 
            })
            add(levelSelector.apply {
                background = JBColor(Color(60, 60, 60), Color(60, 60, 60))
                foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
                border = BorderFactory.createLineBorder(JBColor(Color(80, 80, 80), Color(80, 80, 80)))
            })
            add(JLabel("").apply { background = JBColor(Color(40, 40, 40), Color(40, 40, 40)) })
        }

        // Status bar
        val statusPanel = JPanel(BorderLayout()).apply {
            border = EmptyBorder(5, 10, 5, 10)
            background = JBColor(Color(40, 40, 40), Color(40, 40, 40))
            add(statusLabel.apply {
                foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
            }, BorderLayout.WEST)
            
            val fileCountLabel = JLabel("").apply {
                foreground = JBColor(Color(176, 176, 176), Color(176, 176, 176))
                if (projectFiles.isNotEmpty()) {
                    text = "📁 ${projectFiles.size} files indexed"
                }
            }
            add(fileCountLabel, BorderLayout.EAST)
        }

        // Input panel
        val inputPanel = JPanel(BorderLayout(10, 0)).apply {
            border = EmptyBorder(10, 10, 10, 10)
            background = JBColor(Color(30, 30, 30), Color(30, 30, 30))
            
            val inputScrollPane = JBScrollPane(messageInput.apply {
                background = JBColor(Color(50, 50, 50), Color(50, 50, 50))
                foreground = JBColor(Color(224, 224, 224), Color(224, 224, 224))
                caretColor = JBColor(Color(255, 255, 255), Color(255, 255, 255))
                border = BorderFactory.createCompoundBorder(
                    BorderFactory.createLineBorder(JBColor(Color(80, 80, 80), Color(80, 80, 80))),
                    EmptyBorder(5, 5, 5, 5)
                )
            }).apply {
                preferredSize = Dimension(0, 80)
                background = JBColor(Color(50, 50, 50), Color(50, 50, 50))
                viewport.background = JBColor(Color(50, 50, 50), Color(50, 50, 50))
            }
            
            add(inputScrollPane, BorderLayout.CENTER)
            
            val buttonPanel = JPanel(FlowLayout(FlowLayout.RIGHT, 5, 0)).apply {
                background = JBColor(Color(30, 30, 30), Color(30, 30, 30))
                add(sendButton.apply {
                    background = JBColor(Color(13, 110, 253), Color(13, 110, 253))
                    foreground = Color.WHITE
                    border = BorderFactory.createCompoundBorder(
                        BorderFactory.createLineBorder(JBColor(Color(10, 85, 200), Color(10, 85, 200))),
                        EmptyBorder(4, 16, 4, 16)
                    )
                    isContentAreaFilled = true
                    font = font.deriveFont(Font.BOLD)
                })
                add(cancelButton.apply {
                    background = JBColor(Color(220, 53, 69), Color(220, 53, 69))
                    foreground = Color.WHITE
                    border = BorderFactory.createCompoundBorder(
                        BorderFactory.createLineBorder(JBColor(Color(180, 30, 40), Color(180, 30, 40))),
                        EmptyBorder(4, 16, 4, 16)
                    )
                    isContentAreaFilled = true
                    font = font.deriveFont(Font.BOLD)
                })
            }
            add(buttonPanel, BorderLayout.EAST)
        }

        // Top panel for title
        val topPanel = JPanel(BorderLayout()).apply {
            border = EmptyBorder(10, 10, 5, 10)
            background = JBColor(Color(40, 40, 40), Color(40, 40, 40))
            add(JLabel("ISE AI Copilot - Local Models via Ollama").apply {
                font = Font(font.name, Font.BOLD, 13)
                foreground = JBColor(Color(255, 255, 255), Color(255, 255, 255))
            }, BorderLayout.WEST)
        }

        mainPanel.apply {
            background = JBColor(Color(30, 30, 30), Color(30, 30, 30))
            add(topPanel, BorderLayout.NORTH)
            add(chatScrollPane, BorderLayout.CENTER)
            add(settingsPanel, BorderLayout.NORTH)
            add(quickActionsPanel, BorderLayout.PAGE_START)
            add(statusPanel, BorderLayout.SOUTH)
        }
        
        // Create a wrapper for input
        val bottomPanel = JPanel(BorderLayout()).apply {
            background = JBColor(Color(30, 30, 30), Color(30, 30, 30))
            add(inputPanel, BorderLayout.CENTER)
        }
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
            service.model = selected
            updateStatus("Model: $selected")
        }
        
        modeSelector.addActionListener {
            service.mode = modeSelector.selectedItem as String
            updateStatus("Mode: ${service.mode}")
        }
        
        levelSelector.addActionListener {
            service.effort = levelSelector.selectedItem as String
            updateStatus("Effort: ${service.effort}")
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

        // Trigger backend indexing
        scope.launch {
            try {
                service.indexProject(projectPath, project.name)
            } catch (e: Exception) {
                println("⚠️ Project indexing error: ${e.message}")
            }
        }

        // Also keep local index for quick access
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
        val requestEffort = service.effort

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
                    service.streamRequest(message, context, requestModel, requestMode, requestEffort) { chunk ->
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
            val bgColor = when (role) {
                "user" -> JBColor(Color(50, 100, 200), Color(50, 100, 200))
                "assistant" -> JBColor(Color(60, 60, 70), Color(60, 60, 70))
                "info" -> JBColor(Color(50, 140, 160), Color(50, 140, 160))
                "error" -> JBColor(Color(180, 50, 60), Color(180, 50, 60))
                else -> JBColor(Color(40, 40, 40), Color(40, 40, 40))
            }
            background = bgColor
            border = EmptyBorder(10, 12, 10, 12)
            maximumSize = Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE)
        }

        val headerPanel = JPanel(FlowLayout(FlowLayout.LEFT, 5, 0)).apply {
            background = messagePanel.background
            add(JLabel(
                when (role) {
                    "user" -> "👤 You"
                    "assistant" -> "🤖 Assistant"
                    "info" -> "ℹ️ Info"
                    "error" -> "❌ Error"
                    else -> "Message"
                }
            ).apply {
                foreground = Color.WHITE
                font = font.deriveFont(Font.BOLD, 11f)
            })
        }

        val contentPanel = JPanel(BorderLayout()).apply {
            background = messagePanel.background
            
            val editorPane = MessageFormatter.createHTMLEditorPane(content)
            editorPane.apply {
                background = messagePanel.background
                foreground = Color.WHITE
                isOpaque = true
            }
            
            val scrollPane = JScrollPane(editorPane).apply {
                border = null
                preferredSize = Dimension(400, 100)
                viewport.background = messagePanel.background
                background = messagePanel.background
            }
            add(scrollPane, BorderLayout.CENTER)
        }

        messagePanel.add(headerPanel, BorderLayout.NORTH)
        messagePanel.add(contentPanel, BorderLayout.CENTER)
        chatContainer.add(messagePanel)
        chatContainer.add(Box.createVerticalStrut(8))
        
        // Auto-scroll to bottom
        SwingUtilities.invokeLater {
            chatScrollPane.verticalScrollBar.value = chatScrollPane.verticalScrollBar.maximum
        }
    }

    private fun streamAssistantChunk(chunk: String) {
        if (currentMessageLabel == null) {
            val bgColor = JBColor(Color(60, 60, 70), Color(60, 60, 70))
            val panel = JPanel(BorderLayout()).apply {
                background = bgColor
                border = EmptyBorder(10, 12, 10, 12)
                maximumSize = Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE)
            }
            
            val headerPanel = JPanel(FlowLayout(FlowLayout.LEFT, 5, 0)).apply {
                background = bgColor
                add(JLabel("🤖 Assistant").apply {
                    foreground = Color.WHITE
                    font = font.deriveFont(Font.BOLD, 11f)
                })
            }
            
            currentMessageText = chunk
            currentMessageLabel = MessageFormatter.createHTMLEditorPane(chunk)
            currentMessageLabel!!.apply {
                background = bgColor
                foreground = Color.WHITE
                isOpaque = true
            }
            
            val scrollPane = JScrollPane(currentMessageLabel!!).apply {
                border = null
                viewport.background = bgColor
                background = bgColor
            }
            
            panel.add(headerPanel, BorderLayout.NORTH)
            panel.add(scrollPane, BorderLayout.CENTER)
            chatContainer.add(panel)
        } else {
            currentMessageText += chunk
            currentMessageLabel?.text = MessageFormatter.formatMarkdown(currentMessageText)
        }
        
        SwingUtilities.invokeLater {
            chatScrollPane.verticalScrollBar.value = chatScrollPane.verticalScrollBar.maximum
        }
    }

    private fun finishAssistantMessage(response: String) {
        currentMessageLabel = null
        currentMessageText = ""
    }

    fun dispose() {
        scope.cancel()
    }
}
