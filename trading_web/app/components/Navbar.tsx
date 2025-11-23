'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import './navbar.css';

export default function Navbar() {
    const pathname = usePathname();

    return (
        <nav className="navbar">
            <div className="navbar-brand">
                <span className="brand-icon">📈</span>
                <span className="brand-text">NesHedgeFund</span>
            </div>
            <div className="navbar-links">
                <Link href="/" className={`nav-link ${pathname === '/' ? 'active' : ''}`}>
                    Dashboard
                </Link>
                <Link href="/journal" className={`nav-link ${pathname === '/journal' ? 'active' : ''}`}>
                    Journal
                </Link>
                <Link href="/checklist" className={`nav-link ${pathname === '/checklist' ? 'active' : ''}`}>
                    Checklist
                </Link>
            </div>
        </nav>
    );
}
