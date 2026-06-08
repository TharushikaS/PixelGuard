/**
 * Header Component
 */
import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/components.css';

const Header = () => {
  return (
    <header className="header">
      <div className="header-content">
        <Link to="/" className="logo">
          🔒 PixelGuard
        </Link>
        
        <nav>
          <ul className="nav-links">
            <li><Link to="/" className="nav-link">Home</Link></li>
            <li><Link to="/encode" className="nav-link">Encode</Link></li>
            <li><Link to="/track" className="nav-link">Track</Link></li>
            <li><Link to="/about" className="nav-link">About</Link></li>
            <li><Link to="/pricing" className="nav-link">Pricing</Link></li>
          </ul>
        </nav>
      </div>
    </header>
  );
};

export default Header;
