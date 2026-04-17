import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import authService from '../../services/authService';
import axios from 'axios';
import './LeftPanel.css';

const LeftPanel = () => {
    const user = authService.getCurrentUser();
    const [mistakes, setMistakes] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchMistakes = async () => {
            try {
                const userData = JSON.parse(localStorage.getItem("user"));
                const token = userData?.access;
                if (!token) return;

                const res = await axios.get("http://localhost:8000/api/code/mistakes/", {
                    headers: { Authorization: `Bearer ${token}` }
                });
                setMistakes(res.data);
            } catch (err) {
                console.error("Error fetching mistakes:", err);
            } finally {
                setLoading(false);
            }
        };

        fetchMistakes();
    }, [user]);

    return (
        <div className="left-panel">
            <div className="user-profile">
                <div className="avatar">
                    {user?.username?.[0]?.toUpperCase() || 'C'}
                </div>
                <h3>{user ? user.username || 'Cobra Coder' : 'Guest'}</h3>
                <p className="user-rank">🐍 Python Novice</p>
            </div>

            <nav className="main-nav">
                <ul>
                    <li className="nav-item active"><Link to="/dashboard">Dashboard Home</Link></li>
                    <li className="nav-item"><Link to="/map">Knowledge Map</Link></li>
                    <li className="nav-item"><Link to="/Playground">Playground</Link></li>
                </ul>
            </nav>

            <div className="mistake-log-container">
                <div className="section-header">
                    <h4>⚠️ Learning Gaps</h4>
                    <span className="badge">{mistakes.length}</span>
                </div>
                
                <div className="mistake-list">
                    {loading ? (
                        <p className="loading-text">Analyzing gaps...</p>
                    ) : mistakes.length === 0 ? (
                        <p className="empty-text">No gaps detected yet. Keep coding!</p>
                    ) : (
                        mistakes.map((m, i) => (
                            <div key={i} className="mistake-item">
                                <div className="mistake-meta">
                                    <span className={`source-tag ${m.source}`}>{m.source}</span>
                                    <span className="timestamp">{m.created_at}</span>
                                </div>
                                <p className="mistake-topic">{m.topic}</p>
                                <p className="mistake-desc">{m.mistake}</p>
                            </div>
                        ))
                    )}
                </div>
            </div>

            <div className="auth-footer">
                {user ? (
                   <button onClick={() => { authService.logout(); window.location.reload(); }} className="logout-btn">Logout</button>
                ) : (
                    <div className="auth-links">
                        <Link to='/Login'>Login</Link>
                        <span className="divider">|</span>
                        <Link to='/Register'>Register</Link>
                    </div>
                )}
            </div>
        </div>
    );
};

export default LeftPanel;