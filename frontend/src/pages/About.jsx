/**
 * About Page
 */
import React from 'react';

const About = () => {
  return (
    <div className="container" style={{ padding: '2rem 0', maxWidth: '800px' }}>
      <h1 style={{ marginBottom: '2rem' }}>About PixelGuard</h1>

      <div className="card">
        <h2>What is PixelGuard?</h2>
        <p>
          PixelGuard is an advanced image watermarking system that uses deep learning to embed 
          invisible tracking IDs into images. Unlike traditional watermarks, PixelGuard watermarks 
          are completely imperceptible to the human eye while remaining robust against common 
          image transformations like JPEG compression, resizing, and cropping.
        </p>
      </div>

      <div className="card">
        <h2>Key Technologies</h2>
        <ul style={{ lineHeight: '1.8' }}>
          <li><strong>Deep Learning:</strong> Fully Convolutional Networks (FCN) for adaptive image encoding</li>
          <li><strong>Robustness:</strong> Global Average Pooling for crop-resistant decoding</li>
          <li><strong>Adversarial Training:</strong> GAN-based approach for imperceptibility</li>
          <li><strong>Noise Resilience:</strong> JPEG approximation and geometric transformations</li>
          <li><strong>Quality Metrics:</strong> PSNR > 40dB, SSIM > 0.98 for imperceptibility</li>
        </ul>
      </div>

      <div className="card">
        <h2>How It Works</h2>
        <ol style={{ lineHeight: '1.8' }}>
          <li><strong>Encoding:</strong> Our neural network embeds a 32-64 bit tracking ID into image pixels</li>
          <li><strong>Imperceptibility:</strong> The encoding is mathematically optimized to be invisible</li>
          <li><strong>Metadata Storage:</strong> Owner information is securely stored in our database</li>
          <li><strong>Decoding:</strong> Another neural network extracts the tracking ID from (possibly distorted) images</li>
          <li><strong>Verification:</strong> The tracking ID is used to retrieve and verify ownership</li>
        </ol>
      </div>

      <div className="card">
        <h2>Use Cases</h2>
        <ul style={{ lineHeight: '1.8' }}>
          <li>Copyright protection for photographers and content creators</li>
          <li>Proving ownership of images shared on social media</li>
          <li>Supply chain authentication for product images</li>
          <li>Digital asset management and verification</li>
          <li>Intellectual property protection</li>
        </ul>
      </div>

      <div className="card">
        <h2>Privacy & Security</h2>
        <p>
          PixelGuard respects your privacy:
        </p>
        <ul style={{ lineHeight: '1.8' }}>
          <li>Images are processed and deleted after encoding/decoding</li>
          <li>Tracking information is encrypted and securely stored</li>
          <li>No personal data is shared with third parties</li>
          <li>All communications are encrypted (HTTPS)</li>
        </ul>
      </div>

      <div className="card">
        <h2>Technical Specifications</h2>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <tbody>
            <tr style={{ borderBottom: '1px solid #dee2e6' }}>
              <td style={{ padding: '0.5rem 0', fontWeight: 'bold' }}>Message Length</td>
              <td style={{ padding: '0.5rem 0' }}>32-64 bits</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #dee2e6' }}>
              <td style={{ padding: '0.5rem 0', fontWeight: 'bold' }}>Image Size</td>
              <td style={{ padding: '0.5rem 0' }}>256×256 pixels (any size supported)</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #dee2e6' }}>
              <td style={{ padding: '0.5rem 0', fontWeight: 'bold' }}>Accuracy</td>
              <td style={{ padding: '0.5rem 0' }}>95-99% bit recovery rate</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #dee2e6' }}>
              <td style={{ padding: '0.5rem 0', fontWeight: 'bold' }}>Processing Time</td>
              <td style={{ padding: '0.5rem 0' }}>~800ms per image</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #dee2e6' }}>
              <td style={{ padding: '0.5rem 0', fontWeight: 'bold' }}>PSNR Metric</td>
              <td style={{ padding: '0.5rem 0' }}>{'>'} 40 dB (imperceptible)</td>
            </tr>
            <tr>
              <td style={{ padding: '0.5rem 0', fontWeight: 'bold' }}>SSIM Metric</td>
              <td style={{ padding: '0.5rem 0' }}>{'>'} 0.98 (highly similar)</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Contact & Support</h2>
        <p>
          Have questions or need assistance? Contact us at:
        </p>
        <p>
          Email: <a href="mailto:support@pixelguard.com" style={{ color: '#6366f1' }}>support@pixelguard.com</a>
        </p>
        <p>
          GitHub: <a href="https://github.com/pixelguard" style={{ color: '#6366f1' }} target="_blank" rel="noopener noreferrer">github.com/pixelguard</a>
        </p>
      </div>
    </div>
  );
};

export default About;
