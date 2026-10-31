import React, { useState, useRef } from 'react';
import { useOutletContext } from 'react-router-dom';
import { UploadCloud, FileVideo, X } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function Upload() {
  const [file, setFile] = useState(null);
  const fileInputRef = useRef(null);
  const { lang, dir, t } = useLanguage();
  
  // Consume the global background upload function from Layout context
  const { uploadVideoFile } = useOutletContext();

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleStartUpload = () => {
    if (!file) return;
    uploadVideoFile(file);
    setFile(null);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto h-full flex flex-col" dir={dir}>
      <header className={`mb-10 ${dir === 'rtl' ? 'text-right' : 'text-left'}`}>
        <h2 className="text-3xl font-bold text-[#D7E0EE] tracking-tight font-sans">{t('uploadTitle')}</h2>
        <p className="text-[#96A8C0] mt-2 font-medium">{t('uploadSub')}</p>
      </header>

      <div 
        className={`flex-1 border-2 border-dashed rounded-3xl flex flex-col items-center justify-center p-12 transition-all duration-300 ${file ? 'border-indigo-500/50 bg-indigo-500/5' : 'border-[#26344A] bg-[#0F172A] hover:bg-[#151F33] hover:border-[#707FF0] shadow-sm'}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {!file ? (
          <>
            <div className="w-24 h-24 bg-[#151F33] text-[#707FF0] rounded-full flex items-center justify-center mb-6 shadow-sm border border-[#26344A]">
              <UploadCloud size={40} className="text-[#96A8C0]" />
            </div>
            <h3 className="text-xl font-bold text-[#D7E0EE] mb-2 tracking-wide">
              {lang === "ar" ? "اسحب وأسقط ملف الفيديو هنا" : "Drag and drop your video here"}
            </h3>
            <p className="text-[#96A8C0] mb-8 font-medium">MP4, AVI, MKV (Up to 500MB)</p>
            
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              className="hidden" 
              accept="video/*"
            />
            <button 
              onClick={() => fileInputRef.current.click()}
              className="px-6 py-3 bg-[#707FF0] hover:bg-[#3935A8] text-white rounded-xl font-bold tracking-wide transition-colors shadow-sm shadow-slate-500/10"
            >
              {lang === "ar" ? "تصفح الملفات" : "Browse Files"}
            </button>
          </>
        ) : (
          <div className="w-full max-w-md bg-[#0F172A] border border-[#26344A] rounded-2xl p-6 shadow-lg relative text-[#D7E0EE]">
            <button 
              onClick={() => setFile(null)}
              className="absolute -top-3 -right-3 bg-[#151F33] border border-[#26344A] p-1.5 rounded-full text-[#96A8C0] hover:text-[#D7E0EE] transition-colors"
            >
              <X size={16} />
            </button>
            
            <div className="flex items-center gap-4 mb-6">
              <div className="p-4 bg-indigo-500/10 rounded-xl text-[#45C5F5]">
                <FileVideo size={32} />
              </div>
              <div className="flex-1 min-w-0 text-left">
                <h4 className="font-bold text-[#F8FAFC] truncate">{file.name}</h4>
                <p className="text-sm text-[#96A8C0] font-mono">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
              </div>
            </div>

            <button 
              onClick={handleStartUpload}
              className="w-full py-3 bg-[#707FF0] hover:bg-[#3935A8] text-white rounded-xl font-bold tracking-wide transition-colors flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20"
            >
              {t('uploadBtn')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
