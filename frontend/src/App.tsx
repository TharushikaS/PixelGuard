import { useState, useRef } from 'react';
import { Upload, Download, Lock, Unlock, Shield, Image as ImageIcon, Loader2 } from 'lucide-react';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState<'encode' | 'decode'>('encode');

  // Encode state
  const [encodeFile, setEncodeFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [imageName, setImageName] = useState('');
  const [ownerInfo, setOwnerInfo] = useState('');
  const [isEncoding, setIsEncoding] = useState(false);
  const [encodedBlobUrl, setEncodedBlobUrl] = useState<string | null>(null);
  const [encodeError, setEncodeError] = useState('');

  // Decode state
  const [decodeFile, setDecodeFile] = useState<File | null>(null);
  const [isDecoding, setIsDecoding] = useState(false);
  const [decodedPayload, setDecodedPayload] = useState<any>(null);
  const [decodeError, setDecodeError] = useState('');

  const encodeFileInputRef = useRef<HTMLInputElement>(null);
  const decodeFileInputRef = useRef<HTMLInputElement>(null);

  const handleEncodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!encodeFile) {
      setEncodeError("Please upload an image to encode.");
      return;
    }
    if (!name || !imageName || !ownerInfo) {
      setEncodeError("Please fill out all fields.");
      return;
    }

    setIsEncoding(true);
    setEncodeError('');
    setEncodedBlobUrl(null);

    const formData = new FormData();
    formData.append('image', encodeFile);
    formData.append('name', name);
    formData.append('image_name', imageName);
    formData.append('owner_info', ownerInfo);

    try {
      const response = await fetch('/encode', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to encode image");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setEncodedBlobUrl(url);
    } catch (err: any) {
      setEncodeError(err.message || "An unexpected error occurred");
    } finally {
      setIsEncoding(false);
    }
  };

  const handleDecodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!decodeFile) {
      setDecodeError("Please upload an image to decode.");
      return;
    }

    setIsDecoding(true);
    setDecodeError('');
    setDecodedPayload(null);

    const formData = new FormData();
    formData.append('image', decodeFile);

    try {
      const response = await fetch('/decode', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Failed to decode image");
      }

      if (!data.success) {
        throw new Error(data.error || "Failed to decode valid payload");
      }

      setDecodedPayload(data.payload);
    } catch (err: any) {
      setDecodeError(err.message || "An unexpected error occurred");
    } finally {
      setIsDecoding(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-indigo-500/30">
      {/* Background ambient effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-4 py-12 flex flex-col items-center">
        
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center p-3 bg-indigo-500/10 rounded-2xl mb-6 ring-1 ring-indigo-500/20 shadow-[0_0_40px_-10px_rgba(99,102,241,0.3)]">
            <Shield className="w-10 h-10 text-indigo-400" />
          </div>
          <h1 className="text-5xl md:text-6xl font-bold mb-4 tracking-tight bg-gradient-to-br from-white to-neutral-400 bg-clip-text text-transparent">
            PixelGuard
          </h1>
          <p className="text-neutral-400 text-lg max-w-2xl mx-auto">
            Securely embed identity data directly into your images using deep neural networks. 100% invisible. 100% recoverable.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex p-1 bg-neutral-900/50 backdrop-blur-md rounded-2xl ring-1 ring-white/5 mb-8 w-full max-w-md mx-auto">
          <button
            onClick={() => setActiveTab('encode')}
            className={`flex-1 py-3 px-6 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 ${
              activeTab === 'encode' 
                ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/25' 
                : 'text-neutral-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <Lock className="w-4 h-4" />
            Encode Data
          </button>
          <button
            onClick={() => setActiveTab('decode')}
            className={`flex-1 py-3 px-6 rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2 ${
              activeTab === 'decode' 
                ? 'bg-purple-500 text-white shadow-lg shadow-purple-500/25' 
                : 'text-neutral-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <Unlock className="w-4 h-4" />
            Decode Image
          </button>
        </div>

        {/* Main Content Area */}
        <div className="w-full max-w-3xl bg-neutral-900/40 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl">
          
          {/* ENCODE SECTION */}
          {activeTab === 'encode' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
                <Lock className="w-6 h-6 text-indigo-400" />
                Protect Your Image
              </h2>
              
              <form onSubmit={handleEncodeSubmit} className="space-y-6">
                
                {/* File Uploader */}
                <div 
                  className="group relative border-2 border-dashed border-white/10 rounded-2xl p-8 transition-colors hover:border-indigo-500/50 hover:bg-indigo-500/5 cursor-pointer text-center"
                  onClick={() => encodeFileInputRef.current?.click()}
                >
                  <input 
                    type="file" 
                    ref={encodeFileInputRef}
                    className="hidden" 
                    accept="image/*"
                    onChange={(e) => setEncodeFile(e.target.files?.[0] || null)}
                  />
                  {encodeFile ? (
                    <div className="flex flex-col items-center gap-3">
                      <img src={URL.createObjectURL(encodeFile)} alt="Preview" className="w-32 h-32 object-cover rounded-xl shadow-lg border border-white/10" />
                      <p className="text-sm text-indigo-300 font-medium">{encodeFile.name}</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-3">
                      <div className="p-4 bg-white/5 rounded-full group-hover:scale-110 transition-transform">
                        <Upload className="w-8 h-8 text-neutral-400 group-hover:text-indigo-400" />
                      </div>
                      <p className="text-neutral-300 font-medium">Click to select an image</p>
                      <p className="text-sm text-neutral-500">PNG, JPG, JPEG up to 10MB</p>
                    </div>
                  )}
                </div>

                {/* Form Fields */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-neutral-300">Your Name</label>
                    <input 
                      type="text" 
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
                      placeholder="John Doe"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-neutral-300">Image Name</label>
                    <input 
                      type="text" 
                      value={imageName}
                      onChange={(e) => setImageName(e.target.value)}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
                      placeholder="Sunset over mountains"
                    />
                  </div>
                  <div className="space-y-2 md:col-span-2">
                    <label className="text-sm font-medium text-neutral-300">Owner Identity Information</label>
                    <textarea 
                      value={ownerInfo}
                      onChange={(e) => setOwnerInfo(e.target.value)}
                      rows={3}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all resize-none"
                      placeholder="Email, Wallet Address, or Registration ID..."
                    />
                  </div>
                </div>

                {encodeError && (
                  <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                    {encodeError}
                  </div>
                )}

                <button 
                  type="submit" 
                  disabled={isEncoding || !encodeFile}
                  className="w-full py-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-neutral-800 disabled:text-neutral-500 text-white rounded-xl font-semibold transition-all duration-300 flex items-center justify-center gap-2 hover:shadow-[0_0_30px_-5px_rgba(99,102,241,0.5)] disabled:hover:shadow-none"
                >
                  {isEncoding ? (
                    <><Loader2 className="w-5 h-5 animate-spin" /> Encoding Securely...</>
                  ) : (
                    <><Lock className="w-5 h-5" /> Embed Data & Generate Image</>
                  )}
                </button>
              </form>

              {/* Success State */}
              {encodedBlobUrl && (
                <div className="mt-8 p-6 bg-green-500/10 border border-green-500/20 rounded-2xl flex flex-col sm:flex-row items-center gap-6 animate-in zoom-in-95 duration-500">
                  <div className="w-24 h-24 shrink-0 rounded-xl overflow-hidden border-2 border-green-500/30">
                    <img src={encodedBlobUrl} alt="Encoded" className="w-full h-full object-cover" />
                  </div>
                  <div className="flex-1 text-center sm:text-left">
                    <h3 className="text-lg font-semibold text-green-400 mb-1">Encoding Successful!</h3>
                    <p className="text-neutral-400 text-sm mb-4">Your identity data has been permanently embedded into the image.</p>
                    <a 
                      href={encodedBlobUrl} 
                      download={`secured_${encodeFile?.name || 'image.png'}`}
                      className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-500/20 hover:bg-green-500/30 text-green-300 rounded-lg font-medium transition-colors border border-green-500/30"
                    >
                      <Download className="w-4 h-4" />
                      Download Secured Image
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* DECODE SECTION */}
          {activeTab === 'decode' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
                <Unlock className="w-6 h-6 text-purple-400" />
                Reveal Hidden Data
              </h2>
              
              <form onSubmit={handleDecodeSubmit} className="space-y-6">
                
                {/* File Uploader */}
                <div 
                  className="group relative border-2 border-dashed border-white/10 rounded-2xl p-8 transition-colors hover:border-purple-500/50 hover:bg-purple-500/5 cursor-pointer text-center"
                  onClick={() => decodeFileInputRef.current?.click()}
                >
                  <input 
                    type="file" 
                    ref={decodeFileInputRef}
                    className="hidden" 
                    accept="image/*"
                    onChange={(e) => setDecodeFile(e.target.files?.[0] || null)}
                  />
                  {decodeFile ? (
                    <div className="flex flex-col items-center gap-3">
                      <img src={URL.createObjectURL(decodeFile)} alt="Preview" className="w-32 h-32 object-cover rounded-xl shadow-lg border border-white/10" />
                      <p className="text-sm text-purple-300 font-medium">{decodeFile.name}</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-3">
                      <div className="p-4 bg-white/5 rounded-full group-hover:scale-110 transition-transform">
                        <ImageIcon className="w-8 h-8 text-neutral-400 group-hover:text-purple-400" />
                      </div>
                      <p className="text-neutral-300 font-medium">Select a secured image to decode</p>
                      <p className="text-sm text-neutral-500">PNG, JPG, JPEG</p>
                    </div>
                  )}
                </div>

                {decodeError && (
                  <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                    {decodeError}
                  </div>
                )}

                <button 
                  type="submit" 
                  disabled={isDecoding || !decodeFile}
                  className="w-full py-4 bg-purple-600 hover:bg-purple-500 disabled:bg-neutral-800 disabled:text-neutral-500 text-white rounded-xl font-semibold transition-all duration-300 flex items-center justify-center gap-2 hover:shadow-[0_0_30px_-5px_rgba(168,85,247,0.5)] disabled:hover:shadow-none"
                >
                  {isDecoding ? (
                    <><Loader2 className="w-5 h-5 animate-spin" /> Extracting Data...</>
                  ) : (
                    <><Unlock className="w-5 h-5" /> Decode Image</>
                  )}
                </button>
              </form>

              {/* Decoded Payload Results */}
              {decodedPayload && (
                <div className="mt-8 p-6 bg-white/5 border border-white/10 rounded-2xl animate-in zoom-in-95 duration-500">
                  <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Shield className="w-5 h-5 text-purple-400" />
                    Verified Identity Record
                  </h3>
                  
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 border-b border-white/10 pb-3">
                      <span className="text-neutral-500 text-sm">ID</span>
                      <span className="col-span-2 text-white font-mono text-sm">{decodedPayload.unique_id}</span>
                    </div>
                    <div className="grid grid-cols-3 border-b border-white/10 pb-3">
                      <span className="text-neutral-500 text-sm">Owner Name</span>
                      <span className="col-span-2 text-white font-medium">{decodedPayload.name}</span>
                    </div>
                    <div className="grid grid-cols-3 border-b border-white/10 pb-3">
                      <span className="text-neutral-500 text-sm">Image Name</span>
                      <span className="col-span-2 text-white">{decodedPayload.image_name}</span>
                    </div>
                    <div className="grid grid-cols-3">
                      <span className="text-neutral-500 text-sm">Identity Info</span>
                      <span className="col-span-2 text-white text-sm bg-black/40 p-3 rounded-lg">{decodedPayload.owner_info}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

export default App;
