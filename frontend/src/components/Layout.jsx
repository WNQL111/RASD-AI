import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, Upload, History, Settings, Shield, Activity, 
  Folder, BarChart3, Globe, ShieldCheck, Film
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import RasdLogo from './RasdLogo';
import api from '../services/api';

export default function Layout() {
  const navigate = useNavigate();
  const [backgroundUploads, setBackgroundUploads] = useState([]);
  const [videoProgressMap, setVideoProgressMap] = useState({});
  const { lang, toggleLang, dir, t } = useLanguage();

  // Connect native EventSource SSE for global progress telemetry & completion updates
  React.useEffect(() => {
    const baseURL = api.defaults.baseURL || 'http://localhost:8001/api';
    const sseUrl = `${baseURL.replace(/\/$/, '')}/alerts/stream`;
    
    let eventSource = null;
    try {
      eventSource = new EventSource(sseUrl);

      const handleTelemetry = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'progress_update' && data.video_id) {
            setVideoProgressMap(prev => ({
              ...prev,
              [data.video_id]: data
            }));
          } else if ((data.type === 'analysis_complete' || data.type === 'status_update') && data.video_id) {
            setVideoProgressMap(prev => ({
              ...prev,
              [data.video_id]: {
                ...data,
                progress_percentage: 100.0,
                current_stage: "COMPLETED",
                status: "completed"
              }
            }));
          }
        } catch (err) {
          console.error("Layout: Error parsing SSE progress telemetry:", err);
        }
      };

      eventSource.addEventListener('progress_update', handleTelemetry);
      eventSource.addEventListener('analysis_complete', handleTelemetry);
      eventSource.addEventListener('status_update', handleTelemetry);
      eventSource.addEventListener('message', handleTelemetry);

    } catch (err) {
      console.error("Layout: Failed to initialize SSE EventSource:", err);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  const uploadVideoFile = async (file) => {
    const uploadId = Math.random().toString(36).substring(7);
    const newUpload = {
      id: uploadId,
      name: file.name,
      progress: 0,
      status: "uploading"
    };

    setBackgroundUploads(prev => [...prev, newUpload]);
    navigate('/');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/upload-video', formData, {
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setBackgroundUploads(prev => prev.map(u => 
            u.id === uploadId ? { ...u, progress: percent } : u
          ));
        }
      });

      const videoId = res.data.id;
      setBackgroundUploads(prev => prev.map(u => 
        u.id === uploadId ? { ...u, status: "processing", video_id: videoId, progress: 100 } : u
      ));

    } catch (err) {
      console.error("Background upload failed:", err);
      setBackgroundUploads(prev => prev.map(u => 
        u.id === uploadId ? { ...u, status: "error" } : u
      ));
    }
  };

  return (
    <div className="flex h-screen bg-[#020618] text-[#D7E0EE] font-sans overflow-hidden" dir={dir}>
      {/* Executive Dark-Mode Sidebar - Unified RASD AI Operations Palette */}
      <aside className={`w-64 bg-[#0A1023] flex flex-col z-20 transition-all ${
        dir === 'rtl' ? 'border-l border-[#26344A]' : 'border-r border-[#26344A]'
      }`}>
        
        {/* Brand & Language Switcher Header */}
        <div className="p-4 border-b border-[#26344A] bg-[#0F172A]/70 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <RasdLogo size={32} />
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-base font-extrabold tracking-tight text-[#F8FAFC]">RASD</span>
                <span className="text-[11px] bg-[#707FF0] text-white font-bold px-1.5 py-0.5 rounded shadow-xs">AI</span>
                <span className="text-[11px] font-bold text-[#96A8C0] mr-1">رَصْد</span>
              </div>
              <p className="text-[10px] text-[#96A8C0] font-medium tracking-tight">Security & Forensics</p>
            </div>
          </div>

          <button 
            onClick={toggleLang}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-[#151F33] hover:bg-[#1D293D] border border-[#26344A] rounded-lg text-xs font-semibold text-[#D7E0EE] transition-all shadow-2xs cursor-pointer active:scale-95"
            title="Switch Language / تغيير اللغة"
          >
            <Globe size={13} className="text-[#707FF0]" />
            <span>{lang === "ar" ? "EN" : "عربي"}</span>
          </button>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 p-3 space-y-1.5 mt-2 overflow-y-auto">
          <NavLink 
            to="/" 
            className={({isActive}) => `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              isActive 
                ? 'bg-[#707FF0] text-white font-bold shadow-md shadow-[#707FF0]/25 border border-[#707FF0]' 
                : 'text-[#96A8C0] hover:bg-[#151F33] hover:text-[#F8FAFC] border border-transparent'
            }`}
          >
            {({isActive}) => (
              <>
                <LayoutDashboard size={18} className={`shrink-0 ${isActive ? 'text-white' : 'text-[#707FF0]'}`} /> 
                <span>{t('dashboard')}</span>
              </>
            )}
          </NavLink>

          <NavLink 
            to="/upload" 
            className={({isActive}) => `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              isActive 
                ? 'bg-[#707FF0] text-white font-bold shadow-md shadow-[#707FF0]/25 border border-[#707FF0]' 
                : 'text-[#96A8C0] hover:bg-[#151F33] hover:text-[#F8FAFC] border border-transparent'
            }`}
          >
            {({isActive}) => (
              <>
                <Upload size={18} className={`shrink-0 ${isActive ? 'text-white' : 'text-[#707FF0]'}`} /> 
                <span>{t('uploadVideo')}</span>
              </>
            )}
          </NavLink>

          <NavLink 
            to="/events" 
            className={({isActive}) => `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              isActive 
                ? 'bg-[#707FF0] text-white font-bold shadow-md shadow-[#707FF0]/25 border border-[#707FF0]' 
                : 'text-[#96A8C0] hover:bg-[#151F33] hover:text-[#F8FAFC] border border-transparent'
            }`}
          >
            {({isActive}) => (
              <>
                <History size={18} className={`shrink-0 ${isActive ? 'text-white' : 'text-[#707FF0]'}`} /> 
                <span>{t('eventsHistory')}</span>
              </>
            )}
          </NavLink>

          <NavLink 
            to="/cases" 
            className={({isActive}) => `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              isActive 
                ? 'bg-[#707FF0] text-white font-bold shadow-md shadow-[#707FF0]/25 border border-[#707FF0]' 
                : 'text-[#96A8C0] hover:bg-[#151F33] hover:text-[#F8FAFC] border border-transparent'
            }`}
          >
            {({isActive}) => (
              <>
                <Folder size={18} className={`shrink-0 ${isActive ? 'text-white' : 'text-[#707FF0]'}`} /> 
                <span>{t('investigationCases')}</span>
              </>
            )}
          </NavLink>

          <NavLink 
            to="/confidence" 
            className={({isActive}) => `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              isActive 
                ? 'bg-[#707FF0] text-white font-bold shadow-md shadow-[#707FF0]/25 border border-[#707FF0]' 
                : 'text-[#96A8C0] hover:bg-[#151F33] hover:text-[#F8FAFC] border border-transparent'
            }`}
          >
            {({isActive}) => (
              <>
                <BarChart3 size={18} className={`shrink-0 ${isActive ? 'text-white' : 'text-[#707FF0]'}`} /> 
                <span>{t('aiStats')}</span>
              </>
            )}
          </NavLink>

          <NavLink 
            to="/settings" 
            className={({isActive}) => `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              isActive 
                ? 'bg-[#707FF0] text-white font-bold shadow-md shadow-[#707FF0]/25 border border-[#707FF0]' 
                : 'text-[#96A8C0] hover:bg-[#151F33] hover:text-[#F8FAFC] border border-transparent'
            }`}
          >
            {({isActive}) => (
              <>
                <Settings size={18} className={`shrink-0 ${isActive ? 'text-white' : 'text-[#707FF0]'}`} /> 
                <span>{t('settings')}</span>
              </>
            )}
          </NavLink>

          <NavLink 
            to="/health" 
            className={({isActive}) => `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              isActive 
                ? 'bg-[#707FF0] text-white font-bold shadow-md shadow-[#707FF0]/25 border border-[#707FF0]' 
                : 'text-[#96A8C0] hover:bg-[#151F33] hover:text-[#F8FAFC] border border-transparent'
            }`}
          >
            {({isActive}) => (
              <>
                <Activity size={18} className={`shrink-0 ${isActive ? 'text-white' : 'text-[#707FF0]'}`} /> 
                <span>{t('systemHealth')}</span>
              </>
            )}
          </NavLink>
        </nav>

        {/* Global background uploads progress indicator inside Sidebar */}
        {backgroundUploads.length > 0 && (
          <div className="p-3 border-t border-[#26344A] bg-[#151F33]/40 space-y-2">
            <span className="text-[10px] font-bold text-[#96A8C0] uppercase tracking-wider block">
              {lang === "ar" ? "تحميلات قيد المعالجة" : "Active Ingestions"}
            </span>
            {backgroundUploads.map(up => (
              <div key={up.id} className="text-xs space-y-1 bg-[#0F172A] p-2 rounded-lg border border-[#26344A] shadow-2xs">
                <div className="flex justify-between items-center text-[#D7E0EE]">
                  <span className="truncate max-w-[120px] font-medium text-[#F8FAFC]">{up.name}</span>
                  <span className="font-mono text-[10px] font-bold text-[#707FF0]">{up.progress}%</span>
                </div>
                <div className="w-full bg-[#151F33] h-1.5 rounded-full overflow-hidden">
                  <div className="bg-[#707FF0] h-full transition-all duration-300" style={{ width: `${up.progress}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer info badge */}
        <div className="p-3.5 border-t border-[#26344A] bg-[#0A1023] flex items-center justify-between text-[11px] text-[#96A8C0]">
          <div className="flex items-center gap-1.5 font-medium">
            <ShieldCheck size={14} className="text-[#00D090]" />
            <span>{lang === "ar" ? "حماية محلية 100%" : "100% Edge AI"}</span>
          </div>
          <span className="font-mono text-[10px] bg-[#151F33] text-[#707FF0] border border-[#26344A] px-1.5 py-0.5 rounded font-bold">
            v2.0
          </span>
        </div>
      </aside>
      
      {/* Main Content Area */}
      <main className="flex-1 overflow-auto bg-[#020618] relative">
        <Outlet context={{ uploadVideoFile, backgroundUploads, videoProgressMap }} />
      </main>
    </div>
  );
}
