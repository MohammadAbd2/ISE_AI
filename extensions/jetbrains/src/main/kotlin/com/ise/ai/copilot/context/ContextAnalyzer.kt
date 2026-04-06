package com.ise.ai.copilot.context

import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.psi.PsiManager
import java.io.File

/**
 * Advanced context analysis for better code understanding
 */
class ContextAnalyzer(private val project: Project) {
    
    fun analyzeCurrentFile(file: VirtualFile): Map<String, Any> {
        val context = mutableMapOf<String, Any>()
        
        context["file_path"] = file.path
        context["file_name"] = file.name
        context["language"] = file.fileType.name
        
        try {
            val psiFile = PsiManager.getInstance(project).findFile(file)
            if (psiFile != null) {
                val structure = extractStructure(psiFile)
                context["structure"] = structure
            }
        } catch (e: Exception) {
            // Gracefully handle analysis failures
        }
        
        return context
    }
    
    fun analyzeProjectStructure(): Map<String, Any> {
        val context = mutableMapOf<String, Any>()
        val basePath = project.basePath ?: return context
        
        val projectRoot = File(basePath)
        val structure = mutableMapOf<String, Int>()
        
        fun traverseDir(dir: File, depth: Int = 0) {
            if (depth > 3) return
            
            dir.listFiles()?.forEach { file ->
                if (!file.name.startsWith(".") && !file.name.startsWith("node_modules")) {
                    if (file.isFile) {
                        val ext = file.extension.ifEmpty { "unknown" }
                        structure[ext] = (structure[ext] ?: 0) + 1
                    } else if (file.isDirectory) {
                        traverseDir(file, depth + 1)
                    }
                }
            }
        }
        
        traverseDir(projectRoot)
        context["file_types"] = structure
        context["project_name"] = projectRoot.name
        
        return context
    }
    
    fun suggestRelevantFiles(userQuery: String): List<String> {
        val basePath = project.basePath ?: return emptyList()
        val projectRoot = File(basePath)
        val relevantFiles = mutableListOf<String>()
        val keywords = userQuery.lowercase().split(" ").filter { it.length > 3 }
        
        fun traverseDir(dir: File, depth: Int = 0) {
            if (depth > 4 || relevantFiles.size > 10) return
            
            dir.listFiles()?.forEach { file ->
                if (!file.name.startsWith(".")) {
                    if (file.isFile) {
                        val fileName = file.name.lowercase()
                        if (keywords.any { it in fileName } || file.extension in listOf("ts", "tsx", "kt", "java", "py")) {
                            relevantFiles.add(file.absolutePath)
                        }
                    } else if (file.isDirectory && file.name !in listOf("node_modules", ".git", "build", "dist")) {
                        traverseDir(file, depth + 1)
                    }
                }
            }
        }
        
        traverseDir(projectRoot)
        return relevantFiles
    }
    
    fun detectFrameworksAndLibraries(): List<String> {
        val frameworks = mutableListOf<String>()
        val basePath = project.basePath ?: return frameworks
        
        File(basePath, "package.json").takeIf { it.exists() }?.let {
            val content = it.readText().lowercase()
            if ("react" in content) frameworks.add("React")
            if ("vue" in content) frameworks.add("Vue")
            if ("angular" in content) frameworks.add("Angular")
            if ("next" in content) frameworks.add("Next.js")
            if ("typescript" in content) frameworks.add("TypeScript")
        }
        
        File(basePath, "pom.xml").takeIf { it.exists() }?.let {
            frameworks.add("Maven")
            val content = it.readText().lowercase()
            if ("spring" in content) frameworks.add("Spring")
        }
        
        File(basePath, "build.gradle").takeIf { it.exists() }?.let {
            frameworks.add("Gradle")
        }
        
        File(basePath, "requirements.txt").takeIf { it.exists() }?.let {
            frameworks.add("Python")
        }
        
        return frameworks
    }
    
    private fun extractStructure(psiFile: com.intellij.psi.PsiFile): Map<String, Any> {
        val structure = mutableMapOf<String, Any>()
        
        try {
            val text = psiFile.text
            structure["line_count"] = text.lines().size
            
            val content = text.lowercase()
            val constructs = mutableListOf<String>()
            
            if (content.contains("class ")) constructs.add("classes")
            if (content.contains("fun ") || content.contains("def ")) constructs.add("functions")
            if (content.contains("interface ")) constructs.add("interfaces")
            if (content.contains("enum ")) constructs.add("enums")
            
            structure["constructs"] = constructs
            
        } catch (e: Exception) {
            // Gracefully handle errors
        }
        
        return structure
    }
}
