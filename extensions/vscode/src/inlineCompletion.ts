import * as vscode from 'vscode';
import { ISEAIProvider } from './provider';

export class InlineCompletionProvider implements vscode.InlineCompletionItemProvider {
  private provider: ISEAIProvider;
  private lastCompletion: string = '';
  private debounceTimer: NodeJS.Timeout | null = null;

  constructor(provider: ISEAIProvider) {
    this.provider = provider;
  }

  async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    context: vscode.InlineCompletionContext,
    token: vscode.CancellationToken
  ): Promise<vscode.InlineCompletionItem[] | null> {
    const config = vscode.workspace.getConfiguration('ise-ai-copilot');
    if (!config.get('enableGhostCompletion')) {
      return null;
    }

    if (!config.get('enableAutoComplete')) {
      return null;
    }

    // Debounce completions
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    return new Promise((resolve) => {
      this.debounceTimer = setTimeout(async () => {
        try {
          const completion = await this.getCompletion(document, position, token);
          if (completion && completion.trim()) {
            this.lastCompletion = completion;
            resolve([
              new vscode.InlineCompletionItem(
                completion,
                new vscode.Range(position, position)
              )
            ]);
          } else {
            resolve(null);
          }
        } catch (error) {
          console.error('Error providing inline completion:', error);
          resolve(null);
        }
      }, config.get('completionDelay', 300));
    });
  }

  private async getCompletion(
    document: vscode.TextDocument,
    position: vscode.Position,
    token: vscode.CancellationToken
  ): Promise<string | null> {
    const line = document.lineAt(position.line);
    const prefix = document.getText(
      new vscode.Range(new vscode.Position(0, 0), position)
    );
    const suffix = document.getText(
      new vscode.Range(position, new vscode.Position(document.lineCount - 1, document.lineAt(document.lineCount - 1).text.length))
    );

    // Only request completion if there's some prefix
    if (prefix.trim().length < 3) {
      return null;
    }

    try {
      const completion = await this.provider.getCompletion(prefix, suffix, position);
      return completion;
    } catch (error) {
      console.error('Error getting completion:', error);
      return null;
    }
  }

  handleDidAcceptCompletionItem(): void {
    // Track acceptance for telemetry (if enabled)
    const config = vscode.workspace.getConfiguration('ise-ai-copilot');
    if (config.get('enableTelemetry')) {
      // Send acceptance telemetry
    }
  }

  handleDidPartiallyAcceptCompletionItem(acceptedLength: number): void {
    // Track partial acceptance
  }
}
