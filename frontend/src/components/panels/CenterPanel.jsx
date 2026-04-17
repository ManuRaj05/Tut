import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { getWelcomeMessage } from '../../services/chatService';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Sparkles, Send, Bot, User, Download } from 'lucide-react';
import './CenterPanel.css';

const DJANGO_BASE_URL = "http://127.0.0.1:8000/api";

const MarkdownComponents = {
    p: ({ children }) => <div className="mb-4 last:mb-0 leading-relaxed text-[15px]">{children}</div>,
    code: ({ inline, children }) => (
        inline 
            ? <code className="bg-gray-800 px-1.5 py-0.5 rounded text-indigo-300 font-mono text-sm">{children}</code>
            : <div className="my-4 rounded-xl overflow-hidden bg-gray-900 border border-gray-800">
                <pre className="p-4 overflow-x-auto font-mono text-sm text-indigo-100"><code>{children}</code></pre>
              </div>
    ),
    ul: ({ children }) => <ul className="list-disc ml-6 mb-4 space-y-2">{children}</ul>,
    ol: ({ children }) => <ol className="list-decimal ml-6 mb-4 space-y-2">{children}</ol>,
    li: ({ children }) => <li className="pl-1 text-[15px]">{children}</li>,
    
    // TABLES
    table: ({ children }) => (
        <div className="my-6 overflow-x-auto rounded-xl border border-gray-800 bg-gray-900/40 shadow-inner">
            <table className="w-full border-collapse text-left text-sm">
                {children}
            </table>
        </div>
    ),
    thead: ({ children }) => <thead className="bg-gray-800/60 text-indigo-300 font-bold uppercase tracking-wider">{children}</thead>,
    th: ({ children }) => <th className="px-5 py-3 border-b border-gray-800">{children}</th>,
    td: ({ children }) => <td className="px-5 py-3 border-b border-gray-700/30 text-gray-400">{children}</td>,
    tr: ({ children }) => <tr className="hover:bg-indigo-500/5 transition-colors">{children}</tr>,
};

const CenterPanel = () => {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const navigate = useNavigate();

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    useEffect(() => {
        const initChat = async () => {
            const welcomeData = await getWelcomeMessage();
            if (welcomeData && welcomeData.message) {
                setMessages([{ sender: 'bot', text: welcomeData.message, recommendedTopic: welcomeData.recommended_topic }]);
            } else {
                setMessages([{ sender: 'bot', text: 'Welcome to Cobra Tutor! What Python topic would you like to learn today?' }]);
            }
        };
        initChat();
    }, []);

    const callMainAgentApi = async (message) => {
        const tokenData = localStorage.getItem("user");
        const token = tokenData ? JSON.parse(tokenData).access : null;
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        try {
            const response = await axios.post(`${DJANGO_BASE_URL}/main-agent/chat/`, { message }, { headers });
            return response.data;
        } catch (error) {
            console.error("Agent API Error:", error);
            const errorMsg = error.response?.data?.error || "Failed to reach the agent.";
            return { reply: `Error: ${errorMsg}` };
        }
    };

    const handleSendMessage = async (e, directText = null) => {
        if (e) e.preventDefault();
        const userText = directText || inputMessage;
        if (!userText.trim() || loading) return;

        setMessages(prev => [...prev, { sender: 'user', text: userText }]);
        if (!directText) setInputMessage('');
        setLoading(true);

        try {
            const data = await callMainAgentApi(userText);
            setMessages(prev => [...prev, { sender: 'bot', text: data.reply }]);

            // Handle Actions
            if (data.action && data.action.type === 'SWITCH_TAB') {
                setTimeout(() => {
                    const topicStr = encodeURIComponent(data.action.data?.topic || '');
                    if (data.action.view === 'tutor') navigate(`/agent-tutor`, { state: { topic: data.action.data?.topic, initialMessage: data.reply } });
                    if (data.action.view === 'code') navigate(`/agent-code?topic=${topicStr}`);
                    if (data.action.view === 'debugger') navigate(`/agent-debugger?topic=${topicStr}`);
                    if (data.action.view === 'quiz') navigate(`/agent-quiz?topic=${topicStr}`);
                }, 1500);
            }
        } catch (err) {
            setMessages(prev => [...prev, { sender: 'bot', text: "Something went wrong." }]);
        } finally {
            setLoading(false);
        }
    };

    const downloadChat = () => {
        if (messages.length === 0) return;
        
        let content = "=== COBRA TUTOR CHAT LOG ===\n\n";
        messages.forEach((msg, index) => {
            const sender = msg.sender === 'bot' ? "COBRA TUTOR" : "USER";
            content += `[${sender}]\n${msg.text}\n\n`;
        });
        
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `CobraTutor_Chat_${new Date().toISOString().slice(0,10)}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="center-panel flex flex-col h-full relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h2 className="mb-0">Cobra Tutor Intelligence</h2>
                <button
                    onClick={downloadChat}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-800/50 hover:bg-gray-800 border border-gray-700/50 text-gray-400 hover:text-indigo-400 transition-all text-xs font-semibold group shadow-lg backdrop-blur-sm"
                    title="Download Chat Log"
                >
                    <Download size={14} className="group-hover:-translate-y-0.5 transition-transform" />
                    <span>Download Chat</span>
                </button>
            </div>


            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto px-0 py-4 relative z-10 custom-scrollbar">
                <div className="max-w-3xl mx-auto space-y-10">
                    {messages.map((msg, index) => (
                        <div key={index} className={`flex w-full gap-4 ${msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'} animate-message-in`}>
                            {/* Avatar */}
                            <div className={`flex-shrink-0 h-10 w-10 rounded-2xl flex items-center justify-center border shadow-sm ${
                                msg.sender === 'bot' 
                                    ? 'bg-gray-900 border-gray-800 text-indigo-400' 
                                    : 'bg-gradient-to-br from-indigo-500 to-purple-600 border-transparent text-white'
                            }`}>
                                {msg.sender === 'bot' ? <Bot size={20} /> : <User size={20} />}
                            </div>

                            {/* Message Content Area */}
                            <div className={`flex flex-col gap-2 max-w-[85%] ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                                <div className={`px-6 py-4 shadow-xl ${
                                    msg.sender === 'user'
                                        ? 'bg-gray-800/80 text-white rounded-3xl rounded-tr-none border border-gray-700/50 backdrop-blur-sm'
                                        : 'bg-gray-900/50 text-gray-200 rounded-3xl rounded-tl-none border border-indigo-500/20 backdrop-blur-xl'
                                }`}>
                                    <div className={`prose prose-invert max-w-none`}>
                                        {msg.sender === 'user' ? (
                                            <div className="whitespace-pre-wrap text-[15px]">{msg.text}</div>
                                        ) : (
                                            <ReactMarkdown 
                                                remarkPlugins={[remarkGfm]} 
                                                components={MarkdownComponents}
                                            >
                                                {msg.text}
                                            </ReactMarkdown>
                                        )}
                                    </div>
                                </div>

                                {/* Recommendation Button Hook */}
                                {msg.recommendedTopic && index === 0 && (
                                    <div className="mt-2 flex">
                                        <button
                                            onClick={() => handleSendMessage(null, `Let's start with ${msg.recommendedTopic}`)}
                                            className="group relative flex items-center gap-2 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 px-5 py-2.5 rounded-2xl text-sm font-semibold transition-all duration-300"
                                        >
                                            <Sparkles size={16} className="group-hover:animate-pulse" />
                                            <span>Start: {msg.recommendedTopic}</span>
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* Loading Indicator */}
                    {loading && (
                        <div className="flex w-full gap-4 animate-fade-in">
                            <div className="flex-shrink-0 h-10 w-10 rounded-2xl bg-gray-900 border border-gray-800 flex items-center justify-center text-indigo-400 shadow-sm">
                                <Bot size={20} />
                            </div>
                            <div className="px-6 py-4 bg-gray-900/30 rounded-3xl rounded-tl-none border border-indigo-500/10 backdrop-blur-xl flex items-center gap-2">
                                <span className="flex gap-1.5">
                                    <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                    <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                    <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"></span>
                                </span>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Wrapper */}
            <div className="pt-6 relative z-20">
                <div className="max-w-3xl mx-auto">
                    <form
                        className="relative flex items-center group transition-all"
                        onSubmit={(e) => handleSendMessage(e)}
                    >
                        <input
                            type="text"
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            placeholder="Type your question here or ask for a topic..."
                            disabled={loading}
                            className="w-full bg-gray-900/50 border border-gray-800 text-gray-100 rounded-3xl pl-7 pr-16 py-5 text-[15px] focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500/50 focus:bg-gray-900/80 transition-all shadow-2xl disabled:opacity-60 placeholder:text-gray-500"
                        />
                        <button
                            type="submit"
                            disabled={loading || !inputMessage.trim()}
                            className="absolute right-3 p-3 rounded-2xl bg-indigo-500 text-white font-medium hover:bg-indigo-400 transition-all duration-300 disabled:opacity-20 disabled:grayscale hover:scale-105 active:scale-95 flex items-center justify-center shadow-lg shadow-indigo-500/30"
                        >
                            <Send size={20} />
                        </button>
                    </form>
                    <p className="mt-3 text-center text-[10px] text-gray-500 font-medium tracking-widest uppercase opacity-60">
                        Cobra LLM v2.0 • Real-time Assistance
                    </p>
                </div>
            </div>
        </div>
    );
};

export default CenterPanel;