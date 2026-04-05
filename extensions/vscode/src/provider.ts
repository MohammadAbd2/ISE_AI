import * as vscode from 'vscode';
import fetch from 'node-fetch';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface CompletionRequest {
  message: string;
  context?: {
    file?: string;
    language?: string;
    code?: string;
    selection?: string;
    cursor?: vscode.Position;
  };
  multiAgent?: boolean;
}

export class ISEAIProvider {
  private context: vscode.ExtensionContext;
  private serverUrl: string;
  private apiKey: string;
  private model: string;
  private chatHistory: ChatMessage[] = [];
  private abortController: AbortController | null = null;

  constructor(context: vscode.ExtensionContext) {
    this.context = context;
    const config = vscode.workspace.getConfiguration('ise-ai-copilot');
    this.serverUrl = config.get('serverUrl', 'http://localhost:8000');
    this.apiKey = config.get('apiKey', '');
    this.model = config.get('model', '');
  }

  async sendRequest(message: string, context?: any): Promise<string> {
    this.abortController = new AbortController();
    
    try {
      const config = vscode.workspace.getConfiguration('ise-ai-copilot');
      const enableMultiAgent = config.get('enableMultiAgent', true);

      const response = await fetch(`${this.serverUrl}/api/agents/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
        },
        body: JSON.stringify({
          description: message,
          multi_agent: enableMultiAgent,
          context: context || {}
        }),
        signal: this.abortController.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.result || 'No response';
    } catch (error) {
      if (error.name === 'AbortError') {
        return 'Request aborted';
      }
      console.error('Error sending request:', error);
      throw error;
    } finally {
      this.abortController = null;
    }
  }

  async streamRequest(message: string, context?: any, onChunk?: (chunk: string) => void): Promise<string> {
    this.abortController = new AbortController();
    
    try {
      const config = vscode.workspace.getConfiguration('ise-ai-copilot');
      const enableMultiAgent = config.get('enableMultiAgent', true);

      const response = await fetch(`${this.serverUrl}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
        },
        body: JSON.stringify({
          message: message,
          model: this.model || undefined,
          multi_agent: enableMultiAgent,
          context: context || {}
        }),
        signal: this.abortController.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.trim()) continue;
          
          try {
            const data = JSON.parse(line);
            if (data.type === 'token') {
              fullResponse += data.content;
              onChunk?.(data.content);
            } else if (data.type === 'error') {
              throw new Error(data.message);
            } else if (data.type === 'done') {
              break;
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }

      return fullResponse;
    } catch (error) {
      if (error.name === 'AbortError') {
        return 'Request aborted';
      }
      console.error('Error streaming request:', error);
      throw error;
    } finally {
      this.abortController = null;
    }
  }

  async getCompletion(prefix: string, suffix: string, position: vscode.Position): Promise<string | null> {
    try {
      const config = vscode.workspace.getConfiguration('ise-ai-copilot');
      const maxContextLines = config.get('maxContextLines', 100);

      const response = await fetch(`${this.serverUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
        },
        body: JSON.stringify({
          message: `Complete this code. Provide ONLY the completion that should come next.\n\nPrefix:\n${prefix}\n\nSuffix:\n${suffix}\n\nComplete the code:`,
          model: this.model || undefined,
          context: {
            completion_mode: true,
            max_lines: maxContextLines
          }
        })
      });

      if (!response.ok) {
        return null;
      }

      const data = await response.json();
      return data.message || null;
    } catch (error) {
      console.error('Error getting completion:', error);
      return null;
    }
  }

  cancelRequest() {
    this.abortController?.abort();
  }

  getChatHistory(): ChatMessage[] {
    return [...this.chatHistory];
  }

  clearChatHistory() {
    this.chatHistory = [];
  }

  async updateConfig() {
    const config = vscode.workspace.getConfiguration('ise-ai-copilot');
    this.serverUrl = config.get('serverUrl', 'http://localhost:8000');
    this.apiKey = config.get('apiKey', '');
    this.model = config.get('model', '');
  }
}
