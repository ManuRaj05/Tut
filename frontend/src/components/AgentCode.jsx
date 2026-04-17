import React, { useState, useRef, useEffect } from "react";
import CodeEditor from "./CodeEditor";
import { loadPyodide } from "pyodide";
import axios from "axios";
import { useLocation, useSearchParams, useNavigate } from "react-router-dom";
import VisualizerRenderer from "./VisualizerRenderer";

function HiddenHint({ code }) {
    const [revealed, setRevealed] = useState(false);
    return (
        <div className="my-2 p-3 bg-gray-800 rounded-lg border border-amber-500/30">
            {revealed ? (
                <pre className="text-xs text-amber-300 font-mono whitespace-pre-wrap">{code}</pre>
            ) : (
                <div className="flex flex-col items-center">
                    <span className="text-[10px] text-amber-500/70 font-mono mb-2">HIDDEN HINT (PASSWORD)</span>
                    <button 
                        onClick={() => setRevealed(true)}
                        className="text-xs bg-amber-600/20 hover:bg-amber-600/40 text-amber-400 px-4 py-1.5 rounded-full border border-amber-600/50 transition-all active:scale-95"
                    >
                        Reveal Step Code
                    </button>
                </div>
            )}
        </div>
    );
}

export default function AgentCode() {
    const [searchParams] = useSearchParams();
    const location = useLocation();
    const navigate = useNavigate();
    // Support both URL param and state
    const topic = searchParams.get("topic") || location.state?.topic;

    const [code, setCode] = useState(`# Write your solution here\nprint("Hello, World!")`);
    const [consoleOutput, setConsoleOutput] = useState("");
    const [assistantMessages, setAssistantMessages] = useState([]);
    const [questions, setQuestions] = useState([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(false);
    const [model] = useState("AI-1.5-flash");
    const [pyodide, setPyodide] = useState(null);
    const [testCases, setTestCases] = useState([]);
    const [planDescription, setPlanDescription] = useState("");
    const [responseMode, setResponseMode] = useState(null);
    const assistantEndRef = useRef(null);

    // Track which questions have been successfully passed locally
    const [passedQuestions, setPassedQuestions] = useState(new Set());
    
    // GUIDED MODE STATE
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [isReviewing, setIsReviewing] = useState(false);

    // VISUALIZATION STATE
    const [isVisModalOpen, setIsVisModalOpen] = useState(false);
    const [visualizationHtml, setVisualizationHtml] = useState(null);
    const [visLoading, setVisLoading] = useState(false);

    const fetchVisualization = async () => {
        if (!currentQuestion.title && !code) return;
        setVisLoading(true);
        setIsVisModalOpen(true);
        try {
            const userData = JSON.parse(localStorage.getItem("user"));
            const token = userData?.access;
            // Construct a prompt based on current context
            const prompt = `Visualize this problem: ${currentQuestion.title || "User Code"}. 
            Description: ${currentQuestion.description || "N/A"}. 
            Current Code: ${code}`;

            const res = await axios.post(
                "http://localhost:8000/api/code/vis/",
                { prompt },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            setVisualizationHtml(res.data.visualization);
        } catch (err) {
            console.error(err);
            setVisualizationHtml("<p class='text-red-500'>Failed to load visualization.</p>");
        } finally {
            setVisLoading(false);
        }
    };

    // Auto-Fetch
    useEffect(() => {
        if (topic) {
            // Auto-fetch questions for the agent's topic
            fetchQuestions(topic);
        } else {
            setPlanDescription("⚠️ No topic provided by Agent.");
        }
    }, [topic]);

    useEffect(() => {
        async function initPyodide() {
            try {
                const py = await loadPyodide({
                    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/",
                });
                setPyodide(py);
                setConsoleOutput("✅ Pyodide ready for code execution.");
            } catch (err) {
                console.error("Pyodide load error:", err);
                setConsoleOutput("❌ Failed to load Pyodide.");
            }
        }
        initPyodide();
    }, []);

    const fetchQuestions = async (userInput) => {
        setLoading(true);
        try {
            const userData = JSON.parse(localStorage.getItem("user"));
            const token = userData?.access;
            if (!token) throw new Error("User not authenticated");

            const res = await axios.post(
                "http://localhost:8000/api/code/generate-challenge/",
                { topic: userInput },
                {
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            const data = res.data;

            if (data.type === "single") {
                const question = data.question;
                setQuestions([question]);
                setTestCases(question.testcases || []);
                setPlanDescription(`🎯 ${question.title}`);
                setResponseMode("single");
                if (question.starter_code) setCode(question.starter_code);
            } else if (data.type === "plan") {
                const validQuestions = (data.questions || []).filter(
                    (q) => q.title || (q.description && q.description.trim())
                );
                setQuestions(validQuestions);
                setTestCases(validQuestions.length > 0 ? validQuestions[0].testcases || [] : []);
                setPlanDescription(data.plan || "");
                setResponseMode("plan");
                if (validQuestions[0]?.starter_code) setCode(validQuestions[0].starter_code);
            } else {
                throw new Error("Unknown response type");
            }

            setCurrentIndex(0);
        } catch (err) {
            console.error("Error fetching questions:", err.response?.data || err.message);
            setPlanDescription("⚠️ Failed to load challenge.");
            setQuestions([]);
            setTestCases([]);
            setResponseMode(null);
            setPassedQuestions(new Set());
        } finally {
            setLoading(false);
        }
    };

    const onSkip = async () => {
        if (!window.confirm("Are you sure you want to skip this challenge?")) return;
        setConsoleOutput("⏭️ Skipping challenge...");

        try {
            const userData = JSON.parse(localStorage.getItem("user"));
            const token = userData?.access;

            // Call AGENT Success Report
            const successRes = await axios.post(
                "http://127.0.0.1:8000/api/main-agent/report_success/",
                {},
                { headers: { Authorization: `Bearer ${token}` } }
            );

            setConsoleOutput((prev) => prev + "\n🤖 AGENT SAYS:\n" + successRes.data.reply + "\n");

            if (successRes.data.action) {
                const action = successRes.data.action;
                setConsoleOutput((prev) => prev + `\n🚀 Auto-navigating to ${action.view}...`);
                console.log(action, action.view)
                setTimeout(() => {
                    if (action.view === 'code') navigate(`/agent-code?topic=${encodeURIComponent(action.data?.topic)}`);
                    if (action.view === 'debugger') navigate(`/agent-debugger?topic=${encodeURIComponent(action.data?.topic)}`);
                    if (action.view === 'Gaps') navigate(`/agent-quiz?topic=${encodeURIComponent(action.data?.topic)}`);
                    if (action.view === 'tutor') navigate('/agent-tutor', { state: { initialMessage: successRes.data.reply } });
                    if (action.view === 'dashboard') navigate('/');
                }, 2000);
            } else {
                setConsoleOutput((prev) => prev + `\n🚀 Auto-navigating to Tutor...`);
                setTimeout(() => {
                    navigate('/agent-tutor', { state: { initialMessage: successRes.data.reply } });
                }, 2000);
            }
        } catch (apiErr) {
            console.error(apiErr);
            setConsoleOutput((prev) => prev + "\n⚠️ Failed to report success to Agent.");
        }
    };



    const onRun = async () => {

        if (!pyodide) {
            return setConsoleOutput("⏳ Pyodide is still loading...");
        }
        setConsoleOutput("▶ Running your code...\n");

        try {
            // 1. If NO test cases, run normally (interactive / single run)
            if (!testCases || testCases.length === 0) {
                pyodide.runPython(`
          import sys
          from io import StringIO
          sys.stdout = mystdout = StringIO()
        `);
                await pyodide.runPythonAsync(code);
                const output = pyodide.runPython("mystdout.getvalue()");
                setConsoleOutput(output || "(No output)");
                return;
            }

            // 2. If WE HAVE test cases, run them in a loop inside Python
            const testCasesJson = JSON.stringify(testCases);

            const pythonRunnerScript = `
import sys
import json
from io import StringIO

def run_tests(user_code, test_cases_json):
    cases = json.loads(test_cases_json)
    results = []
    
    for i, case in enumerate(cases):
        inp = case.get("input_data", "")
        exp = case.get("expected_output", "").strip()
        
        # PID: Prepare IO
        sys.stdin = StringIO(inp)
        sys.stdout = capture = StringIO()
        
        try:
            local_scope = {}
            exec(user_code, local_scope)
            
            actual = capture.getvalue().strip()
            params = {
                "id": i + 1,
                "input": inp,
                "expected": exp,
                "actual": actual,
                "passed": actual == exp,
                "error": None
            }
        except Exception as e:
            params = {
                "id": i + 1,
                "input": inp,
                "expected": exp,
                "actual": "",
                "passed": False,
                "error": str(e)
            }
            
        results.append(params)
    
    return json.dumps(results)

# Execute
results_json = run_tests(code_to_run, test_cases_json)
results_json
`;

            pyodide.globals.set("code_to_run", code);
            pyodide.globals.set("test_cases_json", testCasesJson);

            const rawResults = await pyodide.runPythonAsync(pythonRunnerScript);
            const results = JSON.parse(rawResults);

            let outputString = "";
            let passCount = 0;

            results.forEach((r) => {
                if (r.error) {
                    outputString += `❌ Test ${r.id} Error:\n${r.error}\n\n`;
                } else if (r.passed) {
                    passCount++;
                    outputString += `✅ Test ${r.id} Passed\nInput: ${r.input}\nExpected: ${r.expected}\nActual: ${r.actual}\n\n`;
                } else {
                    outputString += `❌ Test ${r.id} Failed\nInput: ${r.input}\nExpected: ${r.expected}\nActual: ${r.actual}\n\n`;
                }
            });

            outputString = `📊 Result: ${passCount}/${results.length} Passed\n\n` + outputString;

            if (results.length > 0 && passCount === results.length) {
                outputString += "\n🎉 ALL TESTS PASSED! Click 'Submit Answer' or 'Finish Phase' when ready.\n";
                setConsoleOutput(outputString);

                // Mark current question as passed
                setPassedQuestions((prev) => {
                    const newSet = new Set(prev);
                    newSet.add(questions[currentIndex].id || currentIndex);
                    return newSet;
                });
            } else {
                setConsoleOutput(outputString);
            }

        } catch (err) {
            setConsoleOutput("❌ Runtime Error:\n" + (err.message || err));
        }
    };

    const onFinishPhase = async () => {
        if (!window.confirm("Are you sure you want to finish the coding phase?")) return;

        setConsoleOutput("🏁 Submitting final code results...");

        try {
            const userData = JSON.parse(localStorage.getItem("user"));
            const token = userData?.access;

            // Gather stats for all questions
            const codeStatsArray = questions.map((q, idx) => {
                const qId = q.id || idx;
                const passed = passedQuestions.has(qId);
                return {
                    difficulty: q.difficulty || "medium",
                    passed: passed,
                    ai_usage: 0 // Could aggregate per question if tracked, ignoring for now
                };
            });

            const successRes = await axios.post(
                "http://127.0.0.1:8000/api/main-agent/report_success/",
                {
                    source: "code",
                    code_stats: codeStatsArray // Assuming scoring engine can sum these
                },
                { headers: { Authorization: `Bearer ${token}` } }
            );

            setConsoleOutput((prev) => prev + "\n🤖 AGENT SAYS:\n" + successRes.data.reply + "\n");

            if (successRes.data.action) {
                const action = successRes.data.action;
                setConsoleOutput((prev) => prev + `\n🚀 Auto-navigating...`);
                setTimeout(() => {
                    if (action.view === 'code') navigate(`/agent-code?topic=${encodeURIComponent(action.data?.topic)}`);
                    else if (action.view === 'debugger') navigate(`/agent-debugger?topic=${encodeURIComponent(action.data?.topic)}`);
                    else if (action.view === 'quiz') navigate(`/agent-quiz?topic=${encodeURIComponent(action.data?.topic)}`);
                    else if (action.view === 'dashboard') navigate('/');
                    else navigate('/agent-tutor', { state: { initialMessage: successRes.data.reply } });
                }, 2000);
            } else {
                setConsoleOutput((prev) => prev + `\n🚀 Auto-navigating to Tutor...`);
                setTimeout(() => {
                    navigate('/agent-tutor', { state: { initialMessage: successRes.data.reply } });
                }, 2000);
            }
        } catch (apiErr) {
            console.error(apiErr);
            setConsoleOutput((prev) => prev + "\n⚠️ Failed to submit results.");
        }
    };

    const sendToAssistant = async (userPrompt, extraData = {}) => {
        const message = { role: "user", text: userPrompt || "Review current step", ts: Date.now() };
        if (userPrompt) setAssistantMessages((prev) => [...prev, message]);
        setLoading(true);

        const userData = JSON.parse(localStorage.getItem("user"));
        const token = userData?.access;

        const history = assistantMessages.map(msg => ({
            role: msg.role,
            content: msg.text
        }));

        try {
            const resp = await fetch("http://localhost:8000/api/code/ai-assist/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ 
                    prompt: userPrompt, 
                    code, 
                    model, 
                    history,
                    ...extraData 
                }),
            });
            const data = await resp.json();
            
            if (extraData.mode === "review") {
                const botMsg = {
                    role: "assistant",
                    text: data.passed 
                        ? `✅ **Step ${currentStepIndex + 1} Verified!**\n\n${data.feedback}\n\n**Next Mission:** ${data.next_instruction}`
                        : `❌ **Review Feedback:**\n\n${data.feedback}`,
                    ts: Date.now(),
                    isReview: true
                };
                setAssistantMessages((prev) => [...prev, botMsg]);
                if (data.passed) {
                    setCurrentStepIndex((prev) => prev + 1);
                }
            } else {
                const botMsg = {
                    role: "assistant",
                    text: data.reply || "No reply from AI.",
                    ts: Date.now(),
                };
                setAssistantMessages((prev) => [...prev, botMsg]);
            }
        } catch (e) {
            setAssistantMessages((prev) => [
                ...prev,
                { role: "assistant", text: `⚠️ Error: ${e.message} `, ts: Date.now() },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const onReviewStep = () => {
        const q = questions[currentIndex];
        if (!q.steps || currentStepIndex >= q.steps.length) return;
        
        const currentStep = q.steps[currentStepIndex];
        sendToAssistant(null, {
            mode: "review",
            current_step: currentStep
        });
    };

    const onSend = () => {
        const trimmed = query.trim();
        if (!trimmed) return;
        sendToAssistant(trimmed);
        setQuery("");
    };

    useEffect(() => {
        assistantEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [assistantMessages]);

    useEffect(() => {
        if (questions.length > 0) {
            const q = questions[currentIndex];
            setTestCases(q.testcases || []);
            setCurrentStepIndex(0);
            
            // Set initial instructions if in guided mode
            if (q.steps && q.steps.length > 0) {
                setAssistantMessages([
                    {
                        role: "assistant",
                        text: `🚀 **Mission Started!**\n\nI will guide you through this challenge step-by-step.\n\n**Step 1:** ${q.steps[0].instruction}`,
                        ts: Date.now()
                    }
                ]);
            } else {
                setAssistantMessages([]);
            }
        }
    }, [currentIndex, questions]);

    const currentQuestion = questions[currentIndex] || {};

    // =============== RESIZING STATE & LOGIC ===============
    const [leftWidth, setLeftWidth] = useState(28);    // Problem
    const [centerWidth, setCenterWidth] = useState(44); // Code + Console
    const [rightWidth, setRightWidth] = useState(28);  // Assistant + Tests
    const minPanelWidth = 15;

    const [consoleHeight, setConsoleHeight] = useState(30); // % of center panel
    const minConsoleHeight = 15;
    const maxConsoleHeight = 70;

    const [assistantHeight, setAssistantHeight] = useState(70); // % of right panel
    const minAssistantHeight = 30;
    const maxAssistantHeight = 85;

    const startHorizontalResize = (panel, e) => {
        e.preventDefault();
        const startX = e.clientX;
        const startLeft = leftWidth;
        const startCenter = centerWidth;
        const startRight = rightWidth;

        const doResize = (moveEvent) => {
            const container = document.querySelector('.main-layout');
            const containerWidth = container?.offsetWidth || window.innerWidth;
            const dxPercent = ((moveEvent.clientX - startX) / containerWidth) * 100;

            if (panel === 'left') {
                let newLeft = Math.min(100 - minPanelWidth * 2, Math.max(minPanelWidth, startLeft + dxPercent));
                let remaining = 100 - newLeft;
                let newRight = Math.min(remaining - minPanelWidth, startRight);
                let newCenter = remaining - newRight;
                setLeftWidth(newLeft);
                setCenterWidth(newCenter);
                setRightWidth(newRight);
            } else if (panel === 'right') {
                let newRight = Math.min(100 - minPanelWidth * 2, Math.max(minPanelWidth, startRight + dxPercent));
                let remaining = 100 - newRight;
                let newLeft = Math.min(remaining - minPanelWidth, startLeft);
                let newCenter = remaining - newLeft;
                setRightWidth(newRight);
                setLeftWidth(newLeft);
                setCenterWidth(newCenter);
            }
        };

        const stopResize = () => {
            window.removeEventListener('mousemove', doResize);
            window.removeEventListener('mouseup', stopResize);
        };

        window.addEventListener('mousemove', doResize);
        window.addEventListener('mouseup', stopResize);
    };

    const startConsoleResize = (e) => {
        e.preventDefault();
        const startY = e.clientY;
        const startHeight = consoleHeight;

        const doResize = (moveEvent) => {
            const container = document.querySelector('.center-panel');
            const containerHeight = container?.offsetHeight || window.innerHeight;
            const dyPercent = ((startY - moveEvent.clientY) / containerHeight) * 100;
            const newHeight = Math.min(maxConsoleHeight, Math.max(minConsoleHeight, startHeight + dyPercent));
            setConsoleHeight(newHeight);
        };

        const stopResize = () => {
            window.removeEventListener('mousemove', doResize);
            window.removeEventListener('mouseup', stopResize);
        };

        window.addEventListener('mousemove', doResize);
        window.addEventListener('mouseup', stopResize);
    };

    const startAssistantResize = (e) => {
        e.preventDefault();
        const startY = e.clientY;
        const startHeight = assistantHeight;

        const doResize = (moveEvent) => {
            const container = document.querySelector('.right-panel');
            const containerHeight = container?.offsetHeight || window.innerHeight;
            const dyPercent = ((startY - moveEvent.clientY) / containerHeight) * 100;
            const newHeight = Math.min(maxAssistantHeight, Math.max(minAssistantHeight, startHeight + dyPercent));
            setAssistantHeight(newHeight);
        };

        const stopResize = () => {
            window.removeEventListener('mousemove', doResize);
            window.removeEventListener('mouseup', stopResize);
        };

        window.addEventListener('mousemove', doResize);
        window.addEventListener('mouseup', stopResize);
    };

    // =============== RENDER CONDITIONAL ===============
    if (!topic) {
        return (
            <div className="w-screen h-screen flex flex-col items-center justify-center bg-gray-950 text-white">
                <div className="bg-gray-900 p-8 rounded-2xl shadow-2xl border border-red-900 text-center max-w-md">
                    <h2 className="text-3xl font-bold text-red-500 mb-4">⚠️ No Mission Assigned</h2>
                    <p className="text-gray-400 mb-6">The Agent has not provided a topic for this Coding Session.</p>
                    <button onClick={() => navigate('/agent-tutor')} className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold transition">
                        Return to Tutor
                    </button>
                    <p className="mt-4 text-xs text-gray-500">Wait for the Agent to assign a task.</p>
                </div>
            </div>
        );
    }

    if (loading && questions.length === 0) {
        return (
            <div className="w-screen h-screen flex flex-col items-center justify-center bg-gray-950 text-white">
                <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-indigo-500 mb-6"></div>
                <h2 className="text-2xl font-bold animate-pulse">Generating Challenge...</h2>
                <p className="text-indigo-400 mt-2 font-mono">Topic: {topic}</p>
            </div>
        );
    }

    // =============== MAIN UI — FULL WIDTH + RESIZABLE ===============
    return (
        <div className="w-screen h-screen flex flex-col bg-gray-950 text-gray-200 overflow-hidden">
            {/* Header */}
            <header className="p-4 bg-gray-900 border-b border-gray-800 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-white">🤖 AUTOMATIC AGENT CODE</h1>
                    {topic && <span className="text-xs text-indigo-400 font-mono bg-indigo-900/30 px-2 py-1 rounded">Target: {topic}</span>}
                </div>

                {planDescription && (
                    <p className="text-indigo-400 mt-2 text-sm md:text-base">
                        {planDescription}
                    </p>
                )}
            </header>

            {/* Question Navigation */}
            {responseMode === "plan" && questions.length > 1 && (
                <div className="flex flex-wrap justify-center gap-2 p-3 bg-gray-900 border-b border-gray-800">
                    {questions.map((q, i) => (
                        <button
                            key={i}
                            onClick={() => setCurrentIndex(i)}
                            className={`px - 4 py - 2 rounded - lg text - sm font - medium transition ${i === currentIndex
                                ? "bg-indigo-600 text-white"
                                : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                                } `}
                        >
                            {q.title || `Q${i + 1} `}
                        </button>
                    ))}
                </div>
            )}

            {/* Main Layout — Full Width & Resizable */}
            <div className="main-layout flex flex-row flex-1 overflow-hidden p-3 gap-2">
                {/* LEFT: Problem */}
                <div
                    className="flex flex-col bg-gray-900 rounded-xl border border-gray-800 overflow-hidden"
                    style={{ width: `${leftWidth}% ` }}
                >
                    <div className="p-4 bg-gradient-to-r from-indigo-800/30 to-purple-800/30 border-b border-gray-800">
                        <h2 className="text-lg font-bold text-indigo-400">📜 Problem</h2>
                    </div>
                    <div className="flex-1 p-4 overflow-auto">
                        {questions.length === 0 ? (
                            <p className="text-gray-500 italic">Waiting for Agent Assignment...</p>
                        ) : (
                            <>
                                <div className="flex justify-between items-start mb-3">
                                    <h3 className="text-xl font-semibold text-white">{currentQuestion.title}</h3>
                                    {passedQuestions.has(currentQuestion.id || currentIndex) && (
                                        <span className="px-2 py-1 bg-green-900/50 text-green-400 text-xs font-bold rounded border border-green-700">
                                            ✅ PASSED
                                        </span>
                                    )}
                                </div>
                                <div className="text-gray-300 whitespace-pre-wrap text-sm leading-relaxed">
                                    {currentQuestion.description?.trim() || (
                                        <span className="text-gray-500 italic">No description provided.</span>
                                    )}
                                </div>
                                <div className="mt-4 pt-3 border-t border-gray-800">
                                    <span className="inline-block px-3 py-1 bg-gray-800 rounded-full text-xs text-gray-400">
                                        {currentQuestion.difficulty || "N/A"} Difficulty
                                    </span>
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* LEFT RESIZE HANDLE */}
                <div
                    onMouseDown={(e) => startHorizontalResize('left', e)}
                    className="w-1.5 cursor-col-resize bg-indigo-900/30 hover:bg-indigo-600 self-stretch flex items-center justify-center"
                    title="Drag to resize"
                >
                    <div className="w-0.5 h-6 bg-indigo-400 rounded-full opacity-70"></div>
                </div>

                {/* CENTER: Code + Console */}
                <div
                    className="center-panel flex flex-col bg-gray-900 rounded-xl border border-gray-800 overflow-hidden"
                    style={{ width: `${centerWidth}% ` }}
                >
                    <div
                        className="flex-1 flex flex-col overflow-hidden"
                        style={{ height: `${100 - consoleHeight}% ` }}
                    >
                        <div className="flex justify-between items-center p-3 bg-gray-850 border-b border-gray-800">
                            <h3 className="font-medium text-indigo-300">🐍 Python Editor</h3>
                            <div className="flex gap-2 items-center">
                                <button
                                    onClick={fetchVisualization}
                                    className="bg-purple-600 hover:bg-purple-700 px-3 py-1.5 rounded-lg text-sm font-medium text-white transition-colors flex items-center gap-1"
                                >
                                    🎨 Visualize
                                </button>
                                <button
                                    onClick={onRun}
                                    className="bg-green-600 hover:bg-green-700 px-4 py-1.5 rounded-lg text-sm font-medium"
                                >
                                    ▶ Run
                                </button>
                                <div className="w-px h-6 bg-gray-700 mx-1"></div>
                                <button
                                    onClick={onFinishPhase}
                                    className="bg-blue-600 hover:bg-blue-700 px-4 py-1.5 rounded-lg text-sm font-bold text-white shadow-[0_0_10px_rgba(37,99,235,0.4)]"
                                >
                                    Finish Phase
                                </button>
                            </div>
                        </div>
                        <div className="flex-1 overflow-hidden">
                            <CodeEditor code={code} setCode={setCode} />
                        </div>
                    </div>

                    {/* Console Resize Handle */}
                    <div
                        onMouseDown={startConsoleResize}
                        className="h-1.5 cursor-row-resize bg-indigo-900/30 hover:bg-indigo-600 flex items-center justify-center"
                        title="Drag to resize console"
                    >
                        <div className="h-0.5 w-6 bg-indigo-400 rounded-full opacity-70"></div>
                    </div>

                    <div
                        className="h-full bg-gray-900"
                        style={{ height: `${consoleHeight}% ` }}
                    >
                        <div className="flex justify-between items-center p-3 bg-gray-850 border-b border-gray-800">
                            <h3 className="font-medium text-amber-400">🧾 Console</h3>
                            <button
                                onClick={() => setConsoleOutput("")}
                                className="text-xs text-gray-500 hover:text-red-400"
                            >
                                Clear
                            </button>
                        </div>
                        <pre className="p-3 text-xs font-mono text-gray-300 bg-black/20 overflow-auto h-full">
                            {consoleOutput}
                        </pre>
                    </div>
                </div>

                {/* RIGHT RESIZE HANDLE */}
                <div
                    onMouseDown={(e) => startHorizontalResize('right', e)}
                    className="w-1.5 cursor-col-resize bg-indigo-900/30 hover:bg-indigo-600 self-stretch flex items-center justify-center"
                    title="Drag to resize"
                >
                    <div className="w-0.5 h-6 bg-indigo-400 rounded-full opacity-70"></div>
                </div>

                {/* RIGHT: Assistant + Tests */}
                <div
                    className="right-panel flex flex-col bg-gray-900 rounded-xl border border-gray-800 overflow-hidden"
                    style={{ width: `${rightWidth}% ` }}
                >
                    {/* Assistant */}
                    <div
                        className="flex flex-col overflow-hidden"
                        style={{ height: `${assistantHeight}% ` }}
                    >
                        <div className="p-3 bg-teal-800 text-white font-medium">🤖AI Assistant</div>
                        <div className="flex-1 overflow-auto p-3 space-y-3">
                            {/* Mission Progress */}
                            {currentQuestion.steps && currentQuestion.steps.length > 0 && (
                                <div className="mb-4 p-3 bg-gray-800/50 rounded-lg border border-indigo-500/30">
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="text-xs font-bold text-indigo-400 uppercase tracking-widest">Current Mission</span>
                                        <span className="text-xs text-gray-400">{currentStepIndex + 1} / {currentQuestion.steps.length}</span>
                                    </div>
                                    <div className="w-full bg-gray-700 h-1.5 rounded-full overflow-hidden">
                                        <div 
                                            className="bg-indigo-500 h-full transition-all duration-500" 
                                            style={{ width: `${((currentStepIndex) / currentQuestion.steps.length) * 100}%` }}
                                        ></div>
                                    </div>
                                    <p className="mt-2 text-xs text-gray-300 italic">
                                        {currentStepIndex < currentQuestion.steps.length 
                                          ? `Target: ${currentQuestion.steps[currentStepIndex].title}`
                                          : "✨ Mission Complete!"}
                                    </p>
                                </div>
                            )}

                            {assistantMessages.length === 0 ? (
                                <p className="text-gray-500 text-sm italic">Ask for help with your code!</p>
                            ) : (
                                assistantMessages.map((msg, i) => (
                                    <div
                                        key={i}
                                        className={`p-3 rounded-lg max-w-[95%] ${msg.role === "user"
                                            ? "bg-indigo-900/50 ml-auto border border-indigo-700"
                                            : "bg-teal-900/20 mr-auto border border-teal-800"
                                            } `}
                                    >
                                        <div className="text-xs text-gray-400 mb-1 flex justify-between">
                                            <span>{msg.role === "user" ? "You" : "AI Coach"}</span>
                                            <span className="opacity-50 text-[10px]">
                                                {new Date(msg.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        </div>
                                        <div className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
                                            {/* HANDLE HIDDEN HINTS (REVEAL) */}
                                            {msg.text.split(/(\[REVEAL\].*?\[\/REVEAL\])/g).map((part, idx) => {
                                                const match = part.match(/\[REVEAL\](.*?)\[\/REVEAL\]/);
                                                if (match) {
                                                    return <HiddenHint key={idx} code={match[1]} />;
                                                }
                                                return part;
                                            })}
                                        </div>
                                    </div>
                                ))
                            )}
                            <div ref={assistantEndRef} className="h-0" />
                        </div>
                        <div className="p-3 border-t border-gray-800 bg-gray-900/50">
                            {currentQuestion.steps && currentStepIndex < currentQuestion.steps.length && (
                                <button
                                    onClick={onReviewStep}
                                    disabled={loading}
                                    className="mb-2 w-full bg-indigo-600 hover:bg-indigo-700 py-2.5 rounded-lg text-white text-sm font-bold shadow-lg transition-transform active:scale-95 disabled:opacity-50"
                                >
                                    {loading ? "Analyzing Code..." : `Check Progress: Step ${currentStepIndex + 1}`}
                                </button>
                            )}
                            <div className="flex gap-2">
                                <textarea
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    placeholder="Ask for a hint..."
                                    className="flex-1 p-2 bg-gray-850 border border-gray-700 rounded-lg text-sm resize-none text-white focus:border-teal-500 focus:outline-none"
                                    rows="1"
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            e.preventDefault();
                                            onSend();
                                        }
                                    }}
                                />
                                <button
                                    onClick={onSend}
                                    disabled={!query.trim() || loading}
                                    className="px-4 bg-teal-600 hover:bg-teal-700 rounded-lg text-white text-sm font-medium disabled:opacity-60"
                                >
                                    Send
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Assistant Resize Handle */}
                    <div
                        onMouseDown={startAssistantResize}
                        className="h-1.5 cursor-row-resize bg-indigo-900/30 hover:bg-indigo-600 flex items-center justify-center"
                        title="Drag to resize panels"
                    >
                        <div className="h-0.5 w-6 bg-indigo-400 rounded-full opacity-70"></div>
                    </div>

                    {/* Test Cases */}
                    <div className="bg-gray-900 max-h-full overflow-hidden">
                        <div className="p-3 bg-amber-900/20 border-b border-amber-800/30">
                            <h3 className="font-medium text-amber-400">🧪 Test Cases</h3>
                        </div>
                        <div className="p-3 overflow-auto max-h-36">
                            {testCases.length === 0 ? (
                                <p className="text-gray-500 text-sm italic">No test cases available.</p>
                            ) : (
                                <div className="space-y-2.5">
                                    {testCases.map((tc, i) => (
                                        <div key={i} className="text-xs">
                                            <div className="text-amber-400 font-medium">Input: {tc.input_data}</div>
                                            <div className="text-green-400 mt-1">→ {tc.expected_output}</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
            {/* VISUALIZATION MODAL */}
            {isVisModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
                    <div className="bg-gray-900 w-full max-w-5xl h-[85vh] rounded-2xl border border-purple-500/50 shadow-2xl flex flex-col overflow-hidden relative">
                        <div className="p-4 bg-gray-800 border-b border-gray-700 flex justify-between items-center">
                            <h3 className="text-xl font-bold text-purple-400">🎨 Algorithm Visualization</h3>
                            <button
                                onClick={() => setIsVisModalOpen(false)}
                                className="text-gray-400 hover:text-white"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="flex-1 bg-white relative">
                            {visLoading ? (
                                <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
                                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
                                </div>
                            ) : (
                                <VisualizerRenderer htmlContent={visualizationHtml} />
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
