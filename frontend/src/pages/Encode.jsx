/**
 * Encode Page - Image Encoding Interface
 */
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { encodeImage } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

const Encode = () => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [result, setResult] = useState(null);
  
  // Form fields
  const [ownerName, setOwnerName] = useState('');
  const [ownerEmail, setOwnerEmail] = useState('');
  const [location, setLocation] = useState('');
  const [description, setDescription] = useState('');

  const onDrop = useCallback(acceptedFiles => {
    const selectedFile = acceptedFiles[0];
    if (selectedFile) {
      setFile(selectedFile);
      
      // Create preview
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

  const handleEncode = async (e) => {
    e.preventDefault();
    
    if (!file || !ownerName || !ownerEmail) {
      setError('Please fill all required fields and select an image');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await encodeImage(file, ownerName, ownerEmail, location, description);
      setResult(response.data);
      setSuccess(true);
      
      // Reset form
      setTimeout(() => {
        setFile(null);
        setPreview(null);
        setOwnerName('');
        setOwnerEmail('');
        setLocation('');
        setDescription('');
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to encode image');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ padding: '2rem 0' }}>
      <h1 style={{ marginBottom: '2rem' }}>Encode Image with Tracking ID</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Upload Section */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Upload Image</h3>
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
                <p style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>📸</p>
                <p style={{ marginBottom: '0.5rem' }}>Drag image here or click to select</p>
                <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>
                  Supported: JPG, PNG, BMP, GIF (max 50MB)
                </p>
              </>
            )}
          </div>
        </div>

        {/* Form Section */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Metadata</h3>
          </div>

          <form onSubmit={handleEncode}>
            <div className="form-group">
              <label className="form-label">Owner Name *</label>
              <input
                type="text"
                className="form-input"
                value={ownerName}
                onChange={(e) => setOwnerName(e.target.value)}
                placeholder="Your name"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Email Address *</label>
              <input
                type="email"
                className="form-input"
                value={ownerEmail}
                onChange={(e) => setOwnerEmail(e.target.value)}
                placeholder="your@email.com"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Location</label>
              <input
                type="text"
                className="form-input"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g., New York, USA"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea
                className="form-textarea"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Additional information about the image"
                rows="3"
              />
            </div>

            {error && (
              <div className="alert alert-danger">{error}</div>
            )}

            {success && result && (
              <div className="alert alert-success">
                ✓ Image encoded successfully!
                <br />
                <strong>Tracking ID:</strong> {result.tracking_id}
              </div>
            )}

            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={loading || !file}
              style={{ width: '100%' }}
            >
              {loading ? 'Encoding...' : 'Encode Image'}
            </button>
          </form>
        </div>
      </div>

      {/* Results Section */}
      {result && success && (
        <div className="card" style={{ marginTop: '2rem' }}>
          <div className="card-header">
            <h3 className="card-title">Encoding Results</h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div>
              <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>Tracking ID</p>
              <p style={{ fontSize: '1.125rem', fontWeight: 'bold' }}>{result.tracking_id}</p>
            </div>
            <div>
              <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>PSNR</p>
              <p style={{ fontSize: '1.125rem', fontWeight: 'bold' }}>{result.psnr} dB</p>
            </div>
            <div>
              <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>SSIM</p>
              <p style={{ fontSize: '1.125rem', fontWeight: 'bold' }}>{result.ssim}</p>
            </div>
            <div>
              <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>Status</p>
              <p style={{ fontSize: '1.125rem', fontWeight: 'bold', color: '#10b981' }}>✓ Success</p>
            </div>
          </div>

          <div style={{ marginTop: '1rem' }}>
            <a href={result.encoded_image_url} className="btn btn-primary">
              Download Encoded Image
            </a>
          </div>
        </div>
      )}

      <LoadingSpinner loading={loading} message="Encoding your image..." />
    </div>
  );
};

export default Encode;
