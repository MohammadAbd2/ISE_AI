package com.ise.ai.copilot.settings

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.ui.Messages
import com.ise.ai.copilot.service.ISEAIService
import javax.swing.*

class ISEAIConfigurable : Configurable {
    private var mySettingsComponent: ISEAISettingsPanel? = null

    override fun getDisplayName(): String {
        return "ISE AI Copilot"
    }

    override fun createComponent(): JComponent {
        mySettingsComponent = ISEAISettingsPanel()
        return mySettingsComponent!!.panel
    }

    override fun isModified(): Boolean {
        val service = ISEAIService.getInstance()
        return mySettingsComponent?.serverUrl?.text != service.serverUrl ||
               mySettingsComponent?.apiKey?.text != service.apiKey ||
               mySettingsComponent?.model?.text != service.model ||
               mySettingsComponent?.mode?.selectedItem as String != service.mode ||
               mySettingsComponent?.effort?.selectedItem as String != service.effort ||
               mySettingsComponent?.enableMultiAgent?.isSelected != service.enableMultiAgent
    }

    override fun apply() {
        val service = ISEAIService.getInstance()
        service.serverUrl = mySettingsComponent?.serverUrl?.text ?: "http://localhost:8000"
        service.apiKey = mySettingsComponent?.apiKey?.text ?: ""
        service.model = mySettingsComponent?.model?.text ?: "llama3"
        service.mode = mySettingsComponent?.mode?.selectedItem as String? ?: "auto"
        service.effort = mySettingsComponent?.effort?.selectedItem as String? ?: "medium"
        service.enableMultiAgent = mySettingsComponent?.enableMultiAgent?.isSelected ?: true
        
        Messages.showInfoMessage("Settings saved successfully", "ISE AI Copilot")
    }

    override fun reset() {
        val service = ISEAIService.getInstance()
        mySettingsComponent?.serverUrl?.text = service.serverUrl
        mySettingsComponent?.apiKey?.text = service.apiKey
        mySettingsComponent?.model?.text = service.model
        mySettingsComponent?.mode?.selectedItem = service.mode
        mySettingsComponent?.effort?.selectedItem = service.effort
        mySettingsComponent?.enableMultiAgent?.isSelected = service.enableMultiAgent
    }

    override fun disposeUIResources() {
        mySettingsComponent = null
    }
}
