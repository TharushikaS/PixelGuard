/**
 * Navigation Component
 */
import React, { useState } from 'react';

const Navigation = ({ currentPage }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const pages = [
    { id: 'home', label: 'Home', path: '/' },
    { id: 'encode', label: 'Encode', path: '/encode' },
    { id: 'decode', label: 'Decode', path: '/decode' },
    { id: 'track', label: 'Track', path: '/track' },
    { id: 'dashboard', label: 'Dashboard', path: '/dashboard' },
    { id: 'about', label: 'About', path: '/about' },
  ];

  return (
    <nav style={{ marginBottom: '1rem' }}>
      <div className="flex-between">
        <h2>PixelGuard Steganography</h2>
        <button 
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          style={{ display: 'none' }}
        >
          Menu
        </button>
      </div>
      
      <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        {pages.map(page => (
          <a 
            key={page.id}
            href={page.path}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '0.375rem',
              backgroundColor: currentPage === page.id ? '#6366f1' : '#f8f9fa',
              color: currentPage === page.id ? 'white' : '#333',
              textDecoration: 'none',
              fontWeight: currentPage === page.id ? 'bold' : 'normal',
              transition: 'all 0.3s ease',
            }}
          >
            {page.label}
          </a>
        ))}
      </div>
    </nav>
  );
};

export default Navigation;
