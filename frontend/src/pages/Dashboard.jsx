import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import { 
  Play, ShieldAlert, Video, Trash, Bell, Volume2, VolumeX, CheckCircle2, 
  Upload, FileVideo, Plus, ArrowLeft, Grid, Maximize2, Minimize2, Radio, Film,
  LayoutGrid, Layers, Briefcase, ExternalLink, X, MonitorPlay
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import api from '../services/api';

export default function Dashboard() {
  const { lang, dir, t } = useLanguage();
  const navigate = useNavigate();

  const outletCtx = useOutletContext() || {};
  const videoProgressMap = outletCtx.videoProgressMap || {};

  const [cameras, setCameras] = useState([]);
  const [videos, setVideos] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Multi-Camera Grid vs Single Camera Expanded View State
  const [viewMode, setViewMode] = useState("grid"); // "grid" | "expanded"
  const [layoutMode, setLayoutMode] = useState("grid"); // "grid" | "quad" | "single"
  const [expandedCamId, setExpandedCamId] = useState(null);

  // Quick Add Camera Modal State (requires stream URL only)
  const [showAddModal, setShowAddModal] = useState(false);
  const [streamUrl, setStreamUrl] = useState('');
  const [addingCamera, setAddingCamera] = useState(false);

  const [activeItem, setActiveItem] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(true);

  // Quick Video File Upload State
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const fetchDashboardData = useCallback(async () => {
    try {
      const [camsRes, videosRes, alertsRes] = await Promise.all([
        api.get('/cameras'),
        api.get('/videos'),
        api.get('/alerts')
      ]);

      setCameras(camsRes.data || []);
      setVideos(videosRes.data || []);

      const sortedAlerts = (alertsRes.data || []).sort((a, b) => b.id - a.id);
      
      const unplayedAlerts = sortedAlerts.filter(a => {
        return a.played_sound !== true && a.acknowledged !== true;
      });

      if (unplayedAlerts.length > 0 && soundEnabled) {
        playBeepAlert();
        unplayedAlerts.forEach(async (a) => {
          try {
            await api.put(`/alerts/${a.id}/played-sound`);
          } catch (err) {
            console.error("Failed to mark alert sound as played:", err);
          }
        });
      }

      const activeAlerts = sortedAlerts.filter(a => a.acknowledged !== true);
      setAlerts(activeAlerts);

      setActiveItem(prev => {
        if (!prev && (camsRes.data || []).length > 0) {
          return { ...camsRes.data[0], type: 'camera' };
        }
        if (prev && prev.type === 'camera') {
          const freshCam = (camsRes.data || []).find(c => c.id === prev.id);
          if (freshCam) return { ...freshCam, type: 'camera' };
        }
        return prev;
      });
    } catch (err) {
      console.error("Dashboard poll failed:", err);
    } finally {
      setLoading(false);
    }
  }, [soundEnabled]);

  const playBeepAlert = () => {
    try {
      const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtxClass) return;
      const audioCtx = new AudioCtxClass();
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
      
      const osc1 = audioCtx.createOscillator();
      const gain1 = audioCtx.createGain();
      osc1.type = 'sawtooth';
      osc1.frequency.setValueAtTime(880, audioCtx.currentTime);
      gain1.gain.setValueAtTime(0.3, audioCtx.currentTime);
      gain1.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);
      osc1.connect(gain1);
      gain1.connect(audioCtx.destination);
      osc1.start();
      osc1.stop(audioCtx.currentTime + 0.25);

      setTimeout(() => {
        try {
          const osc2 = audioCtx.createOscillator();
          const gain2 = audioCtx.createGain();
          osc2.type = 'sawtooth';
          osc2.frequency.setValueAtTime(1046.5, audioCtx.currentTime);
          gain2.gain.setValueAtTime(0.35, audioCtx.currentTime);
          gain2.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.35);
          osc2.connect(gain2);
          gain2.connect(audioCtx.destination);
          osc2.start();
          osc2.stop(audioCtx.currentTime + 0.35);
        } catch (e) {}
      }, 250);
    } catch (e) {
      console.log("Audio play blocked by browser policy", e);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    
    // Connect native EventSource SSE stream for instant real-time security alerts
    const baseURL = api.defaults.baseURL || `http://${window.location.hostname}:8001/api`;
    const sseUrl = `${baseURL.replace(/\/$/, '')}/alerts/stream`;
    
    let eventSource = null;
    try {
      eventSource = new EventSource(sseUrl);

      const handleIncomingAlert = (e) => {
        try {
          const newAlert = JSON.parse(e.data);
          const rawType = String(newAlert.type || newAlert.event?.type || '').toLowerCase();
          if (['progress_update', 'progress', 'status_update', 'analysis_complete', 'analysis_failed', 'heartbeat'].includes(rawType)) {
            return;
          }

          setAlerts(prev => {
            if (prev.some(a => a.id === newAlert.id)) return prev;
            return [newAlert, ...prev];
          });

          if (soundEnabled && newAlert.played_sound !== true) {
            playBeepAlert();
          }
        } catch (err) {
          console.error("Error parsing SSE alert:", err);
        }
      };

      eventSource.addEventListener('live_alert', handleIncomingAlert);
      eventSource.addEventListener('alert', handleIncomingAlert);
      eventSource.addEventListener('video_job_event', handleIncomingAlert);

      const handleCompletion = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.video_id) {
            setVideos(prev => prev.map(v => v.id === data.video_id ? { ...v, status: 'completed' } : v));
          }
          fetchDashboardData();
        } catch (err) {}
      };

      eventSource.addEventListener('analysis_complete', handleCompletion);
      eventSource.addEventListener('status_update', handleCompletion);

      eventSource.onerror = (err) => {
        console.warn("SSE alert stream disconnected. EventSource will reconnect automatically.");
      };
    } catch (err) {
      console.error("Failed to initialize SSE EventSource:", err);
    }

    const interval = setInterval(fetchDashboardData, 3000);

    return () => {
      clearInterval(interval);
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [fetchDashboardData, soundEnabled]);

  const toggleAnalysis = async (camId, running) => {
    try {
      const endpoint = running ? `/cameras/${camId}/stop-analysis` : `/cameras/${camId}/start-analysis`;
      const res = await api.post(endpoint);
      setCameras(cameras.map(c => c.id === camId ? res.data : c));
      if (activeItem && activeItem.id === camId) {
        setActiveItem({ ...res.data, type: 'camera' });
      }
    } catch (err) {
      console.error("Failed to toggle camera analysis:", err);
    }
  };

  const handleAcknowledgeAlert = async (alertId, e) => {
    if (e) e.stopPropagation();
    setAlerts(prev => prev.filter(a => a.id !== alertId));
    try {
      await api.delete(`/alerts/${alertId}`);
    } catch (err) {
      console.error("Failed to acknowledge alert:", err);
      fetchDashboardData();
    }
  };

  const handleClearAllAlerts = async () => {
    if (!window.confirm("هل أنت متأكد من رغبتك في تطهير جميع السجلات والتنبيهات؟")) return;
    try {
      await api.delete('/alerts');
      setAlerts([]);
      fetchDashboardData();
    } catch (err) {
      console.error("Failed to clear alerts:", err);
    }
  };

  const handleQuickUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;

    const formData = new FormData();
    formData.append("file", uploadFile);

    try {
      setUploading(true);
      setUploadProgress(10);
      
      await api.post("/upload-video", formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        }
      });

      setUploadFile(null);
      setUploadProgress(0);
      fetchDashboardData();
    } catch (err) {
      console.error("Upload failed:", err);
      const errorDetail = err.response?.data?.detail || err.message || "Failed to upload video";
      alert(`فشل رفع الفيديو: ${errorDetail}`);
    } finally {
      setUploading(false);
    }
  };

  const triggerReplay = (alert) => {
    const event = alert?.event || {};
    const vidId = event.video_id || alert?.video_id || event.source_id || (videos.length > 0 ? videos[0].id : null);
    const evId = event.id || alert?.event_id || alert?.id;
    if (vidId) {
      navigate('/video-replay', {
        state: {
          videoId: vidId,
          eventId: evId
        }
      });
    }
  };

  const getAlertCardStyles = (type = '') => {
    const safeType = type || '';
    if (safeType.startsWith("violence") || safeType.startsWith("accident") || safeType.startsWith("collision")) {
      // Critical Incident: #2A1020 background, #F02050 text, #B91C3B border
      return { border: "border-[#B91C3B] hover:border-[#F02050] bg-[#2A1020] hover:bg-[#341227]", text: "text-[#F02050]", bg: "bg-[#2A1020] text-[#F02050] border border-[#B91C3B]" };
    }
    if (safeType.startsWith("theft") || safeType.startsWith("warning")) {
      // Warning: #2A2110 background, #F59E0B text, #C09020 border
      return { border: "border-[#C09020] hover:border-[#F59E0B] bg-[#2A2110] hover:bg-[#352914]", text: "text-[#F59E0B]", bg: "bg-[#2A2110] text-[#F59E0B] border border-[#C09020]" };
    }
    // Info: #10223B background, #4299F5 text, #4299F5/40 border
    return { border: "border-[#4299F5]/40 hover:border-[#4299F5] bg-[#10223B] hover:bg-[#162D4E]", text: "text-[#4299F5]", bg: "bg-[#10223B] text-[#4299F5] border border-[#4299F5]/50" };
  };

  const activeWarningType = useMemo(() => {
    const now = new Date();
    const realTimeAlerts = alerts.filter(a => {
      if (a.acknowledged || a.status === 'read') return false;
      const alertTime = new Date(a.created_at || a.event?.start_time);
      return ((now - alertTime) / 1000) <= 30;
    });
    if (realTimeAlerts.length > 0) {
      return realTimeAlerts[0].event?.type || "threat";
    }
    return null;
  }, [alerts]);

  const expandedCamera = useMemo(() => {
    if (!expandedCamId) return null;
    return cameras.find(c => c.id === expandedCamId) || null;
  }, [cameras, expandedCamId]);

  const handleExpandCam = (camId) => {
    setExpandedCamId(camId);
    setViewMode("expanded");
  };

  const handleReturnToGrid = () => {
    setExpandedCamId(null);
    setViewMode("grid");
  };

  const handleQuickAddCamera = async (e) => {
    e.preventDefault();
    if (!streamUrl.trim()) return;

    try {
      setAddingCamera(true);
      await api.post('/cameras', {
        stream_url: streamUrl.trim()
      });
      setStreamUrl('');
      setShowAddModal(false);
      await fetchDashboardData();
    } catch (err) {
      console.error("Failed to add camera:", err);
      alert("فشل إضافة الكاميرا: " + (err.response?.data?.detail || err.message));
    } finally {
      setAddingCamera(false);
    }
  };

  const validAlerts = alerts.filter(a => {
    const rawT = String(a.event?.type || a.alert_type || a.type || '').toLowerCase();
    return !['progress_update', 'progress', 'status_update', 'analysis_complete', 'analysis_failed', 'heartbeat'].includes(rawT);
  });

  return (
    <div className="p-6 max-w-7xl mx-auto h-full flex flex-col space-y-6 overflow-y-auto bg-[#020618] text-[#D7E0EE]" dir={dir}>
      
      {/* Header Bar */}
      <header className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 bg-[#0F172A] p-4 rounded-2xl border border-[#26344A] shadow-sm">
        <div className={dir === 'rtl' ? 'text-right' : 'text-left'}>
          <h2 className={`text-2xl font-bold tracking-tight text-[#D7E0EE] font-sans flex items-center gap-2.5 ${dir === 'rtl' ? 'justify-end' : 'justify-start'}`}>
            {t('liveSurveillance')} <ShieldAlert className="text-[#F02050]" />
          </h2>
          <p className="text-[#96A8C0] text-xs mt-1">{t('liveSurveillanceSub')}</p>
        </div>

        {/* Global Controls & Actions */}
        <div className="flex flex-wrap items-center gap-3">
          <button 
            onClick={handleClearAllAlerts}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#151F33] hover:bg-[#2A1020] hover:border-[#B91C3B] text-[#D7E0EE] hover:text-[#F02050] border border-[#26344A] rounded-xl text-xs font-semibold transition-all"
          >
            <Trash size={14} />
            <span>{lang === "ar" ? "تطهير السجلات الكلية" : "Clear All Records"}</span>
          </button>

          <button 
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
              soundEnabled 
                ? 'bg-[#2A1020] border-[#B91C3B] text-[#F02050] hover:bg-[#FCDADA]' 
                : 'bg-[#151F33] border-[#26344A] text-[#D7E0EE] hover:bg-[#1D293D]'
            }`}
          >
            {soundEnabled ? <Volume2 size={14} className="text-[#F02050] animate-pulse" /> : <VolumeX size={14} />}
            <span>{soundEnabled ? t('muteAlerts') : t('unmuteAlerts')}</span>
          </button>

          <div className="flex items-center gap-1.5 px-4 py-2 bg-[#0B2825] text-[#00D090] border border-[#087F5B] rounded-xl text-xs font-bold">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>{t('aiActive')}</span>
          </div>
        </div>
      </header>

      {/* TOP ROW: 2 Columns Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        
        {/* CENTER COLUMN (2/3 width): Dynamic Multi-Camera Grid OR Expanded Single Camera View */}
        <div className="lg:col-span-2 bg-[#0F172A] border border-[#26344A] rounded-3xl overflow-hidden shadow-sm flex flex-col min-h-[520px] relative">
          
          {/* Header Bar inside video stream box */}
          <div className="p-3.5 bg-[#151F33] border-b border-[#26344A] flex flex-wrap justify-between items-center gap-3 z-10">
            <div className="flex items-center gap-2">
              {/* Layout Mode Selector */}
              <div className="flex items-center bg-[#0F172A] border border-[#26344A] rounded-xl p-0.5 shadow-sm">
                <button
                  type="button"
                  onClick={() => { setLayoutMode("grid"); setViewMode("grid"); }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    layoutMode === "grid" && viewMode === "grid"
                      ? 'bg-[#707FF0] text-white shadow-sm shadow-slate-500/10'
                      : 'text-[#96A8C0] hover:text-[#D7E0EE]'
                  }`}
                  title={lang === "ar" ? "عرض جميع الكاميرات في شبكة موحدة" : "All Cameras Grid"}
                >
                  <LayoutGrid size={14} />
                  <span>{lang === "ar" ? "شبكة الكل" : "Grid"}</span>
                </button>

                <button
                  type="button"
                  onClick={() => { setLayoutMode("quad"); setViewMode("grid"); }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    layoutMode === "quad" && viewMode === "grid"
                      ? 'bg-[#707FF0] text-white shadow-sm shadow-slate-500/10'
                      : 'text-[#96A8C0] hover:text-[#D7E0EE]'
                  }`}
                  title={lang === "ar" ? "عرض 4 كاميرات في تقسيم رباعي" : "Quad 2x2 View"}
                >
                  <Grid size={14} />
                  <span>{lang === "ar" ? "رباعي 2×2" : "Quad"}</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setLayoutMode("single");
                    if (!expandedCamId && cameras.length > 0) {
                      setExpandedCamId(cameras[0].id);
                    }
                    setViewMode("expanded");
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    viewMode === "expanded" || layoutMode === "single"
                      ? 'bg-[#707FF0] text-white shadow-sm shadow-slate-500/10'
                      : 'text-[#96A8C0] hover:text-[#D7E0EE]'
                  }`}
                  title={lang === "ar" ? "تركيز على كاميرا مفردة مع التبديل" : "Single Camera Focus"}
                >
                  <Maximize2 size={14} />
                  <span>{lang === "ar" ? "مفرد" : "Focus"}</span>
                </button>
              </div>

              <span className="text-xs text-[#96A8C0] font-mono hidden sm:inline">
                ({cameras.length} {lang === "ar" ? "كاميرات متصلة" : "cameras"})
              </span>

              <span className="inline-flex items-center gap-1 bg-[#151F33] text-[#707FF0] border border-[#26344A] px-2.5 py-0.5 rounded-full text-[10px] font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-[#707FF0] animate-ping"></span>
                {t('aiRunning')}
              </span>
            </div>

            <div className="flex items-center gap-2">
              {/* Quick Add Camera Button (Stream URL Only) */}
              <button
                type="button"
                onClick={() => setShowAddModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#707FF0] hover:bg-[#3935A8] text-white rounded-xl text-xs font-bold transition-all shadow-sm shadow-slate-500/10"
              >
                <Plus size={14} />
                <span>{lang === "ar" ? "+ إضافة كاميرا" : "+ Add Camera"}</span>
              </button>

              {(viewMode === "expanded" || layoutMode === "single") && expandedCamera && (
                <button 
                  onClick={() => toggleAnalysis(expandedCamera.id, expandedCamera.is_analysis_running)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all border ${
                    expandedCamera.is_analysis_running 
                      ? 'bg-[#2A1020] text-[#F02050] border border-[#B91C3B] hover:bg-[#341227]' 
                      : 'bg-[#707FF0] text-white border-[#707FF0] hover:bg-[#3935A8]'
                  }`}
                >
                  {expandedCamera.is_analysis_running ? t('stopAI') : t('startAI')}
                </button>
              )}
            </div>
          </div>

          {/* Quick Camera Tabs Switcher for Single / Focus Mode */}
          {(viewMode === "expanded" || layoutMode === "single") && cameras.length > 1 && (
            <div className="bg-[#151F33] px-4 py-2 border-b border-[#26344A]/80 flex items-center gap-2 overflow-x-auto z-10">
              <span className="text-[11px] text-[#96A8C0] font-bold shrink-0">{lang === "ar" ? "التبديل بين الكاميرات:" : "Switch Camera:"}</span>
              {cameras.map((cam, idx) => {
                const isSelected = (expandedCamera && expandedCamera.id === cam.id) || (!expandedCamera && idx === 0);
                return (
                  <button
                    key={cam.id}
                    onClick={() => {
                      setExpandedCamId(cam.id);
                      setViewMode("expanded");
                      setLayoutMode("single");
                    }}
                    className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold shrink-0 transition-all border ${
                      isSelected
                        ? 'bg-[#707FF0] text-white border-[#707FF0] shadow-sm'
                        : 'bg-[#0F172A] text-[#D7E0EE] border-[#26344A] hover:border-[#26344A]'
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${cam.is_analysis_running ? 'bg-emerald-400 animate-pulse' : 'bg-[#707FF0]'}`}></span>
                    <span>{cam.name}</span>
                  </button>
                );
              })}
            </div>
          )}

          {/* MAIN PLAYER VIEW CONTAINER */}
          <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden min-h-[440px] p-2">
            
            {/* VIEW MODE 1: EXPANDED / SINGLE FOCUS CAMERA */}
            {(viewMode === "expanded" || layoutMode === "single") && expandedCamera ? (
              <div className="relative w-full h-full flex items-center justify-center bg-black rounded-2xl overflow-hidden group">
                <img 
                  src={`http://${window.location.hostname}:8001/api/cameras/${expandedCamera.id}/video_feed`} 
                  alt={expandedCamera.name} 
                  className="w-full h-full object-contain opacity-95"
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = `http://localhost:8001/api/cameras/${expandedCamera.id}/video_feed`;
                  }}
                />

                {/* Camera Name & Status Badge Overlay */}
                <div className="absolute top-4 right-4 flex items-center gap-2 pointer-events-none">
                  <span className="bg-[#0F172A]/90 text-[#F8FAFC] px-3.5 py-1.5 rounded-xl text-xs font-bold border border-[#26344A] backdrop-blur-md">
                    {expandedCamera.name}
                  </span>
                  <span className={`px-2.5 py-1 rounded-xl text-xs font-bold backdrop-blur-md ${
                    expandedCamera.is_analysis_running ? 'bg-[#0B2825] text-[#00D090] border border-emerald-500/30' : 'bg-slate-800/80 text-[#96A8C0]'
                  }`}>
                    {expandedCamera.is_analysis_running ? (lang === "ar" ? "بث مباشر نشط" : "LIVE") : (lang === "ar" ? "متوقف" : "OFF")}
                  </span>
                </div>
                
                {/* Minimize / Return to Grid overlay button */}
                <button
                  onClick={handleReturnToGrid}
                  className="absolute top-4 left-4 bg-[#0F172A]/80 hover:bg-[#0F172A] text-[#F8FAFC] p-2.5 rounded-xl border border-[#26344A] backdrop-blur-md opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2 text-xs font-bold z-30"
                >
                  <Minimize2 size={16} />
                  <span>{lang === "ar" ? "تصغير لشبكة الكاميرات" : "Return to Grid"}</span>
                </button>
              </div>
            ) : (

              /* VIEW MODE 2 & 3: MULTI-CAMERA MATRIX GRID / QUAD VIEW */
              cameras.length === 0 ? (
                <div className="text-center text-[#96A8C0] text-xs py-20 flex flex-col items-center">
                  <Video size={56} className="mx-auto mb-3 opacity-20" />
                  <p className="font-semibold text-[#96A8C0] text-sm">{t('noCameras')}</p>
                  <p className="text-[#96A8C0] mt-1 max-w-sm">
                    {lang === "ar" ? "لم يتم ربط أي كاميرا مراقبة حتى الآن. يمكنك إضافة كاميرا برابط مباشر خلال ثوانٍ." : "No cameras connected. You can add one with just a URL in seconds."}
                  </p>
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-lg shadow-indigo-600/30"
                  >
                    <Plus size={14} />
                    <span>{lang === "ar" ? "إضافة أول كاميرا الآن" : "Add Camera Now"}</span>
                  </button>
                </div>
              ) : (
                <div className={`w-full h-full grid gap-3 p-1 ${
                  layoutMode === "quad"
                    ? 'grid-cols-1 md:grid-cols-2'
                    : cameras.length === 1 
                      ? 'grid-cols-1' 
                      : cameras.length === 2 
                        ? 'grid-cols-1 md:grid-cols-2' 
                        : cameras.length <= 4 
                          ? 'grid-cols-1 md:grid-cols-2' 
                          : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'
                }`}>
                  {(layoutMode === "quad" ? cameras.slice(0, 4) : cameras).map((cam) => (
                    <div 
                      key={cam.id}
                      onClick={() => handleExpandCam(cam.id)}
                      className="relative bg-[#0F172A] rounded-2xl border border-[#26344A] overflow-hidden group cursor-pointer hover:border-indigo-500/60 transition-all flex flex-col justify-between min-h-[220px]"
                    >
                      {/* Live Feed Image */}
                      <img 
                        src={`http://${window.location.hostname}:8001/api/cameras/${cam.id}/video_feed`} 
                        alt={cam.name} 
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 opacity-90"
                        onError={(e) => {
                          e.target.onerror = null;
                          e.target.src = `http://localhost:8001/api/cameras/${cam.id}/video_feed`;
                        }}
                      />

                      {/* Top Overlay Badge */}
                      <div className="absolute top-3 left-3 right-3 flex justify-between items-center pointer-events-none">
                        <span className="bg-[#0F172A]/80 text-[#F8FAFC] px-3 py-1 rounded-xl text-[10px] font-bold border border-[#26344A] backdrop-blur-md">
                          {cam.name}
                        </span>
                        
                        <div className="flex items-center gap-1.5">
                          <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold backdrop-blur-md ${
                            cam.is_analysis_running ? 'bg-[#0B2825] text-[#00D090] border border-emerald-500/30' : 'bg-slate-800/80 text-[#96A8C0]'
                          }`}>
                            {cam.is_analysis_running ? (lang === "ar" ? "بث نشط" : "LIVE") : (lang === "ar" ? "متوقف" : "OFF")}
                          </span>
                        </div>
                      </div>

                      {/* Hover Expand Button Overlay */}
                      <div className="absolute inset-0 bg-indigo-950/40 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 text-white font-bold text-xs">
                        <Maximize2 size={20} className="text-[#45C5F5] animate-pulse" />
                        <span>{lang === "ar" ? "انقر لتكبير الكاميرا" : "Click to Focus"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )
            )}

            {/* Bottom Alert Warning overlay banner */}
            {activeWarningType && (
              <div className="absolute bottom-6 left-6 right-6 bg-rose-600/90 text-white py-3.5 px-8 rounded-2xl flex items-center justify-center gap-2 border border-rose-500 shadow-2xl font-bold tracking-wider animate-pulse z-20">
                <ShieldAlert size={20} className="animate-bounce" />
                <span>{t('threatDetected')}: {t(activeWarningType.split('_')[0]) || activeWarningType}!</span>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN (1/3 width): Real-Time Alerts + Processed Videos & Quick Upload */}
        <div className="flex flex-col space-y-6">
          
          {/* UPPER HALF: Real-Time Alerts Panel */}
          <div className="bg-[#0F172A] border border-[#26344A] rounded-3xl p-5 shadow-sm flex flex-col h-[280px]">
            <div className="pb-3 border-b border-[#26344A]/60 flex justify-between items-center">
              <h3 className="font-bold text-[#D7E0EE] text-xs flex items-center gap-2 tracking-wider font-sans">
                <Bell size={16} className="text-[#F02050]" /> {t('realtimeAlerts')}
              </h3>
              <span className="bg-[#151F33] border border-[#26344A] px-2.5 py-0.5 rounded-full text-[10px] font-bold text-[#45C5F5] font-mono">
                {validAlerts.length}
              </span>
            </div>

            <div className="flex-1 overflow-y-auto py-3 space-y-3 pl-1">
              {validAlerts.length === 0 ? (
                <div className="h-full flex flex-col justify-center items-center text-[#96A8C0] py-8 text-center">
                  <ShieldAlert size={32} className="opacity-20 mb-2" />
                  <p className="text-xs italic">{t('noAlerts')}</p>
                </div>
              ) : (
                validAlerts.map((alert) => {
                  const event = alert?.event || {};
                  const eventType = event.type || alert?.alert_type || alert?.type || 'threat';
                  const styles = getAlertCardStyles(eventType);
                  const riskVal = event.risk_score != null ? event.risk_score : (event.confidence ? (event.confidence * 100).toFixed(0) : 85);
                  const isUploaded = alert.source_type === 'UPLOADED_VIDEO' || event.source_type === 'UPLOADED_VIDEO' || event.video_id;
                  
                  const matchingVideo = videos.find(v => v.id === event.video_id || v.id === alert.video_id);
                  const sourceLabel = isUploaded 
                    ? `فيديو: ${matchingVideo ? matchingVideo.filename : (event.video_id || '').slice(0, 8)}`
                    : `كاميرا: ${event.camera_id ? `CAM_${event.camera_id}` : 'بث مباشر'}`;

                  return (
                    <div 
                      key={alert.id}
                      onClick={() => triggerReplay(alert)}
                      className={`p-3.5 border rounded-2xl transition-all cursor-pointer flex flex-col gap-2 shadow-md relative group ${styles.border}`}
                    >
                      <div className="flex justify-between items-center">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${styles.bg} ${styles.text}`}>
                          {eventType.toUpperCase()}
                        </span>
                        <span className="text-[10px] text-[#96A8C0] font-mono">
                          ID: #{alert.id}
                        </span>
                      </div>

                      <div className="flex justify-between items-center">
                        <p className="text-xs font-bold text-[#D7E0EE]">
                          {t(eventType.split('_')[0]) || eventType}
                        </p>
                        <span className="text-[9px] text-[#45C5F5] bg-[#151F33] border border-[#26344A] px-2 py-0.5 rounded-md font-sans text-[#707FF0]">
                          {sourceLabel}
                        </span>
                      </div>

                      {/* Exact Incident Timestamp and Video Second */}
                      <div className="text-[10px] text-[#96A8C0] font-mono flex flex-col gap-0.5 bg-[#151F33] p-2 rounded-xl border border-[#26344A]/50">
                        {event.explainability?.timestamp_sec != null && (
                          <div className="flex items-center justify-between text-[#707FF0] font-bold">
                            <span>⏱️ توقيت الحادث:</span>
                            <span>{event.explainability?.formatted_offset || '00:00'} (الثانية {Number(event.explainability?.timestamp_sec).toFixed(1)}s)</span>
                          </div>
                        )}
                        <div className="flex items-center justify-between text-[#96A8C0] text-[9px]">
                          <span>📅 تاريخ الرصد:</span>
                          <span>{event.start_time ? new Date(event.start_time).toLocaleTimeString('ar-EG') : (alert.created_at ? new Date(alert.created_at).toLocaleTimeString('ar-EG') : 'الآن')}</span>
                        </div>
                      </div>

                      <div className="flex justify-between items-center text-[10px] text-[#96A8C0] font-mono pt-1 border-t border-[#26344A]/60">
                        <span>معدل الخطر: {riskVal}%</span>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate('/cases', {
                                state: {
                                  fromEvent: {
                                    id: alert.event?.id || alert.id,
                                    type: eventType,
                                    description: `حادث ${eventType} مسجل برقم #${alert.event?.id || alert.id} (${sourceLabel})`,
                                    risk_score: riskVal
                                  }
                                }
                              });
                            }}
                            className="flex items-center gap-1 px-2 py-0.5 bg-[#707FF0] hover:bg-[#3935A8] text-white rounded-lg text-[10px] font-bold transition-all shadow-sm shadow-slate-500/10"
                            title={lang === "ar" ? "إنشاء قضية جديدة لهذا الحادث مباشرة وربطه بها" : "Open investigation case for this incident"}
                          >
                            <Briefcase size={11} />
                            <span>{lang === "ar" ? "فتح قضية" : "Case"}</span>
                          </button>
                          <button
                            onClick={(e) => handleAcknowledgeAlert(alert.id, e)}
                            className="opacity-0 group-hover:opacity-100 p-1 text-[#96A8C0] hover:text-[#F02050] transition-opacity"
                            title="حذف الإنذار"
                          >
                            <Trash size={13} />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* LOWER HALF: Processed Videos & Embedded Quick Upload */}
          <div className="bg-[#0F172A] border border-[#26344A] rounded-3xl p-5 shadow-sm flex flex-col h-[280px]">
            <div className="pb-3 border-b border-[#26344A]/60 flex justify-between items-center">
              <h3 className="font-bold text-[#D7E0EE] text-xs flex items-center gap-2 tracking-wider font-sans">
                <FileVideo size={16} className="text-[#45C5F5]" /> {t('processedVideos')}
              </h3>
              <span className="bg-[#151F33] border border-[#26344A] px-2.5 py-0.5 rounded-full text-[10px] font-bold text-[#45C5F5] font-mono">
                {videos.length}
              </span>
            </div>

            {/* Embedded Quick Upload Form */}
            <form onSubmit={handleQuickUpload} className="my-3 flex items-center gap-2">
              <input 
                type="file" 
                accept="video/*"
                onChange={(e) => setUploadFile(e.target.files[0])}
                className="hidden"
                id="quick-video-input"
              />
              <label 
                htmlFor="quick-video-input"
                className="flex-1 bg-[#151F33] border border-[#26344A] hover:border-[#26344A] rounded-xl px-3 py-2 text-[11px] text-[#D7E0EE] truncate cursor-pointer flex items-center gap-2"
              >
                <Upload size={14} className="text-[#45C5F5] shrink-0" />
                <span className="truncate">{uploadFile ? uploadFile.name : (lang === "ar" ? "اختر فيديو أمني للرفع..." : "Select security video...")}</span>
              </label>

              <button
                type="submit"
                disabled={!uploadFile || uploading}
                className="bg-[#707FF0] hover:bg-[#3935A8] disabled:opacity-40 text-white px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 flex items-center gap-1 shadow-sm shadow-slate-500/10"
              >
                <Plus size={14} />
                <span>{uploading ? `${uploadProgress}%` : (lang === "ar" ? "رفع وتحليل" : "Upload")}</span>
              </button>
            </form>

            <div className="flex-1 overflow-y-auto space-y-2.5 pl-1">
              {videos.length === 0 ? (
                <div className="h-full flex flex-col justify-center items-center text-[#96A8C0] py-6 text-center">
                  <FileVideo size={32} className="opacity-20 mb-2" />
                  <p className="text-xs italic">{t('noVideos')}</p>
                </div>
              ) : (
                videos.map((vid) => {
                  const liveProg = videoProgressMap[vid.id];
                  
                  const isCompleted = (vid.status === 'completed' || vid.status === 'clean') || 
                                      (liveProg && (liveProg.progress_percentage === 100 || liveProg.status === 'completed' || liveProg.current_stage === 'COMPLETED'));
                  
                  const isProcessing = !isCompleted && (vid.status === 'processing' || vid.status === 'pending' || vid.status === 'queued' || (liveProg && liveProg.status === 'processing'));

                  // Calculate threat count from DB events + matching alerts in state
                  const dbEventsCount = vid.events ? vid.events.length : 0;
                  const matchingAlertsCount = alerts.filter(a => {
                    const evVid = a.event?.video_id || a.video_id || a.source_id;
                    return evVid === vid.id || evVid === vid.filename || (evVid && vid.filename && evVid.includes(vid.filename));
                  }).length;
                  const threatCount = Math.max(dbEventsCount, matchingAlertsCount);

                  return (
                    <div 
                      key={vid.id}
                      onClick={() => navigate('/video-replay', { state: { videoId: vid.id } })}
                      className="p-3 bg-[#151F33] hover:bg-[#151F33] border border-[#26344A] hover:border-indigo-500/50 rounded-2xl transition-all cursor-pointer flex justify-between items-center"
                    >
                      <div className="flex items-center gap-2.5 truncate max-w-[65%]">
                        <FileVideo size={16} className="text-[#45C5F5] shrink-0" />
                        <div className="truncate">
                          <span className="text-xs font-bold text-[#D7E0EE] block truncate" title={vid.filename}>{vid.filename}</span>
                          <span className="text-[9px] text-[#96A8C0] font-mono block">ID: {vid.id.slice(0, 8)}</span>
                        </div>
                      </div>

                      <div className="shrink-0">
                        {isProcessing ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#2A2110] text-[#F59E0B] border border-[#C09020] animate-pulse">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span>
                            {liveProg && liveProg.progress_percentage > 0 
                              ? `${liveProg.progress_percentage}% (${liveProg.processing_fps || 0} FPS)` 
                              : (lang === "ar" ? "جاري المعالجة..." : "Processing...")}
                          </span>
                        ) : threatCount > 0 ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#2A1020] text-[#F02050] border border-rose-500/20">
                            <ShieldAlert size={10} />
                            {lang === "ar" ? `تم رصد ${threatCount} تهديدات` : `Threat Detected (${threatCount})`}
                          </span>
                        ) : vid.status === 'error' || vid.status === 'failed' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-[#96A8C0] border border-[#26344A]">
                            <CheckCircle2 size={10} />
                            {lang === "ar" ? "فشل التحليل" : "Analysis Failed"}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#0B2825] text-[#00D090] border border-[#087F5B]">
                            <CheckCircle2 size={10} />
                            {lang === "ar" ? "فيديو سليم" : "Clean Video"}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

        </div>
      </div>

      {/* BOTTOM ROW: Active Cameras Interactive Grid & Focus Selector */}
      <div className="bg-[#0F172A] border border-[#26344A] rounded-3xl p-6 shadow-sm space-y-4">
        <div className="flex justify-between items-center border-b border-[#26344A]/60 pb-3">
          <h3 className="text-sm font-bold text-[#D7E0EE] uppercase tracking-wider flex items-center gap-2">
            <Video size={16} className="text-[#45C5F5]" /> {t('activeCamerasGrid')}
          </h3>
          {viewMode === "expanded" && (
            <button
              onClick={handleReturnToGrid}
              className="text-xs text-[#45C5F5] font-bold hover:underline flex items-center gap-1"
            >
              <Grid size={14} />
              <span>{lang === "ar" ? "العودة لعرض الشبكة الكلية" : "Back to All Cameras Grid"}</span>
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {cameras.length === 0 ? (
            <p className="text-xs text-[#96A8C0] italic text-center col-span-full py-4">{t('noCameras')}</p>
          ) : (
            cameras.map((cam) => (
              <div 
                key={cam.id}
                onClick={() => handleExpandCam(cam.id)}
                className="p-4 bg-[#151F33] hover:bg-[#151F33] border border-[#26344A] hover:border-indigo-500/50 rounded-2xl transition-all cursor-pointer flex flex-col justify-between space-y-3"
              >
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold text-[#D7E0EE]">{cam.name}</span>
                  <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                    cam.is_analysis_running ? 'bg-[#0B2825] text-[#00D090] border border-[#087F5B]' : 'bg-slate-800 text-[#96A8C0]'
                  }`}>
                    {cam.is_analysis_running ? (lang === "ar" ? "بث نشط" : "LIVE") : (lang === "ar" ? "متوقف" : "OFF")}
                  </span>
                </div>

                <div className="text-[10px] text-[#96A8C0] truncate font-mono">
                  {cam.stream_url}
                </div>

                <div className="flex justify-between items-center pt-2 border-t border-[#26344A]/60">
                  <span className="text-[10px] text-[#96A8C0]">{cam.scene_type || "Mall"}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleAnalysis(cam.id, cam.is_analysis_running);
                    }}
                    className={`px-3 py-1 rounded-lg text-[10px] font-bold border transition-all ${
                      cam.is_analysis_running
                        ? 'bg-[#2A1020] text-[#F02050] border border-[#B91C3B] hover:bg-[#341227]'
                        : 'bg-indigo-600 text-white border-indigo-500/30 hover:bg-indigo-500'
                    }`}
                  >
                    {cam.is_analysis_running ? t('stopAI') : t('startAI')}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Quick Add Camera Modal (Requires ONLY Stream URL) */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-[#0F172A]/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0F172A] border border-[#26344A] rounded-3xl p-6 max-w-lg w-full shadow-2xl relative text-[#D7E0EE]">
            <div className="flex justify-between items-center pb-4 border-b border-[#26344A]">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-600/20 text-[#45C5F5]">
                  <Video size={18} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-[#D7E0EE]">
                    {lang === "ar" ? "إضافة كاميرا مراقبة جديدة" : "Add Security Camera"}
                  </h3>
                  <p className="text-xs text-[#96A8C0]">
                    {lang === "ar" ? "أدخل فقط رابط الكاميرا أو الـ API، وسيقوم النظام بكافة الإعدادات تلقائياً" : "Enter stream URL only. The system handles all settings automatically."}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-[#96A8C0] hover:text-[#D7E0EE] p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleQuickAddCamera} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-bold text-[#D7E0EE] mb-1.5">
                  {lang === "ar" ? "رابط البث أو عنوان الـ API (Stream URL) *" : "Stream / API URL *"}
                </label>
                <input
                  type="text"
                  required
                  value={streamUrl}
                  onChange={(e) => setStreamUrl(e.target.value)}
                  placeholder={lang === "ar" ? "مثال: 0 أو http://192.168.1.X:8080/video" : "e.g., 0, rtsp://..., http://..."}
                  className="w-full bg-[#151F33] border border-[#26344A] focus:border-indigo-500 rounded-xl px-4 py-2.5 text-sm text-[#D7E0EE] placeholder-slate-600 focus:outline-none font-mono"
                />
              </div>

              {/* Quick Presets */}
              <div>
                <span className="text-[11px] font-semibold text-[#96A8C0] block mb-2">
                  {lang === "ar" ? "نماذج سريعة جاهزة للاختيار بنقرة واحدة:" : "Quick 1-Click Presets:"}
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setStreamUrl('0')}
                    className="px-3 py-2 bg-[#020618] text-[#D7E0EE] hover:bg-slate-800 border border-[#26344A] hover:border-indigo-500 rounded-xl text-[11px] font-bold text-[#D7E0EE] text-center transition-all"
                  >
                    💻 كاميرا مدمجة (0)
                  </button>
                  <button
                    type="button"
                    onClick={() => setStreamUrl('http://192.168.1.50:8080/video')}
                    className="px-3 py-2 bg-[#020618] text-[#D7E0EE] hover:bg-slate-800 border border-[#26344A] hover:border-indigo-500 rounded-xl text-[11px] font-bold text-[#D7E0EE] text-center transition-all"
                  >
                    📱 هاتف IP Webcam
                  </button>
                  <button
                    type="button"
                    onClick={() => setStreamUrl('rtsp://admin:123456@192.168.1.100:554/stream1')}
                    className="px-3 py-2 bg-[#020618] text-[#D7E0EE] hover:bg-slate-800 border border-[#26344A] hover:border-indigo-500 rounded-xl text-[11px] font-bold text-[#D7E0EE] text-center transition-all"
                  >
                    📹 كاميرا RTSP
                  </button>
                </div>
              </div>

              <div className="p-3 bg-[#151F33] border border-[#26344A] rounded-xl text-[11px] text-[#D7E0EE]">
                💡 {lang === "ar" ? "يقوم النظام تلقائياً بتحديد بروتوكول البث وتسمية الكاميرا وبدء التحليل بالذكاء الاصطناعي فورياً." : "System auto-detects protocol, assigns camera name, and activates AI."}
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-[#26344A]">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 bg-[#151F33] hover:bg-[#1D293D] text-[#D7E0EE] rounded-xl text-xs font-bold transition-all border border-[#26344A]"
                >
                  {lang === "ar" ? "إلغاء" : "Cancel"}
                </button>
                <button
                  type="submit"
                  disabled={addingCamera || !streamUrl.trim()}
                  className="px-5 py-2 bg-[#707FF0] hover:bg-[#3935A8] disabled:opacity-40 text-white rounded-xl text-xs font-bold transition-all shadow-sm shadow-slate-500/10 flex items-center gap-1.5"
                >
                  <Plus size={14} />
                  <span>{addingCamera ? (lang === "ar" ? "جاري الإضافة..." : "Adding...") : (lang === "ar" ? "تأكيد وإضافة" : "Add Camera")}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
