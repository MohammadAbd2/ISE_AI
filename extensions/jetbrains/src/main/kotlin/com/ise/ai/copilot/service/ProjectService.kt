package com.ise.ai.copilot.service

import com.intellij.openapi.project.Project
import com.intellij.openapi.roots.ProjectRootManager
import com.intellij.openapi.vfs.VirtualFile
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import okhttp3.OkHttpClient
import okhttp3.Request

/**
 * Service for analyzing and managing project structure
 */
class ProjectService(private val project: Project) {
    private val client = OkHttpClient()
    private val mapper = jacksonObjectMapper()
    private var projectMetadata: Map<String, Any>? = null
    
    fun getProjectRoot(): VirtualFile? {
        return ProjectRootManager.getInstance(project).contentRootsFromAllModules.firstOrNull()
    }
    
    fun getProjectPath(): String {
        return project.basePath ?: ""
    }
    
    fun getSourceFolders(): List<VirtualFile> {
        val projectRootManager = ProjectRootManager.getInstance(project)
        return projectRootManager.contentSourceRoots.toList()
    }
    
    fun countFilesInFolder(folderPath: String? = null): Map<String, Any> {
        val root = getProjectRoot() ?: return mapOf("error" to "No project root")
        val target = if (folderPath != null) root.findFileByRelativePath(folderPath) else root
        
        if (target == null || !target.isDirectory) {
            return mapOf("error" to "Folder not found")
        }
        
        var fileCount = 0
        var folderCount = 0
        
        target.children.forEach { child ->
            if (child.isDirectory) folderCount++ else fileCount++
        }
        
        return mapOf(
            "folder" to (folderPath ?: "root"),
            "files" to fileCount,
            "folders" to folderCount
        )
    }
    
    fun getProjectStructure(depth: Int = 2): Map<String, Any> {
        val root = getProjectRoot() ?: return mapOf("error" to "No project root")
        
        return mapOf(
            "name" to (project.name),
            "path" to getProjectPath(),
            "structure" to buildFolderStructure(root, depth)
        )
    }
    
    private fun buildFolderStructure(folder: VirtualFile, depth: Int): Map<String, Any> {
        if (depth <= 0) return emptyMap()
        
        val children = mutableMapOf<String, Any>()
        val folders = mutableListOf<String>()
        val files = mutableListOf<String>()
        
        folder.children.forEach { child ->
            if (child.isDirectory && !child.name.startsWith(".")) {
                folders.add(child.name)
                children[child.name] = buildFolderStructure(child, depth - 1)
            } else if (!child.isDirectory && !child.name.startsWith(".")) {
                files.add(child.name)
            }
        }
        
        return mapOf(
            "folders" to folders,
            "files" to files,
            "subfolders" to children
        )
    }
    
    fun searchFiles(pattern: String): List<Map<String, Any>> {
        val root = getProjectRoot() ?: return emptyList()
        val results = mutableListOf<Map<String, Any>>()
        val regex = Regex(pattern, RegexOption.IGNORE_CASE)
        
        fun searchRecursive(folder: VirtualFile) {
            if (results.size >= 50) return // Limit results
            
            folder.children.forEach { child ->
                if (child.isDirectory && !child.name.startsWith(".")) {
                    searchRecursive(child)
                } else if (!child.isDirectory) {
                    if (regex.containsMatchIn(child.name)) {
                        try {
                            val relativePath = child.path.removePrefix(root.path + "/")
                            results.add(mapOf(
                                "name" to child.name,
                                "path" to relativePath,
                                "size" to child.length
                            ))
                        } catch (e: Exception) {
                            // Ignore files we can't read
                        }
                    }
                }
            }
        }
        
        searchRecursive(root)
        return results
    }
    
    fun readFile(filePath: String): Map<String, Any> {
        val root = getProjectRoot() ?: return mapOf("error" to "No project root")
        val file = root.findFileByRelativePath(filePath) ?: return mapOf("error" to "File not found")
        
        if (file.isDirectory) return mapOf("error" to "Path is a directory")
        
        return try {
            val content = String(file.contentsToByteArray())
            val size = file.length
            
            mapOf(
                "success" to true,
                "path" to filePath,
                "content" to content,
                "size" to size
            )
        } catch (e: Exception) {
            mapOf("error" to "Could not read file: ${e.message}")
        }
    }
    
    fun getFileStats(): Map<String, Any> {
        val root = getProjectRoot() ?: return mapOf("error" to "No project root")
        
        var totalFiles = 0
        var totalSize = 0L
        val typeCount = mutableMapOf<String, Int>()
        
        fun countRecursive(folder: VirtualFile) {
            folder.children.forEach { child ->
                if (child.isDirectory && !child.name.startsWith(".")) {
                    countRecursive(child)
                } else if (!child.isDirectory) {
                    totalFiles++
                    totalSize += child.length
                    
                    val ext = child.extension ?: "no_extension"
                    typeCount[ext] = typeCount.getOrDefault(ext, 0) + 1
                }
            }
        }
        
        countRecursive(root)
        
        return mapOf(
            "total_files" to totalFiles,
            "total_size_mb" to (totalSize / (1024.0 * 1024.0)),
            "by_extension" to typeCount
        )
    }
    
    suspend fun fetchProjectInfoFromBackend(serverUrl: String): Map<String, Any> {
        return try {
            val request = Request.Builder()
                .url("$serverUrl/api/project/info")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (response.isSuccessful) {
                val body = response.body?.string() ?: ""
                mapper.readValue<Map<String, Any>>(body)
            } else {
                mapOf("error" to "Failed to fetch project info from backend")
            }
        } catch (e: Exception) {
            mapOf("error" to "Could not fetch project info: ${e.message}")
        }
    }
    
    fun getProjectContext(): Map<String, Any> {
        val stats = getFileStats()
        val structure = getProjectStructure(depth = 1)
        
        return mapOf(
            "project_name" to project.name,
            "project_path" to getProjectPath(),
            "stats" to stats,
            "structure" to structure,
            "source_folders" to getSourceFolders().map { it.name }
        )
    }
}
