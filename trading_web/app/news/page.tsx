'use client';

import { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import './news.css';

interface News {
    id: number;
    date: string;
    time: string;
    source: string;
    title: string;
    content: string;
    url?: string;
    ai_analysis?: string;
    sentiment?: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
    impact_score?: number;
    tags: string[];
}

export default function NewsPage() {
    const [newsList, setNewsList] = useState<News[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);

    // Filters
    const [keyword, setKeyword] = useState('');
    const [sentimentFilter, setSentimentFilter] = useState('');
    const [sourceFilter, setSourceFilter] = useState('');

    // Form State
    const [formData, setFormData] = useState({
        date: new Date().toISOString().slice(0, 10),
        time: new Date().toTimeString().slice(0, 5),
        source: '',
        title: '',
        content: '',
        url: '',
        tags: ''
    });

    useEffect(() => {
        fetchNews();
    }, []);

    const fetchNews = async () => {
        try {
            setLoading(true);
            let url = 'http://localhost:8000/news/search?limit=100';

            if (keyword) url += `&keyword=${encodeURIComponent(keyword)}`;
            if (sentimentFilter) url += `&sentiment=${sentimentFilter}`;
            if (sourceFilter) url += `&source=${encodeURIComponent(sourceFilter)}`;

            const response = await fetch(url);
            const data = await response.json();
            setNewsList(data);
        } catch (error) {
            console.error('Error fetching news:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const payload = {
                ...formData,
                tags: formData.tags.split(',').map(t => t.trim()).filter(t => t)
            };

            const response = await fetch('http://localhost:8000/news', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                setShowModal(false);
                setFormData({
                    date: new Date().toISOString().slice(0, 10),
                    time: new Date().toTimeString().slice(0, 5),
                    source: '',
                    title: '',
                    content: '',
                    url: '',
                    tags: ''
                });
                fetchNews(); // Refresh list
            }
        } catch (error) {
            console.error('Error creating news:', error);
        }
    };

    const analyzeNews = async (id: number) => {
        try {
            setLoading(true);
            const response = await fetch(`http://localhost:8000/news/${id}/analyze`, {
                method: 'POST'
            });

            if (response.ok) {
                fetchNews(); // Refresh list to show results
            }
        } catch (error) {
            console.error('Error analyzing news:', error);
            setLoading(false);
        }
    };

    const getSentimentColor = (sentiment?: string) => {
        switch (sentiment) {
            case 'POSITIVE': return 'positive';
            case 'NEGATIVE': return 'negative';
            default: return 'neutral';
        }
    };

    return (
        <div className="min-h-screen bg-[#0b0e11]">
            <Navbar />

            <div className="news-container">
                <header className="news-header">
                    <h1>📰 Market News & Analysis</h1>
                    <button className="add-news-btn" onClick={() => setShowModal(true)}>
                        <span>+</span> Add News
                    </button>
                </header>

                {/* Filters */}
                <div className="filters-section">
                    <div className="filter-group">
                        <label>Keyword</label>
                        <input
                            type="text"
                            className="filter-input"
                            placeholder="Search title or content..."
                            value={keyword}
                            onChange={(e) => setKeyword(e.target.value)}
                        />
                    </div>
                    <div className="filter-group">
                        <label>Sentiment</label>
                        <select
                            className="filter-select"
                            value={sentimentFilter}
                            onChange={(e) => setSentimentFilter(e.target.value)}
                        >
                            <option value="">All Sentiments</option>
                            <option value="POSITIVE">Positive</option>
                            <option value="NEGATIVE">Negative</option>
                            <option value="NEUTRAL">Neutral</option>
                        </select>
                    </div>
                    <div className="filter-group">
                        <label>Source</label>
                        <input
                            type="text"
                            className="filter-input"
                            placeholder="e.g. Reuters"
                            value={sourceFilter}
                            onChange={(e) => setSourceFilter(e.target.value)}
                        />
                    </div>
                    <button className="search-btn" onClick={fetchNews}>
                        Search
                    </button>
                </div>

                {/* News Grid */}
                {loading ? (
                    <div style={{ textAlign: 'center', color: '#848e9c', padding: '40px' }}>Loading news...</div>
                ) : (
                    <div className="news-grid">
                        {newsList.map(news => (
                            <div key={news.id} className="news-card">
                                <div className="news-meta">
                                    <span className="news-date">{news.date} {news.time}</span>
                                    {news.source && <span className="news-source">{news.source}</span>}
                                </div>
                                <h3 className="news-title">{news.title}</h3>
                                <p className="news-content-preview">{news.content}</p>

                                {news.tags && news.tags.length > 0 && (
                                    <div className="news-tags">
                                        {news.tags.map((tag, i) => (
                                            <span key={i} className="tag">#{tag}</span>
                                        ))}
                                    </div>
                                )}

                                {news.sentiment ? (
                                    <div className={`ai-badge ${getSentimentColor(news.sentiment)}`}>
                                        <span>{news.sentiment}</span>
                                        {news.impact_score && (
                                            <span className="impact-score">Impact: {news.impact_score}/10</span>
                                        )}
                                    </div>
                                ) : (
                                    <button
                                        className="analyze-btn"
                                        onClick={() => analyzeNews(news.id)}
                                    >
                                        ⚡ Analyze with AI
                                    </button>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Add News Modal */}
            {showModal && (
                <div className="modal-overlay" onClick={(e) => {
                    if (e.target === e.currentTarget) setShowModal(false);
                }}>
                    <div className="modal-content">
                        <div className="modal-header">
                            <h2>Add New News</h2>
                            <button className="close-btn" onClick={() => setShowModal(false)}>×</button>
                        </div>
                        <form onSubmit={handleSubmit}>
                            <div className="modal-body">
                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Date</label>
                                        <input
                                            type="date"
                                            className="form-input"
                                            required
                                            value={formData.date}
                                            onChange={e => setFormData({ ...formData, date: e.target.value })}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Time</label>
                                        <input
                                            type="time"
                                            className="form-input"
                                            value={formData.time}
                                            onChange={e => setFormData({ ...formData, time: e.target.value })}
                                        />
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label>Source</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        placeholder="e.g. Bloomberg, Reuters"
                                        value={formData.source}
                                        onChange={e => setFormData({ ...formData, source: e.target.value })}
                                    />
                                </div>

                                <div className="form-group">
                                    <label>Title</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        required
                                        placeholder="News Headline"
                                        value={formData.title}
                                        onChange={e => setFormData({ ...formData, title: e.target.value })}
                                    />
                                </div>

                                <div className="form-group">
                                    <label>Content</label>
                                    <textarea
                                        className="form-textarea"
                                        required
                                        placeholder="Paste full news content here..."
                                        value={formData.content}
                                        onChange={e => setFormData({ ...formData, content: e.target.value })}
                                    ></textarea>
                                </div>

                                <div className="form-group">
                                    <label>Tags (comma separated)</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        placeholder="gold, fed, inflation"
                                        value={formData.tags}
                                        onChange={e => setFormData({ ...formData, tags: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn-cancel" onClick={() => setShowModal(false)}>Cancel</button>
                                <button type="submit" className="btn-submit">Save News</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
