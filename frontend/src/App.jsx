/**
 * Main App Component
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import Header from './components/Header';
import Footer from './components/Footer';

import Home from './pages/Home';
import Encode from './pages/Encode';
import Decode from './pages/Decode';
import About from './pages/About';

import './styles/globals.css';
import './styles/variables.css';
import './styles/components.css';

function App() {
  return (
    <Router>
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Header />
        
        <main style={{ flex: 1 }}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/encode" element={<Encode />} />
            <Route path="/track" element={<Decode />} />
            <Route path="/decode" element={<Decode />} />
            <Route path="/about" element={<About />} />
            <Route path="*" element={
              <div style={{ textAlign: 'center', padding: '3rem' }}>
                <h1>404 - Page Not Found</h1>
              </div>
            } />
          </Routes>
        </main>
        
        <Footer />
      </div>
    </Router>
  );
}

export default App;
