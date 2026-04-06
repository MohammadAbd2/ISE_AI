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
               mySettingsComponent?.level?.selectedItem as String != service.level ||
               mySettingsComponent?.enableMultiAgent?.isSelected != service.enableMultiAgent ||
               mySettingsComponent?.useAdvancedContext?.isSelected != service.useAdvancedContext
    }

    override fun apply() {
        val service = ISEAIService.getInstance()
        service.serverUrl = mySettingsComponent?.serverUrl?.text ?: "http://localhost:8000"
        service.apiKey = mySettingsComponent?.apiKey?.text ?: ""
        service.model = mySettingsComponent?.model?.text ?: "claude-haiku-4.5"
        service.mode = mySettingsComponent?.mode?.selectedItem as String? ?: "auto"
        service.level = mySettingsComponent?.level?.selectedItem as String? ?: "medium"
        service.enableMultiAgent = mySettingsComponent?.enableMultiAgent?.isSelected ?: true
        service.useAdvancedContext = mySettingsComponent?.useAdvancedContext?.isSelected ?: true
        
        Messages.showInfoMessage("Settings saved successfully", "ISE AI Copilot")
    }

    override fun reset() {
        val service = ISEAIService.getInstance()
        mySettingsComponent?.serverUrl?.text = service.serverUrl
        mySettingsComponent?.apiKey?.text = service.apiKey
        mySettingsComponent?.model?.text = service.model
        mySettingsComponent?.mode?.selectedItem = service.mode
        mySettingsComponent?.level?.selectedItem = service.level
        mySettingsComponent?.enableMultiAgent?.isSelected = service.enableMultiAgent
        mySettingsComponent?.useAdvancedContext?.isSelected = service.useAdvancedContext
    }

    override fun disposeUIResources() {
        mySettingsComponent = null
    }
}
