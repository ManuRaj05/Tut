import React, { useEffect, useRef } from 'react';

import { RefreshCw } from 'lucide-react';


const VisualizerRenderer = ({ htmlContent, onRegenerate, isRegenerating }) => {
    const iframeRef = useRef(null);

    // srcDoc approach avoids "root already declared" issues by resetting context
    // No useEffect needed for writing content


    if (!htmlContent) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 p-6 text-center">
                <div className="w-16 h-16 mb-4 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                    <svg className="w-8 h-8 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                </div>
                <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-1">No Active Visualizer</h3>
                <p className="text-xs max-w-[200px]">When the Tutor explains a complex topic (like Sorting or Graphs), interactive visuals will appear here automatically.</p>
            </div>
        );
    }

    return (
        <div className="w-full h-full bg-slate-50 dark:bg-slate-900 overflow-hidden relative">
            <iframe
                key={htmlContent.length + htmlContent.slice(0, 50)} // Force re-mount on content change
                ref={iframeRef}
                title="Visualizer"
                className="w-full h-full border-none"
                srcDoc={htmlContent}
                sandbox="allow-scripts allow-forms allow-modals allow-same-origin" 
            />
            {/* Regenerate Button */}
            {onRegenerate && (
                <button
                    onClick={onRegenerate}
                    disabled={isRegenerating}
                    className="absolute top-4 right-4 p-2 bg-indigo-600 text-white rounded-lg shadow-lg hover:bg-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed z-10 flex items-center gap-2"
                    title="Regenerate Visualization"
                >
                    <RefreshCw className={`w-4 h-4 ${isRegenerating ? 'animate-spin' : ''}`} />
                    <span className="text-xs font-semibold">Regenerate</span>
                </button>
            )}
        </div>
    );
};

export default VisualizerRenderer;
