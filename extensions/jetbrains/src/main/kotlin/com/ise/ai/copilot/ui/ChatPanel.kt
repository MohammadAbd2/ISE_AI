package com.ise.ai.copilot.ui

import com.intellij.openapi.application.ApplicationManager
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
import javax.swing.text.SimpleAttributeSet
import javax.swing.text.StyleConstants

class ChatPanel(private val project: Project) {
    private val service = ISEAIService.getInstance()
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    
    val mainPanel: JPanel = JPanel(BorderLayout())
    private val chatContainer = JPanel()
    private val messageInput = JBTextArea().apply {
        lineWrap = true
        wrapStyleWord = true
        border = BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(JBColor.border()),
            EmptyBorder(5, 5, 5, 5)
        )
    }
    private val sendButton = JButton("Send")
    private val cancelButton = JButton("Cancel").apply {
        isVisible = false
    }
    
    private val chatLayout = BoxLayout(chatContainer, BoxLayout.Y_AXIS)
    private var currentMessageLabel: JLabel? = null
    private var isStreaming = false

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
        mainPanel.add(inputPanel, BorderLayout.SOUTH)
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
        }

        messageInput.addActionListener {
            if (!isStreaming) {
                sendMessage()
            }
        }
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

        // Get editor context
        val context = getEditorContext()

        // Send request
        scope.launch {
            try {
                var response = ""
                
                response = withContext(Dispatchers.IO) {
                    service.streamRequest(message, context) { chunk ->
                        // Update UI on EDT
                        ApplicationManager.getApplication().invokeLater {
                            streamAssistantChunk(chunk)
                        }
                    }.await()
                }

                // Finalize message
                ApplicationManager.getApplication().invokeLater {
                    finishAssistantMessage(response)
                    sendButton.isVisible = true
                    cancelButton.isVisible = false
                    isStreaming = false
                }
            } catch (e: Exception) {
                ApplicationManager.getApplication().invokeLater {
                    appendMessage("error", "Error: ${e.message}")
                    sendButton.isVisible = true
                    cancelButton.isVisible = false
                    isStreaming = false
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
        
        return context
    }

    private fun appendMessage(role: String, content: String) {
        val messagePanel = JPanel(BorderLayout()).apply {
            border = CompoundBorder(
                LineBorder(
                    when (role) {
                        "user" -> JBColor.BLUE
                        "assistant" -> JBColor.GREEN
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
                "error" -> JBColor.namedColor("Component.errorFocusColor", Color(255, 230, 230))
                else -> JBColor.background()
            }
        }

        val textPane = JTextPane().apply {
            isEditable = false
            background = messagePanel.background
            styledDocument.apply {
                setParagraphAttributes(0, length, SimpleAttributeSet().apply {
                    StyleConstants.setLineSpacing(this, 1.5)
                }, false)
            }
            
            // Format message with code blocks
            formatMessage(content)
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

    private fun formatMessage(content: String) {
        // Simple formatting - in production, use a markdown library
        val lines = content.split("\n")
        var inCodeBlock = false
        
        for (line in lines) {
            if (line.startsWith("```")) {
                inCodeBlock = !inCodeBlock
                continue
            }
            
            if (inCodeBlock) {
                // Code block formatting
            } else {
                // Regular text
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
                verticalAlignment = SwingConstants.TOP
            }
            
            panel.add(JScrollPane(currentMessageLabel!!).apply {
                border = null
            }, BorderLayout.CENTER)
            
            chatContainer.add(panel)
        }
        
        val currentText = currentMessageLabel?.text ?: ""
        currentMessageLabel?.text = currentText + chunk
        
        // Auto-scroll
        SwingUtilities.invokeLater {
            val parent = chatContainer.parent
            if (parent is JScrollPane) {
                parent.verticalScrollBar.value = parent.verticalScrollBar.maximum
            }
        }
    }

    private fun finishAssistantMessage(content: String) {
        if (currentMessageLabel == null) {
            appendMessage("assistant", content)
        }
        currentMessageLabel = null
    }

    fun dispose() {
        scope.cancel()
    }
}
