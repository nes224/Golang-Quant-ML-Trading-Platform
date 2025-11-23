'use client';

import { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import './journal.css';

interface JournalEntry {
    date: string;
    trade1: number;
    trade2: number;
    trade3: number;
    deposit: number;
    withdraw: number;
    note: string;
    profit: number;
    total: number;
    capital: number;
    winrate: number;
}

export default function JournalPage() {
    const [entries, setEntries] = useState<JournalEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingEntry, setEditingEntry] = useState<JournalEntry | null>(null);

    // Form State
    const [formData, setFormData] = useState({
        date: new Date().toISOString().split('T')[0],
        trade1: '',
        trade2: '',
        trade3: '',
        deposit: '',
        withdraw: '',
        capital: '',
        note: ''
    });

    const fetchEntries = async () => {
        try {
            const response = await fetch('http://localhost:8000/journal');
            const data = await response.json();
            setEntries(data);
            setLoading(false);
        } catch (error) {
            console.error('Error fetching journal:', error);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEntries();
    }, []);

    const handleOpenModal = (entry?: JournalEntry) => {
        if (entry) {
            setEditingEntry(entry);
            setFormData({
                date: entry.date,
                trade1: entry.trade1.toString(),
                trade2: entry.trade2.toString(),
                trade3: entry.trade3.toString(),
                deposit: entry.deposit.toString(),
                withdraw: entry.withdraw.toString(),
                capital: entry.capital.toString(),
                note: entry.note || ''
            });
        } else {
            setEditingEntry(null);
            setFormData({
                date: new Date().toISOString().split('T')[0],
                trade1: '',
                trade2: '',
                trade3: '',
                deposit: '',
                withdraw: '',
                capital: '',
                note: ''
            });
        }
        setIsModalOpen(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        const payload = {
            date: formData.date,
            trade1: parseFloat(formData.trade1) || 0,
            trade2: parseFloat(formData.trade2) || 0,
            trade3: parseFloat(formData.trade3) || 0,
            deposit: parseFloat(formData.deposit) || 0,
            withdraw: parseFloat(formData.withdraw) || 0,
            capital: parseFloat(formData.capital) || 0,
            note: formData.note
        };

        try {
            const response = await fetch('http://localhost:8000/journal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (response.ok) {
                setIsModalOpen(false);
                fetchEntries();
            }
        } catch (error) {
            console.error('Error saving entry:', error);
        }
    };

    const handleDelete = async (date: string) => {
        if (confirm('Are you sure you want to delete this entry?')) {
            try {
                await fetch(`http://localhost:8000/journal/${date}`, {
                    method: 'DELETE',
                });
                fetchEntries();
            } catch (error) {
                console.error('Error deleting entry:', error);
            }
        }
    };

    const formatCurrency = (val: number) => {
        return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    const getProfitClass = (val: number) => {
        if (val > 0) return 'positive';
        if (val < 0) return 'negative';
        return 'neutral';
    };

    return (
        <div className="min-h-screen bg-[#0b0e11]">
            <Navbar />

            <div className="journal-container">
                <header className="journal-header">
                    <h1>📝 Trading Journal</h1>
                    <button className="add-btn" onClick={() => handleOpenModal()}>
                        + New Entry
                    </button>
                </header>

                <div className="journal-table-container">
                    <table className="journal-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Capital</th>
                                <th>Trade 1</th>
                                <th>Trade 2</th>
                                <th>Trade 3</th>
                                <th>Profit</th>
                                <th>Deposit</th>
                                <th>Withdraw</th>
                                <th>Total</th>
                                <th>Winrate</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr>
                                    <td colSpan={11} style={{ textAlign: 'center', padding: '40px' }}>
                                        Loading...
                                    </td>
                                </tr>
                            ) : entries.length === 0 ? (
                                <tr>
                                    <td colSpan={11} style={{ textAlign: 'center', padding: '40px' }}>
                                        No entries found. Start by adding a new one!
                                    </td>
                                </tr>
                            ) : (
                                entries.map((entry) => (
                                    <tr key={entry.date}>
                                        <td onClick={() => handleOpenModal(entry)} style={{ cursor: 'pointer' }}>
                                            {entry.date}
                                        </td>
                                        <td>{formatCurrency(entry.capital)}</td>
                                        <td className={getProfitClass(entry.trade1)}>{formatCurrency(entry.trade1)}</td>
                                        <td className={getProfitClass(entry.trade2)}>{formatCurrency(entry.trade2)}</td>
                                        <td className={getProfitClass(entry.trade3)}>{formatCurrency(entry.trade3)}</td>
                                        <td className={getProfitClass(entry.profit)} style={{ fontWeight: 'bold' }}>
                                            {formatCurrency(entry.profit)}
                                        </td>
                                        <td className="positive">{entry.deposit > 0 ? `+${formatCurrency(entry.deposit)}` : '-'}</td>
                                        <td className="negative">{entry.withdraw > 0 ? `-${formatCurrency(entry.withdraw)}` : '-'}</td>
                                        <td style={{ fontWeight: 'bold', color: '#fff' }}>{formatCurrency(entry.total)}</td>
                                        <td>{entry.winrate}%</td>
                                        <td>
                                            <button
                                                className="delete-btn"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleDelete(entry.date);
                                                }}
                                            >
                                                🗑️
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {isModalOpen && (
                <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>{editingEntry ? 'Edit Entry' : 'New Entry'}</h2>
                            <button className="close-btn" onClick={() => setIsModalOpen(false)}>×</button>
                        </div>

                        <form onSubmit={handleSubmit}>
                            <div className="form-group">
                                <label>Date</label>
                                <input
                                    type="date"
                                    className="form-control"
                                    value={formData.date}
                                    onChange={e => setFormData({ ...formData, date: e.target.value })}
                                    required
                                    disabled={!!editingEntry} // Disable date editing for now to simplify logic
                                />
                            </div>

                            <div className="form-group">
                                <label>Starting Capital</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    className="form-control"
                                    value={formData.capital}
                                    onChange={e => setFormData({ ...formData, capital: e.target.value })}
                                    placeholder="0.00"
                                />
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                                <div className="form-group">
                                    <label>Trade 1</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        className="form-control"
                                        value={formData.trade1}
                                        onChange={e => setFormData({ ...formData, trade1: e.target.value })}
                                        placeholder="0.00"
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Trade 2</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        className="form-control"
                                        value={formData.trade2}
                                        onChange={e => setFormData({ ...formData, trade2: e.target.value })}
                                        placeholder="0.00"
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Trade 3</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        className="form-control"
                                        value={formData.trade3}
                                        onChange={e => setFormData({ ...formData, trade3: e.target.value })}
                                        placeholder="0.00"
                                    />
                                </div>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                <div className="form-group">
                                    <label>Deposit</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        className="form-control"
                                        value={formData.deposit}
                                        onChange={e => setFormData({ ...formData, deposit: e.target.value })}
                                        placeholder="0.00"
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Withdraw</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        className="form-control"
                                        value={formData.withdraw}
                                        onChange={e => setFormData({ ...formData, withdraw: e.target.value })}
                                        placeholder="0.00"
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Note</label>
                                <textarea
                                    className="form-control"
                                    value={formData.note}
                                    onChange={e => setFormData({ ...formData, note: e.target.value })}
                                    rows={3}
                                    placeholder="Trading notes..."
                                />
                            </div>

                            <div className="form-actions">
                                <button type="button" className="cancel-btn" onClick={() => setIsModalOpen(false)}>
                                    Cancel
                                </button>
                                <button type="submit" className="submit-btn">
                                    Save Entry
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
