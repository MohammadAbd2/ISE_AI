package ai.ise.plugin

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.components.JBPanel
import com.intellij.ui.components.JBTextArea
import java.awt.BorderLayout
import java.awt.Dimension
import java.net.HttpURLConnection
import java.net.URL
import javax.swing.JButton
import javax.swing.JLabel
import javax.swing.JPanel
import org.json.JSONObject

class IseAiToolWindowFactory : ToolWindowFactory {
    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val root = project.basePath ?: ""
        val panel = JBPanel<JBPanel<*>>(BorderLayout())
        val instruction = JBTextArea("rewrite the component App.jsx in a better way")
        instruction.lineWrap = true
        instruction.preferredSize = Dimension(420, 96)
        val status = JLabel("Project: $root")
        val run = JButton("Apply Agent edit to current project")
        run.addActionListener {
            val basePath = project.basePath
            if (basePath.isNullOrBlank()) {
                Messages.showErrorDialog(project, "No project path detected.", "ISE Agent")
                return@addActionListener
            }
            status.text = "Sending request to Agent..."
            ApplicationManager.getApplication().executeOnPooledThread {
                try {
                    val response = rewriteFile(basePath, "src/App.jsx", instruction.text)
                    val content = response.getString("content")
                    ApplicationManager.getApplication().invokeLater {
                        val file = LocalFileSystem.getInstance().refreshAndFindFileByPath("$basePath/src/App.jsx")
                        val document = file?.let { FileDocumentManager.getInstance().getDocument(it) }
                        if (document == null) {
                            Messages.showErrorDialog(project, "src/App.jsx not found or not editable.", "ISE Agent")
                            status.text = "File not found"
                            return@invokeLater
                        }
                        WriteCommandAction.runWriteCommandAction(project) {
                            document.setText(content)
                            FileDocumentManager.getInstance().saveDocument(document)
                        }
                        file.refresh(false, false)
                        status.text = "Updated src/App.jsx (${response.optInt("bytes")} bytes)"
                    }
                } catch (error: Exception) {
                    ApplicationManager.getApplication().invokeLater {
                        status.text = "Agent edit failed"
                        Messages.showErrorDialog(project, error.message ?: error.toString(), "ISE Agent")
                    }
                }
            }
        }
        val top = JPanel(BorderLayout())
        top.add(JLabel("ISE Agent IDE Bridge"), BorderLayout.NORTH)
        top.add(instruction, BorderLayout.CENTER)
        top.add(run, BorderLayout.SOUTH)
        panel.add(top, BorderLayout.NORTH)
        panel.add(status, BorderLayout.SOUTH)
        toolWindow.component.add(panel)
    }

    private fun rewriteFile(projectPath: String, relativePath: String, instruction: String): JSONObject {
        val url = URL("http://127.0.0.1:8000/api/devx/ide/rewrite-file")
        val body = JSONObject()
            .put("project_path", projectPath)
            .put("relative_path", relativePath)
            .put("instruction", instruction)
            .toString()
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            setRequestProperty("Content-Type", "application/json")
            doOutput = true
            connectTimeout = 5000
            readTimeout = 60000
        }
        conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        val stream = if (conn.responseCode in 200..299) conn.inputStream else conn.errorStream
        val text = stream.bufferedReader().readText()
        if (conn.responseCode !in 200..299) throw RuntimeException(text)
        return JSONObject(text)
    }
}

// v9 IDE write-back bridge notes:
// - Detect Project.basePath and selected editor file.
// - Send {file_path, original_content, request} to /api/agentic-visual/ide/patch.
// - Show returned unified diff.
// - Apply updated_content only after user approval.
//
// fun applyAgentPatchToCurrentFile(project: Project, document: Document, updatedContent: String) {
//     WriteCommandAction.runWriteCommandAction(project) { document.setText(updatedContent) }
// }
