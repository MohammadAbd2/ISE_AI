import * as vscode from 'vscode';
import { ISEAIProvider } from './provider';

export class ChatPanel {
  public static readonly viewType = 'ise-ai-copilot-chat';
  private panel: vscode.WebviewPanel | undefined;
  private provider: ISEAIProvider;
  private context: vscode.ExtensionContext;
  private disposables: vscode.Disposable[] = [];

  constructor(context: vscode.ExtensionContext, provider: ISEAIProvider) {
    this.context = context;
    this.provider = provider;
  }

  public show() {
    if (this.panel) {
      this.panel.reveal(vscode.ViewColumn.One);
      return;
    }

    this.panel = vscode.window.createWebviewPanel(
      ChatPanel.viewType,
      'ISE AI Copilot',
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [this.context.extensionUri]
      }
    );

    this.panel.webview.html = this.getHtml();
    this.setupMessageHandling();

    this.panel.onDidDispose(
      () => {
        this.panel = undefined;
      },
      null,
      this.disposables
    );
  }

  public async sendMessage(message: string) {
    if (!this.panel) {
      this.show();
    }

    this.panel?.webview.postMessage({
      type: 'userMessage',
      content: message
    });

    try {
      await this.handleUserMessage(message);
    } catch (error) {
      this.panel?.webview.postMessage({
        type: 'errorMessage',
        content: `Error: ${error}`
      });
    }
  }

  private setupMessageHandling() {
    this.panel?.webview.onDidReceiveMessage(
      async (message) => {
        switch (message.type) {
          case 'userMessage':
            await this.handleUserMessage(message.content);
            break;
          case 'cancelRequest':
            this.provider.cancelRequest();
            break;
          case 'clearHistory':
            this.provider.clearChatHistory();
            break;
        }
      },
      undefined,
      this.disposables
    );
  }

  private async handleUserMessage(message: string) {
    const editor = vscode.window.activeTextEditor;
    const context: any = {};

    if (editor) {
      context.file = editor.document.fileName;
      context.language = editor.document.languageId;
      context.code = editor.document.getText();
      
      if (!editor.selection.isEmpty) {
        context.selection = editor.document.getText(editor.selection);
      }
    }

    try {
      let response = '';
      
      // Stream the response
      response = await this.provider.streamRequest(
        message,
        context,
        (chunk) => {
          this.panel?.webview.postMessage({
            type: 'assistantChunk',
            content: chunk
          });
        }
      );

      this.panel?.webview.postMessage({
        type: 'assistantResponse',
        content: response
      });
    } catch (error) {
      this.panel?.webview.postMessage({
        type: 'errorMessage',
        content: `Error: ${error}`
      });
    }
  }

  private getHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ISE AI Copilot</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: var(--vscode-font-family);
      padding: 20px;
      height: 100vh;
      display: flex;
      flex-direction: column;
      background: var(--vscode-editor-background);
      color: var(--vscode-editor-foreground);
    }
    #chat-container {
      flex: 1;
      overflow-y: auto;
      margin-bottom: 20px;
      padding: 10px;
    }
    .message {
      margin-bottom: 15px;
      padding: 12px;
      border-radius: 6px;
      line-height: 1.5;
    }
    .user-message {
      background: var(--vscode-input-background);
      border-left: 3px solid var(--vscode-button-background);
    }
    .assistant-message {
      background: var(--vscode-editor-inactiveSelectionBackground);
      border-left: 3px solid var(--vscode-textLink-foreground);
    }
    .error-message {
      background: var(--vscode-inputValidation-errorBackground);
      border-left: 3px solid var(--vscode-errorForeground);
    }
    #input-container {
      display: flex;
      gap: 10px;
    }
    #message-input {
      flex: 1;
      padding: 10px;
      border: 1px solid var(--vscode-input-border);
      background: var(--vscode-input-background);
      color: var(--vscode-input-foreground);
      border-radius: 4px;
      resize: none;
      font-family: var(--vscode-editor-font-family);
      min-height: 60px;
      max-height: 150px;
    }
    #send-button, #cancel-button {
      padding: 10px 20px;
      background: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
    #send-button:hover {
      background: var(--vscode-button-hoverBackground);
    }
    #cancel-button {
      background: var(--vscode-button-secondaryBackground);
    }
    pre {
      background: var(--vscode-textCodeBlock-background);
      padding: 12px;
      border-radius: 4px;
      overflow-x: auto;
      margin: 8px 0;
    }
    code {
      font-family: var(--vscode-editor-font-family);
      font-size: var(--vscode-editor-font-size);
    }
    .typing-indicator {
      display: inline-block;
      animation: blink 1s infinite;
    }
    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }
  </style>
</head>
<body>
  <div id="chat-container"></div>
  <div id="input-container">
    <textarea id="message-input" placeholder="Ask ISE AI anything... (Press Enter to send)"></textarea>
    <button id="send-button">Send</button>
    <button id="cancel-button" style="display: none;">Cancel</button>
  </div>

  <script>
    const vscode = acquireVsCodeApi();
    const chatContainer = document.getElementById('chat-container');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const cancelButton = document.getElementById('cancel-button');
    let currentMessage = null;
    let isStreaming = false;

    // Handle messages from extension
    window.addEventListener('message', event => {
      const message = event.data;
      switch (message.type) {
        case 'userMessage':
          appendMessage('user', message.content);
          break;
        case 'assistantResponse':
          finishAssistantMessage(message.content);
          break;
        case 'assistantChunk':
          streamAssistantChunk(message.content);
          break;
        case 'errorMessage':
          appendMessage('error', message.content);
          hideCancel();
          break;
      }
    });

    function appendMessage(role, content) {
      const messageDiv = document.createElement('div');
      messageDiv.className = \`message \${role}-message\`;
      messageDiv.innerHTML = formatMessage(content);
      chatContainer.appendChild(messageDiv);
      chatContainer.scrollTop = chatContainer.scrollHeight;
      return messageDiv;
    }

    function formatMessage(content) {
      // Simple markdown code formatting
      return content
        .replace(/\`\`\`(\\w+)?\\n([\\s\\S]*?)\`\`\`/g, '<pre><code>$2</code></pre>')
        .replace(/\`([^\`]+)\`/g, '<code>$1</code>')
        .replace(/\\n/g, '<br>');
    }

    function streamAssistantChunk(chunk) {
      if (!currentMessage) {
        currentMessage = appendMessage('assistant', '');
      }
      const content = currentMessage.innerHTML;
      currentMessage.innerHTML = content + chunk;
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function finishAssistantMessage(content) {
      if (!currentMessage) {
        appendMessage('assistant', content);
      }
      currentMessage = null;
      hideCancel();
    }

    function hideCancel() {
      cancelButton.style.display = 'none';
      sendButton.style.display = 'block';
      isStreaming = false;
    }

    function sendMessage() {
      const message = messageInput.value.trim();
      if (!message || isStreaming) return;

      appendMessage('user', message);
      messageInput.value = '';
      isStreaming = true;
      sendButton.style.display = 'none';
      cancelButton.style.display = 'block';
      currentMessage = null;

      vscode.postMessage({
        type: 'userMessage',
        content: message
      });
    }

    sendButton.addEventListener('click', sendMessage);
    cancelButton.addEventListener('click', () => {
      vscode.postMessage({ type: 'cancelRequest' });
      hideCancel();
    });

    messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', () => {
      messageInput.style.height = 'auto';
      messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
    });
  </script>
</body>
</html>`;
  }

  public dispose() {
    this.panel?.dispose();
    this.disposables.forEach(d => d.dispose());
  }
}
