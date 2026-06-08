/**
 * Home Page - Landing/Marketing Page
 */
import React from 'react';
import { Link } from 'react-router-dom';

const Home = () => {
  const features = [
    {
      icon: '🔒',
      title: 'Invisible Watermark',
      description: 'Embed tracking IDs imperceptibly into images using deep learning'
    },
    {
      icon: '📱',
      title: 'Social Media Resilient',
      description: 'Survive JPEG compression, resizing, cropping, and other transformations'
    },
    {
      icon: '🔍',
      title: 'Easy Tracking',
      description: 'Upload any image to retrieve ownership information'
    },
    {
      icon: '⚡',
      title: 'Fast Processing',
      description: 'Encode/decode in seconds with GPU acceleration'
    },
  ];

  return (
    <div className="container">
      {/* Hero Section */}
      <section style={{ textAlign: 'center', padding: '3rem 0' }}>
        <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem', fontWeight: 'bold' }}>
          Invisible Image Watermarking
        </h1>
        <p style={{ fontSize: '1.125rem', color: '#6c757d', marginBottom: '2rem' }}>
          Protect your images with imperceptible tracking IDs that survive social media transformations
        </p>
        
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <Link to="/encode" className="btn btn-primary">
            Try It Now →
          </Link>
          <Link to="/about" className="btn btn-outline">
            Learn More
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section style={{ margin: '3rem 0' }}>
        <h2 style={{ textAlign: 'center', fontSize: '2rem', marginBottom: '2rem' }}>Features</h2>
        
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '2rem',
        }}>
          {features.map((feature, idx) => (
            <div key={idx} className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>
                {feature.icon}
              </div>
              <h3 style={{ marginBottom: '0.5rem' }}>{feature.title}</h3>
              <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section style={{
        backgroundColor: '#6366f1',
        color: 'white',
        padding: '3rem',
        borderRadius: '0.75rem',
        textAlign: 'center',
        margin: '3rem 0',
      }}>
        <h2 style={{ marginBottom: '1rem' }}>Ready to Protect Your Images?</h2>
        <p style={{ marginBottom: '1.5rem', fontSize: '1.125rem' }}>
          Start embedding invisible tracking IDs into your images today
        </p>
        <Link to="/encode" className="btn" style={{ backgroundColor: 'white', color: '#6366f1' }}>
          Get Started
        </Link>
      </section>

      {/* How It Works */}
      <section style={{ margin: '3rem 0', padding: '2rem', backgroundColor: '#f8f9fa', borderRadius: '0.75rem' }}>
        <h2 style={{ textAlign: 'center', marginBottom: '2rem' }}>How It Works</h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '2rem' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>1️⃣</div>
            <h4>Upload Image</h4>
            <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>Select an image to protect</p>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>2️⃣</div>
            <h4>Add Metadata</h4>
            <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>Enter owner information and location</p>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>3️⃣</div>
            <h4>Embed Watermark</h4>
            <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>System generates tracking ID and embeds it</p>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>4️⃣</div>
            <h4>Track Ownership</h4>
            <p style={{ color: '#6c757d', fontSize: '0.875rem' }}>Upload any image to verify ownership</p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
