// CodeEditor.jsx
import React, { useState, useRef } from "react";
import Editor from "@monaco-editor/react";

export default function CodeEditor({ code = "", setCode, readOnly = false, className = "" }) {
  const [copied, setCopied] = useState(false);
  const editorRef = useRef(null);

  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;

    // Register Inline Completion Provider for AI Autocomplete
    monaco.languages.registerInlineCompletionsProvider("python", {
      provideInlineCompletions: async (model, position, context, token) => {
        // Skip if no aiWorker attached by PairCodingPanel
        if (!window.aiWorker) {
          return { items: [] };
        }

        const textBeforeCursor = model.getValueInRange({
          startLineNumber: 1,
          startColumn: 1,
          endLineNumber: position.lineNumber,
          endColumn: position.column
        });

        // Add a small delay/debounce if desired, but for now we query the worker
        return new Promise((resolve) => {
          const reqId = Math.random().toString(36).substring(7);

          const handleMsg = (e) => {
            if (e.data.id === reqId && (e.data.status === 'complete' || e.data.status === 'error')) {
              window.aiWorker.removeEventListener("message", handleMsg);
              
              if (e.data.status === 'error' || !e.data.output) {
                resolve({ items: [] });
              } else {
                resolve({
                  items: [{
                    insertText: e.data.output,
                    range: new monaco.Range(position.lineNumber, position.column, position.lineNumber, position.column)
                  }]
                });
              }
            }
          };

          window.aiWorker.addEventListener("message", handleMsg);
          window.aiWorker.postMessage({ id: reqId, text: textBeforeCursor });
        });
      },
      freeInlineCompletions: () => {}
    });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.warn("Failed to copy code:", err);
    }
  };

  const handleReset = () => {
    if (setCode && typeof setCode === "function") {
      setCode("");
    }
  };

  return (
    <div
      className={`flex flex-col border border-gray-300 dark:border-gray-700 rounded-xl overflow-hidden bg-white dark:bg-gray-900 shadow-sm ${className}`}
      style={{ height: "100%" }}
    >
      {/* Minimal Toolbar (Python-focused) */}
      {!readOnly && (
        <div className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200/50 dark:border-gray-700/50 text-sm">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300 rounded">
              Python
            </span>
          </div>
          <div className="flex gap-1.5">
            <button
              onClick={handleCopy}
              title="Copy code"
              className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              {copied ? (
                <span className="text-green-600 dark:text-green-400 text-xs font-bold">✓ Copied</span>
              ) : (
                <span className="text-gray-600 dark:text-gray-400 text-sm">📋 Copy</span>
              )}
            </button>
            <button
              onClick={handleReset}
              title="Clear code"
              className="text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300 p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors text-sm"
            >
              🗑️ Clear
            </button>
          </div>
        </div>
      )}

      {/* Monaco Editor — Python Only */}
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          language="python"
          value={code}
          onChange={(value) => setCode?.(value || "")}
          theme={document.documentElement.classList.contains("dark") ? "vs-dark" : "vs"}
          onMount={handleEditorDidMount}
          options={{
            readOnly,
            minimap: { enabled: false },
            fontSize: 15,
            tabSize: 4,               // Python standard
            insertSpaces: true,       // PEP 8 compliant
            wordWrap: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,    // ✅ Critical for responsive resizing
            smoothScrolling: true,
            lineNumbers: "on",
            roundedSelection: true,
            padding: { top: 12, bottom: 12 },
            folding: true,
            renderLineHighlight: "gutter",
            quickSuggestions: { other: true, comments: false, strings: false },
            suggest: {
              showIcons: true,
              showMethods: true,
              showFunctions: true,
            },
            // Python-specific: enable snippets and autocomplete
            snippetSuggestions: "top",
            suggestOnTriggerCharacters: true,
          }}
        />
      </div>
    </div>
  );
}