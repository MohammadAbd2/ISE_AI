package com.ise.ai.copilot.status

import com.intellij.openapi.wm.StatusBar
import com.intellij.openapi.wm.StatusBarWidget
import com.intellij.openapi.util.Disposer
import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.StatusBarWidgetFactory
import com.ise.ai.copilot.service.ISEAIService
import java.awt.event.MouseEvent
import javax.swing.JComponent
import javax.swing.JLabel

/**
 * Status bar widget showing ISE AI Copilot status.
 */
class ISEAIStatusBarWidget(private val project: Project) : StatusBarWidget {
    
    private val label = JLabel("ISE AI").apply {
        toolTipText = "ISE AI Copilot - Click to open chat"
    }
    
    override fun ID(): String = "ISEAIStatusBarWidget"
    
    override fun getPresentation(): StatusBarWidget.Presentation = 
        object : StatusBarWidget.Presentation {
            override fun getTooltipText(): String = "ISE AI Copilot - Click to open chat"
            override fun getClickConsumer(): java.awt.event.Consumer<MouseEvent>? = null
        }
    
    override fun getComponent(): JComponent = label
    
    override fun install(statusBar: StatusBar) {
        label.addMouseListener(object : java.awt.event.MouseAdapter() {
            override fun mouseClicked(e: MouseEvent) {
                // Open chat tool window
                val toolWindow = com.intellij.openapi.wm.ToolWindowManager.getInstance(project)
                    .getToolWindow("ISE AI Copilot")
                toolWindow?.show()
            }
        })
    }
    
    override fun dispose() {
        // Cleanup if needed
    }
}

/**
 * Factory for creating status bar widgets.
 */
class ISEAIStatusBarFactory : StatusBarWidgetFactory {
    override fun getId(): String = "ISEAIStatusBarFactory"
    
    override fun getDisplayName(): String = "ISE AI Copilot Status"
    
    override fun isAvailable(project: Project): Boolean = true
    
    override fun createWidget(project: Project): StatusBarWidget = ISEAIStatusBarWidget(project)
    
    override fun disposeWidget(widget: StatusBarWidget) {
        Disposer.dispose(widget)
    }
    
    override fun canBeEnabledOn(statusBar: StatusBar): Boolean = true
}
