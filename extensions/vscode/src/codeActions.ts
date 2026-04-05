import * as vscode from 'vscode';
import { ISEAIProvider } from './provider';

export class CodeActionProvider implements vscode.CodeActionProvider {
  public static readonly providedCodeActionKinds = [
    vscode.CodeActionKind.QuickFix,
    vscode.CodeActionKind.Refactor,
    vscode.CodeActionKind.Source
  ];

  private provider: ISEAIProvider;

  constructor(provider: ISEAIProvider) {
    this.provider = provider;
  }

  provideCodeActions(
    document: vscode.TextDocument,
    range: vscode.Range | vscode.Selection,
    context: vscode.CodeActionContext,
    token: vscode.CancellationToken
  ): vscode.CodeAction[] {
    const actions: vscode.CodeAction[] = [];

    // Add quick fix for errors
    if (context.diagnostics.length > 0) {
      const fixAction = this.createFixAction(document, range, context);
      if (fixAction) {
        actions.push(fixAction);
      }
    }

    // Add refactor action
    const refactorAction = this.createRefactorAction(document, range);
    if (refactorAction) {
      actions.push(refactorAction);
    }

    // Add explain action
    const explainAction = this.createExplainAction(document, range);
    if (explainAction) {
      actions.push(explainAction);
    }

    return actions;
  }

  private createFixAction(
    document: vscode.TextDocument,
    range: vscode.Range,
    context: vscode.CodeActionContext
  ): vscode.CodeAction | null {
    const errors = context.diagnostics.filter(
      d => d.severity === vscode.DiagnosticSeverity.Error
    );

    if (errors.length === 0) {
      return null;
    }

    const action = new vscode.CodeAction(
      'ISE AI: Fix Errors',
      vscode.CodeActionKind.QuickFix
    );

    action.command = {
      command: 'ise-ai-copilot.fix-errors',
      title: 'Fix Errors with ISE AI'
    };

    return action;
  }

  private createRefactorAction(
    document: vscode.TextDocument,
    range: vscode.Range
  ): vscode.CodeAction | null {
    const action = new vscode.CodeAction(
      'ISE AI: Refactor',
      vscode.CodeActionKind.Refactor
    );

    action.command = {
      command: 'ise-ai-copilot.refactor',
      title: 'Refactor with ISE AI'
    };

    return action;
  }

  private createExplainAction(
    document: vscode.TextDocument,
    range: vscode.Range
  ): vscode.CodeAction | null {
    const action = new vscode.CodeAction(
      'ISE AI: Explain',
      vscode.CodeActionKind.QuickFix
    );

    action.command = {
      command: 'ise-ai-copilot.explain',
      title: 'Explain with ISE AI'
    };

    return action;
  }
}
