/**
 * Footer Component
 */
import React from 'react';

const Footer = () => {
  return (
    <footer style={{ 
      marginTop: '3rem', 
      padding: '2rem', 
      borderTop: '1px solid #dee2e6',
      textAlign: 'center',
      backgroundColor: '#f8f9fa'
    }}>
      <p>&copy; 2024 PixelGuard. All rights reserved.</p>
      <p style={{ fontSize: '0.875rem', color: '#6c757d', marginTop: '0.5rem' }}>
        Invisible image watermarking for copyright protection
      </p>
    </footer>
  );
};

export default Footer;
