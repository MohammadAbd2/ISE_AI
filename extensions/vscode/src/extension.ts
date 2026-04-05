import * as vscode from 'vscode';
import { ISEAIProvider } from './provider';
import { ChatPanel } from './chatPanel';
import { InlineCompletionProvider } from './inlineCompletion';
import { CodeActionProvider } from './codeActions';

let chatPanel: ChatPanel | undefined;
let inlineCompletionProvider: InlineCompletionProvider | undefined;
let codeActionProvider: CodeActionProvider | undefined;

export function activate(context: vscode.ExtensionContext) {
  console.log('ISE AI Copilot is now active!');

  const provider = new ISEAIProvider(context);
  chatPanel = new ChatPanel(context, provider);
  inlineCompletionProvider = new InlineCompletionProvider(provider);
  codeActionProvider = new CodeActionProvider(provider);

  // Register commands
  registerCommands(context, provider);

  // Register inline completion provider
  if (inlineCompletionProvider) {
    const config = vscode.workspace.getConfiguration('ise-ai-copilot');
    if (config.get('enableGhostCompletion')) {
      vscode.languages.registerInlineCompletionItemProvider(
        { pattern: '**/*' },
        inlineCompletionProvider
      );
    }
  }

  // Register code action provider
  if (codeActionProvider) {
    vscode.languages.registerCodeActionsProvider(
      { pattern: '**/*.{ts,tsx,js,jsx,py,java,go,rs,cpp,c}' },
      codeActionProvider
    );
  }

  // Show welcome notification
  vscode.window.showInformationMessage(
    'ISE AI Copilot is ready! Press Ctrl+Shift+I (Cmd+Shift+I on Mac) to open chat.',
    'Open Chat'
  ).then(selection => {
    if (selection === 'Open Chat') {
      chatPanel?.show();
    }
  });
}

function registerCommands(context: vscode.ExtensionContext, provider: ISEAIProvider) {
  // Open Chat Panel
  context.subscriptions.push(
    vscode.commands.registerCommand('ise-ai-copilot.chat', () => {
      chatPanel?.show();
    })
  );

  // Inline Chat
  context.subscriptions.push(
    vscode.commands.registerCommand('ise-ai-copilot.inline-chat', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
      }

      const selection = editor.selection;
      const selectedText = editor.document.getText(selection);

      const message = await vscode.window.showInputBox({
        prompt: 'Ask ISE AI...',
        placeHolder: 'What would you like to do?',
        value: selectedText ? `Selected: ${selectedText.substring(0, 50)}...` : undefined
      });

      if (message) {
        await provider.sendRequest(message, {
          file: editor.document.fileName,
          language: editor.document.languageId,
          selection: selectedText,
          cursor: editor.selection.active
        });
      }
    })
  );

  // Explain Code
  context.subscriptions.push(
    vscode.commands.registerCommand('ise-ai-copilot.explain', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;

      const selectedText = editor.document.getText(editor.selection);
      if (!selectedText) {
        vscode.window.showWarningMessage('Please select code to explain');
        return;
      }

      const prompt = `Explain this code:\n\n\`\`\`${editor.document.languageId}\n${selectedText}\n\`\`\``;
      chatPanel?.show();
      chatPanel?.sendMessage(prompt);
    })
  );

  // Refactor Code
  context.subscriptions.push(
    vscode.commands.registerCommand('ise-ai-copilot.refactor', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;

      const selectedText = editor.document.getText(editor.selection);
      if (!selectedText) {
        vscode.window.showWarningMessage('Please select code to refactor');
        return;
      }

      const prompt = `Refactor this code to improve readability and performance:\n\n\`\`\`${editor.document.languageId}\n${selectedText}\n\`\`\``;
      chatPanel?.show();
      chatPanel?.sendMessage(prompt);
    })
  );

  // Generate Tests
  context.subscriptions.push(
    vscode.commands.registerCommand('ise-ai-copilot.generate-tests', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;

      const document = editor.document;
      const prompt = `Generate comprehensive unit tests for this ${document.languageId} code:\n\n\`\`\`${document.languageId}\n${document.getText()}\n\`\`\``;
      
      chatPanel?.show();
      chatPanel?.sendMessage(prompt);
    })
  );

  // Fix Errors
  context.subscriptions.push(
    vscode.commands.registerCommand('ise-ai-copilot.fix-errors', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;

      const diagnostics = vscode.languages.getDiagnostics(editor.document.uri);
      const errors = diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Error);

      if (errors.length === 0) {
        vscode.window.showInformationMessage('No errors found in current file');
        return;
      }

      const errorMessages = errors.map(e => e.message).join('\n');
      const prompt = `Fix these errors in the code:\n\nErrors:\n${errorMessages}\n\nCode:\n\`\`\`${editor.document.languageId}\n${editor.document.getText()}\n\`\`\``;
      
      chatPanel?.show();
      chatPanel?.sendMessage(prompt);
    })
  );

  // Optimize Code
  context.subscriptions.push(
    vscode.commands.registerCommand('ise-ai-copilot.optimize', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;

      const selectedText = editor.document.getText(editor.selection);
      if (!selectedText) {
        vscode.window.showWarningMessage('Please select code to optimize');
        return;
      }

      const prompt = `Optimize this code for better performance and efficiency:\n\n\`\`\`${editor.document.languageId}\n${selectedText}\n\`\`\``;
      chatPanel?.show();
      chatPanel?.sendMessage(prompt);
    })
  );

  // Generate Documentation
  context.subscriptions.push(
    vscode.commands.registerCommand('ise-ai-copilot.document', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;

      const selectedText = editor.document.getText(editor.selection);
      if (!selectedText) {
        vscode.window.showWarningMessage('Please select code to document');
        return;
      }

      const prompt = `Generate comprehensive documentation for this code:\n\n\`\`\`${editor.document.languageId}\n${selectedText}\n\`\`\``;
      chatPanel?.show();
      chatPanel?.sendMessage(prompt);
    })
  );

  // Configure
  context.subscriptions.push(
    vscode.commands.registerCommand('ise-ai-copilot.configure', () => {
      vscode.commands.executeCommand(
        'workbench.action.openSettings',
        'ise-ai-copilot'
      );
    })
  );
}

export function deactivate() {
  chatPanel?.dispose();
}
