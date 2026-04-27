# ISE Agent JetBrains Bridge

This refreshed tool window detects the opened JetBrains project through `project.basePath`, sends an Agent instruction plus the relative file path to `/api/devx/ide/rewrite-file`, receives the full rewritten source, and applies it to `src/App.jsx` using `WriteCommandAction`.

Run backend on `127.0.0.1:8000`, open a React project, type for example:

```text
rewrite the component App.jsx in a better way
```

Then click **Apply Agent edit to current project**. The editor document is updated and saved immediately.
