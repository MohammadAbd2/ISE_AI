package com.ise.ai.copilot.settings

import com.intellij.ui.components.JBCheckBox
import com.intellij.ui.components.JBLabel
import com.intellij.ui.components.JBTextField
import com.intellij.util.ui.FormBuilder
import javax.swing.JPanel

class ISEAISettingsPanel {
    val panel: JPanel
    val serverUrl = JBTextField().apply {
        text = "http://localhost:8000"
    }
    val apiKey = JBTextField()
    val model = JBTextField()
    val enableMultiAgent = JBCheckBox("Enable Multi-Agent Orchestration").apply {
        isSelected = true
    }

    init {
        panel = FormBuilder.createFormBuilder()
            .addLabeledComponent(JBLabel("Server URL:"), serverUrl, 1, false)
            .addLabeledComponent(JBLabel("API Key (optional):"), apiKey, 1, false)
            .addLabeledComponent(JBLabel("Model (optional):"), model, 1, false)
            .addComponent(enableMultiAgent, 1)
            .addComponentFillVertically(JPanel(), 0)
            .panel
    }
}
