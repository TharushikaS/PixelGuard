/**
 * Loading Spinner Component
 */
import React from 'react';
import { ClipLoader } from 'react-spinners';

const LoadingSpinner = ({ loading, size = 50, message = 'Loading...' }) => {
  if (!loading) return null;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '2rem',
      gap: '1rem',
    }}>
      <ClipLoader color="#6366f1" size={size} />
      <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>{message}</p>
    </div>
  );
};

export default LoadingSpinner;
