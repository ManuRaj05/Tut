import React, { useEffect, useState } from 'react';
import ReactFlow, {
    Controls,
    Background,
    applyNodeChanges,
    applyEdgeChanges,
    Handle,
    Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import axios from 'axios';

// Custom Node to dynamically style based on mastery
const ConceptNode = ({ data }) => {
    let bgColor = 'bg-slate-700'; // Default (Locked or low mastery)
    let borderColor = 'border-slate-500';
    let textColor = 'text-slate-300';

    if (data.status === 'mastered') {
        bgColor = 'bg-emerald-900/60';
        borderColor = 'border-emerald-500';
        textColor = 'text-emerald-100';
    } else if (data.status === 'in-progress') {
        bgColor = 'bg-amber-900/60';
        borderColor = 'border-amber-500';
        textColor = 'text-amber-100';
    }

    return (
        <div className={`px-4 py-2 shadow-lg rounded-md border-2 ${bgColor} ${borderColor} ${textColor} text-sm font-semibold text-center min-w-[120px]`}>
            <Handle type="target" position={Position.Top} className="!bg-slate-500" />
            <div>{data.label}</div>
            {data.mastery !== undefined && (
                <div className="flex flex-col gap-1 mt-2 border-t border-slate-500/30 pt-2 w-full">
                    <div className="text-xs font-bold text-center mb-1">
                        Mastery: {(data.mastery * 100).toFixed(0)}%
                    </div>
                    {data.understanding !== undefined && (
                        <div className="flex justify-between text-[10px] font-normal opacity-90">
                            <span>Theory:</span>
                            <span>{(data.understanding * 100).toFixed(0)}%</span>
                        </div>
                    )}
                    {data.application !== undefined && (
                        <div className="flex justify-between text-[10px] font-normal opacity-90">
                            <span>Code:</span>
                            <span>{(data.application * 100).toFixed(0)}%</span>
                        </div>
                    )}
                    {data.reasoning !== undefined && (
                        <div className="flex justify-between text-[10px] font-normal opacity-90">
                            <span>Debug:</span>
                            <span>{(data.reasoning * 100).toFixed(0)}%</span>
                        </div>
                    )}
                </div>
            )}
            <Handle type="source" position={Position.Bottom} className="!bg-slate-500" />
        </div>
    );
};

const nodeTypes = {
    default: ConceptNode,
};

const KnowledgeGraph = () => {
    const [nodes, setNodes] = useState([]);
    const [edges, setEdges] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchGraphData = async () => {
            try {
                const userDataString = localStorage.getItem('user');
                // The backend uses JWT, so usually .access or .token
                const token = userDataString ? (JSON.parse(userDataString).access || JSON.parse(userDataString).token) : null;

                if (!token) throw new Error("Please log in to view your Knowledge Graph.");

                const res = await axios.get('http://localhost:8000/api/chat/gkt/graph/', {
                    headers: {
                        Authorization: `Bearer ${token}`
                    }
                });

                if (res.data) {
                    setNodes(res.data.nodes || []);
                    setEdges(res.data.edges || []);
                }
            } catch (err) {
                console.error("Knowledge Graph Error:", err);
                setError(err.response?.data?.error || err.message || "Failed to load graph data.");
            } finally {
                setLoading(false);
            }
        };

        fetchGraphData();
    }, []);

    const onNodesChange = (changes) => setNodes((nds) => applyNodeChanges(changes, nds));
    const onEdgesChange = (changes) => setEdges((eds) => applyEdgeChanges(changes, eds));

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-slate-900 text-white">
                <div className="text-center animate-pulse">
                    <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-slate-400">Loading your knowledge universe...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-screen bg-slate-900 text-white p-6">
                <div className="bg-red-900/30 border border-red-500 rounded-lg p-6 max-w-md text-center">
                    <h2 className="text-xl font-bold text-red-400 mb-2">Error</h2>
                    <p className="text-slate-300">{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col w-screen h-screen bg-slate-900 text-white">
            <div className="p-4 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm z-10 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                        Your Knowledge Graph
                    </h1>
                    <p className="text-sm text-slate-400">Visual mapping of your conceptual mastery.</p>
                </div>

                {/* Legend */}
                <div className="flex gap-4 text-xs font-semibold bg-slate-800/50 p-2 rounded-md border border-slate-700">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                        <span className="text-emerald-100">Mastered</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]"></div>
                        <span className="text-amber-100">In Progress</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-slate-600"></div>
                        <span className="text-slate-300">Locked</span>
                    </div>
                </div>
            </div>

            <div className="flex-grow w-full relative">
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    nodeTypes={nodeTypes}
                    fitView
                    attributionPosition="bottom-right"
                    className="bg-slate-900"
                >
                    <Background color="#334155" gap={24} size={2} />
                    <Controls className="!bg-slate-800 !border-slate-700 !fill-slate-300" />
                </ReactFlow>
            </div>
        </div>
    );
};

export default KnowledgeGraph;
