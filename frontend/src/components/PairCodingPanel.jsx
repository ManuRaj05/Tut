import React, { useState, useEffect, useRef, useMemo } from 'react';
import CodeEditor from './CodeEditor';
import AIWorker from '../workers/aiWorker?worker';

export default function PairCodingPanel({ codingTask }) {
    const [code, setCode] = useState(codingTask?.starter_code || "");
    const [modelStatus, setModelStatus] = useState('Initiating Pair Coder...');
    const [isReady, setIsReady] = useState(false);
    const workerRef = useRef(null);

    // Generate a unique identifier on mount
    const uid = useMemo(() => Math.random().toString(36).substring(7), []);

    useEffect(() => {
        if (!workerRef.current) {
            // Instantiate worker using Vite's native bundler plugin
            workerRef.current = new AIWorker();
            window.aiWorker = workerRef.current;

            // Post 'load' event to force initialization downloading
            workerRef.current.postMessage({ type: 'load' });

            workerRef.current.onmessage = (e) => {
                const { status, data, error } = e.data;
                if (status === 'progress') {
                    setModelStatus(`Loading AI Pair Coder... (${Math.round(data.progress || 0)}%)`);
                } else if (status === 'ready') {
                    setModelStatus('Ready');
                    setIsReady(true);
                } else if (status === 'error') {
                    setModelStatus(`Model Error: ${error}`);
                }
            };

            workerRef.current.onerror = (err) => {
                setModelStatus(`Worker Boot Error: Failed to load module`);
                console.error("Worker Boot Error:", err);
            };
        }

        return () => {
            if (workerRef.current) {
                workerRef.current.terminate();
                window.aiWorker = null;
            }
        };
    }, []);

    const handleCodeChange = (newCode) => {
        setCode(newCode);
    };

    return (
        <div className="flex flex-col h-full bg-slate-900 border-l border-slate-800">
            {/* Header */}
            <div className="p-4 border-b border-indigo-900/30 bg-slate-900 flex justify-between items-center shrink-0">
                <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${isReady ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : 'bg-amber-500 animate-pulse'}`} />
                    <h2 className="font-bold text-slate-200">Practice Sandbox</h2>
                </div>
                <div className="text-xs text-slate-500 font-mono px-3 py-1 bg-slate-800 rounded-full border border-slate-700">
                    {modelStatus}
                </div>
            </div>

            {/* Task View */}
            {codingTask && (
                <div className="p-4 bg-indigo-900/10 border-b border-indigo-900/30 shrink-0">
                    <p className="text-xs text-indigo-400 font-bold mb-1 uppercase tracking-wider text-center">Current Task</p>
                    <p className="text-sm text-slate-300 bg-black/20 p-3 rounded-lg border border-slate-800 whitespace-pre-wrap leading-relaxed shadow-inner font-medium font-mono text-center">
                        {codingTask.instructions}
                    </p>
                </div>
            )}

            {/* Editor Wrapper */}
            <div className="flex-1 min-h-0 bg-slate-950 p-2 relative">
                {/* 
                    Ideally, we'd inject monaco.languages.registerInlineCompletionsProvider here.
                    To keep things React-clean, we pass the worker ref to the editor or wait until 
                    implementation inside CodeEditor.jsx handles it via a global window ref.
                */}
                <CodeEditor code={code} setCode={handleCodeChange} />
                
                {/* Floating "Pair Coding Active" Indicator */}
                {isReady && (
                    <div className="absolute bottom-4 right-4 bg-indigo-600 border border-t border-l border-indigo-500 rounded-tl-xl text-[10px] text-white px-2 py-0.5 shadow-lg select-none opacity-50 z-50">
                        ⚡ AI AutoComplete ON
                    </div>
                )}
            </div>
            
            {/* Footer / Controls */}
            <div className="p-3 bg-slate-900 border-t border-slate-800 shrink-0 flex gap-2">
                <button className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 rounded-lg transition-all shadow-lg active:scale-95 text-sm uppercase tracking-wide">
                    Submit Answer
                </button>
            </div>
        </div>
    );
}
