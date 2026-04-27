const vscode = require('vscode');

async function postJson(url, body){
  const res = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!res.ok) throw new Error(await res.text());
  return res.json();
}

function relPath(root, file){
  return file.startsWith(root) ? file.slice(root.length).replace(/^[/\\]/,'') : file;
}

function activate(context){
  context.subscriptions.push(vscode.commands.registerCommand('iseAi.openPanel', () => {
    const panel = vscode.window.createWebviewPanel('iseAiAgent','ISE AI Agent',vscode.ViewColumn.Beside,{enableScripts:true});
    panel.webview.html = `<html><body style="font-family:system-ui;padding:16px"><h2>ISE AI Agent</h2><p>Use “Rewrite Current File with Agent” to apply real edits directly to your workspace.</p></body></html>`;
  }));

  context.subscriptions.push(vscode.commands.registerCommand('iseAi.rewriteCurrentFile', async () => {
    const editor = vscode.window.activeTextEditor;
    if(!editor) return vscode.window.showWarningMessage('Open a file first.');
    const backend = vscode.workspace.getConfiguration('iseAi').get('backendUrl') || 'http://127.0.0.1:8000';
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if(!root) return vscode.window.showWarningMessage('Open a workspace folder first.');
    const instruction = await vscode.window.showInputBox({prompt:'Agent instruction', value:`rewrite ${relPath(root, editor.document.uri.fsPath)} in a better way`});
    if(!instruction) return;
    const result = await postJson(`${backend}/api/devx/ide/rewrite-file`, {project_path:root, relative_path:relPath(root, editor.document.uri.fsPath), instruction});
    const full = new vscode.Range(editor.document.positionAt(0), editor.document.positionAt(editor.document.getText().length));
    await editor.edit(edit => edit.replace(full, result.content));
    await editor.document.save();
    vscode.window.showInformationMessage(`ISE Agent updated ${result.relative_path}`);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('iseAi.sendSelection', async () => {
    const editor = vscode.window.activeTextEditor; if(!editor) return;
    const backend = vscode.workspace.getConfiguration('iseAi').get('backendUrl') || 'http://127.0.0.1:8000';
    const text = editor.document.getText(editor.selection) || editor.document.getText();
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if(root) await postJson(`${backend}/api/devx/workspaces`, {label:'vscode', path:root}).catch(()=>{});
    const result = await postJson(`${backend}/api/agents/plan-and-execute`, {request:`Help with this code:\n\n${text.slice(0,8000)}`, source_path:root, export_zip:true});
    vscode.window.showInformationMessage(result.summary || 'ISE AI Agent finished');
  }));
}
function deactivate(){}
module.exports = { activate, deactivate };

// v9 IDE write-back bridge:
// Send selected file content to POST /api/agentic-visual/ide/patch and apply updated_content
// with vscode.WorkspaceEdit after showing the diff preview to the user.
