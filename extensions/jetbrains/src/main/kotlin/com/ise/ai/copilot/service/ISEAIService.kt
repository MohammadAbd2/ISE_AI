package com.ise.ai.copilot.service

import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.project.Project
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.BufferedReader
import java.io.InputStreamReader

data class ChatMessage(
    val role: String,
    val content: String,
    val timestamp: Long = System.currentTimeMillis()
)

data class CompletionRequest(
    val message: String,
    val context: Map<String, Any?>? = null,
    val multiAgent: Boolean = true
)

data class CompletionResponse(
    val result: String?,
    val status: String,
    val usedAgents: List<String>? = null,
    val error: String? = null
)

@Service
class ISEAIService {
    private val client = OkHttpClient.Builder()
        .connectTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(120, java.util.concurrent.TimeUnit.SECONDS)
        .build()
    
    private val mapper = jacksonObjectMapper()
    private val chatHistory = mutableListOf<ChatMessage>()
    private var currentJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    var serverUrl: String = "http://localhost:8000"
    var apiKey: String = ""
    var model: String = "claude-haiku-4.5"
    var mode: String = "auto"
    var level: String = "medium"
    var enableMultiAgent: Boolean = true
    var useAdvancedContext: Boolean = true

    companion object {
        @JvmStatic
        fun getInstance(): ISEAIService {
            return ApplicationManager.getApplication().getService(ISEAIService::class.java)
        }
    }

    suspend fun sendRequest(message: String, context: Map<String, Any?>? = null): String {
        return try {
            val requestBody = mapper.writeValueAsString(
                mapOf(
                    "description" to message,
                    "multi_agent" to enableMultiAgent,
                    "context" to (context ?: emptyMap<String, Any?>())
                )
            )

            val request = Request.Builder()
                .url("$serverUrl/api/agents/execute")
                .post(requestBody.toRequestBody("application/json".toMediaType()))
                .apply {
                    if (apiKey.isNotEmpty()) {
                        header("Authorization", "Bearer $apiKey")
                    }
                }
                .build()

            withContext(Dispatchers.IO) {
                client.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) {
                        throw Exception("HTTP error: ${response.code}")
                    }
                    
                    val responseBody = response.body?.string() ?: ""
                    val completionResponse = mapper.readValue<CompletionResponse>(responseBody)
                    
                    completionResponse.result ?: "No response"
                }
            }
        } catch (e: Exception) {
            throw Exception("Error sending request: ${e.message}", e)
        }
    }

    suspend fun streamRequest(
        message: String, 
        context: Map<String, Any?>? = null,
        model: String = "",
        mode: String = "auto",
        level: String = "medium",
        onChunk: (String) -> Unit
    ): String {
        return withContext(Dispatchers.IO) {
            currentJob = coroutineContext[Job]
            
            try {
                val systemPrompt = when {
                    mode == "agent" -> """You are an autonomous AI agent capable of analyzing code, suggesting improvements, and executing tasks. 
You should be proactive in identifying issues and providing solutions."""
                    mode == "chat" -> """You are a helpful AI assistant. Provide clear, conversational responses.
Be friendly and engage the user in dialogue."""
                    else -> """You are an intelligent code assistant. Analyze code, provide explanations, suggestions, and improvements.
Be concise but thorough. Format code blocks with proper syntax highlighting."""
                }
                
                val contextStr = context?.entries?.joinToString("\n") { (k, v) ->
                    "$k: ${v.toString().take(500)}"
                } ?: ""
                
                val requestBody = mapper.writeValueAsString(
                    mapOf(
                        "message" to message,
                        "model" to (model.ifEmpty { this@ISEAIService.model }),
                        "mode" to mode,
                        "level" to level,
                        "system_prompt" to systemPrompt,
                        "multi_agent" to enableMultiAgent,
                        "use_advanced_context" to useAdvancedContext,
                        "context" to (context ?: emptyMap<String, Any?>()),
                        "temperature" to when (level) {
                            "low" -> 0.2
                            "high" -> 0.9
                            else -> 0.6
                        }
                    )
                )

                val request = Request.Builder()
                    .url("$serverUrl/api/chat/stream")
                    .post(requestBody.toRequestBody("application/json".toMediaType()))
                    .apply {
                        if (apiKey.isNotEmpty()) {
                            header("Authorization", "Bearer $apiKey")
                        }
                        header("User-Agent", "ISE-AI-Plugin/1.0")
                    }
                    .build()

                val response = client.newCall(request).execute()
                
                if (!response.isSuccessful) {
                    throw Exception("HTTP error: ${response.code} - ${response.message}")
                }

                val reader = BufferedReader(InputStreamReader(response.body?.byteStream()))
                val fullResponse = StringBuilder()
                var receivedData = false
                
                reader.useLines { lines ->
                    lines.forEach { line ->
                        if (line.isBlank()) return@forEach
                        
                        try {
                            val data = mapper.readValue<Map<String, Any>>(line)
                            when (data["type"]) {
                                "token" -> {
                                    val content = (data["content"] as? String) ?: ""
                                    if (content.isNotEmpty()) {
                                        receivedData = true
                                        fullResponse.append(content)
                                        onChunk(content)
                                    }
                                }
                                "error" -> {
                                    throw Exception((data["message"] as? String) ?: "Unknown error from backend")
                                }
                                "done" -> {
                                    return@forEach
                                }
                            }
                        } catch (e: Exception) {
                            if (e.message?.contains("Unknown error from backend") == true) {
                                throw e
                            }
                            // Skip invalid JSON lines
                        }
                    }
                }

                if (!receivedData && fullResponse.toString().isEmpty()) {
                    throw Exception("No response received from backend. Please check if the backend is running.")
                }

                fullResponse.toString()
            } catch (e: Exception) {
                if (e is CancellationException) {
                    "Request cancelled"
                } else {
                    throw Exception("Error streaming request: ${e.message}", e)
                }
            } finally {
                currentJob = null
            }
        }
    }

    fun getCompletion(prefix: String, suffix: String): String? {
        return try {
            val prompt = """
                Complete this code. Provide ONLY the completion that should come next.
                
                Prefix:
                $prefix
                
                Suffix:
                $suffix
                
                Complete the code:
            """.trimIndent()

            val requestBody = mapper.writeValueAsString(
                mapOf(
                    "message" to prompt,
                    "model" to (model.ifEmpty { null }),
                    "context" to mapOf(
                        "completion_mode" to true,
                        "max_lines" to 100
                    )
                )
            )

            val request = Request.Builder()
                .url("$serverUrl/api/chat")
                .post(requestBody.toRequestBody("application/json".toMediaType()))
                .apply {
                    if (apiKey.isNotEmpty()) {
                        header("Authorization", "Bearer $apiKey")
                    }
                }
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    return null
                }
                
                val responseBody = response.body?.string() ?: ""
                val data = mapper.readValue<Map<String, Any>>(responseBody)
                data["message"] as? String
            }
        } catch (e: Exception) {
            null
        }
    }

    fun cancelRequest() {
        currentJob?.cancel()
    }

    fun getChatHistory(): List<ChatMessage> {
        return chatHistory.toList()
    }

    fun clearChatHistory() {
        chatHistory.clear()
    }

    fun addMessageToHistory(message: ChatMessage) {
        chatHistory.add(message)
    }
}
