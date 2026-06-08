/**
 * Decode/Track Page - Image Tracking Interface
 */
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { decodeImage } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

const Decode = () => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const onDrop = useCallback(acceptedFiles => {
    const selectedFile = acceptedFiles[0];
    if (selectedFile) {
      setFile(selectedFile);
      
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreview(e.target.result);
      };
      reader.readAsDataURL(selectedFile);
      
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.bmp', '.gif'] }
  });

  const handleDecode = async () => {
    if (!file) {
      setError('Please select an image');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await decodeImage(file);
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to decode image');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="container" style={{ padding: '2rem 0' }}>
      <h1 style={{ marginBottom: '2rem' }}>Track Image Ownership</h1>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
        {/* Upload Section */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Upload Image to Track</h3>
          </div>

          <div
            {...getRootProps()}
            style={{
              border: '2px dashed ' + (isDragActive ? '#6366f1' : '#dee2e6'),
              borderRadius: '0.75rem',
              padding: '2rem',
              textAlign: 'center',
              cursor: 'pointer',
              backgroundColor: isDragActive ? '#f0f4ff' : 'white',
              transition: 'all 0.3s ease',
              marginBottom: '1rem',
            }}
          >
            <input {...getInputProps()} />
            {preview ? (
              <>
                <img 
                  src={preview} 
                  alt="Preview" 
                  style={{ 
                    maxWidth: '100%', 
                    maxHeight: '300px', 
                    borderRadius: '0.5rem',
                    marginBottom: '1rem'
                  }} 
                />
                <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>
                  Click or drag to change image
                </p>
              </>
            ) : (
              <>
                <p style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>🔍</p>
                <p style={{ marginBottom: '0.5rem' }}>Drag image here or click to select</p>
                <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>
                  Upload any image to check for embedded tracking information
                </p>
              </>
            )}
          </div>

          {error && (
            <div className="alert alert-danger">{error}</div>
          )}

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button 
              onClick={handleDecode}
              className="btn btn-primary"
              disabled={loading || !file}
              style={{ flex: 1 }}
            >
              {loading ? 'Analyzing...' : 'Extract Tracking Info'}
            </button>
            {file && (
              <button 
                onClick={handleReset}
                className="btn btn-outline"
                style={{ flex: 1 }}
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Results Section */}
        {result && (
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">🎯 Tracking Results</h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ borderBottom: '1px solid #dee2e6', paddingBottom: '1rem' }}>
                <p style={{ color: '#6c757d', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                  Tracking ID
                </p>
                <p style={{ fontSize: '1rem', fontFamily: 'monospace', fontWeight: 'bold', wordBreak: 'break-all' }}>
                  {result.tracking_id}
                </p>
              </div>

              {result.owner_name && (
                <div>
                  <p style={{ color: '#6c757d', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                    Owner Name
                  </p>
                  <p style={{ fontSize: '1rem', fontWeight: '500' }}>
                    {result.owner_name}
                  </p>
                </div>
              )}

              {result.owner_email && (
                <div>
                  <p style={{ color: '#6c757d', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                    Email
                  </p>
                  <p style={{ fontSize: '1rem', fontWeight: '500' }}>
                    <a href={`mailto:${result.owner_email}`} style={{ color: '#6366f1' }}>
                      {result.owner_email}
                    </a>
                  </p>
                </div>
              )}

              {result.location && (
                <div>
                  <p style={{ color: '#6c757d', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                    Location
                  </p>
                  <p style={{ fontSize: '1rem', fontWeight: '500' }}>
                    {result.location}
                  </p>
                </div>
              )}

              <div>
                <p style={{ color: '#6c757d', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                  Confidence
                </p>
                <div style={{ 
                  backgroundColor: '#e0e7ff', 
                  borderRadius: '0.25rem', 
                  overflow: 'hidden',
                  height: '24px'
                }}>
                  <div 
                    style={{
                      backgroundColor: '#6366f1',
                      height: '100%',
                      width: `${result.confidence}%`,
                      transition: 'width 0.3s ease',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'white',
                      fontSize: '0.75rem',
                      fontWeight: 'bold'
                    }}
                  >
                    {result.confidence > 10 && `${result.confidence.toFixed(1)}%`}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <LoadingSpinner loading={loading} message="Extracting tracking information..." />

      {!result && !loading && (
        <div className="card" style={{ marginTop: '2rem' }}>
          <div className="card-header">
            <h3 className="card-title">How It Works</h3>
          </div>
          <ol style={{ lineHeight: '1.8', color: '#6c757d' }}>
            <li>Upload an image that may contain embedded tracking information</li>
            <li>Our decoder analyzes the image pixels using advanced neural networks</li>
            <li>If a tracking ID is found, we display the associated ownership information</li>
            <li>The confidence score indicates how certain we are about the extraction</li>
          </ol>
        </div>
      )}
    </div>
  );
};

export default Decode;
