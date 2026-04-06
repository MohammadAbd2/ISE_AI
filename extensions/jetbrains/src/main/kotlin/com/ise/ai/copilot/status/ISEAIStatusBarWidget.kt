package com.ise.ai.copilot.status

import com.intellij.openapi.wm.StatusBar
import com.intellij.openapi.util.Disposer
import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.StatusBarWidgetFactory

/**
 * Factory for creating status bar widgets.
 */
class ISEAIStatusBarFactory : StatusBarWidgetFactory {
    override fun getId(): String = "ISEAIStatusBarFactory"
    
    override fun getDisplayName(): String = "ISE AI Copilot Status"
    
    override fun isAvailable(project: Project): Boolean = false
    
    override fun createWidget(project: Project): com.intellij.openapi.wm.StatusBarWidget {
        // Return a simple label widget
        return object : com.intellij.openapi.wm.StatusBarWidget {
            private val label = javax.swing.JLabel("ISE AI")
            
            override fun ID(): String = "ISEAIStatusBarWidget"
            
            override fun install(statusBar: StatusBar) {
                label.addMouseListener(object : java.awt.event.MouseAdapter() {
                    override fun mouseClicked(e: java.awt.event.MouseEvent) {
                        val toolWindow = com.intellij.openapi.wm.ToolWindowManager.getInstance(project)
                            .getToolWindow("ISE AI Copilot")
                        toolWindow?.show()
                    }
                })
            }
            
            override fun dispose() {}
        }
    }
    
    override fun disposeWidget(widget: com.intellij.openapi.wm.StatusBarWidget) {
        Disposer.dispose(widget)
    }
    
    override fun canBeEnabledOn(statusBar: StatusBar): Boolean = true
}
