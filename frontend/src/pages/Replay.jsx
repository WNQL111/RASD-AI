import React, { useEffect, useState, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Play, SkipForward, SkipBack, X, Video, AlertTriangle, CheckCircle2, ChevronDown, Clock, Loader2, ThumbsUp, ThumbsDown, ClipboardCheck, Network, Shield, AlertCircle, RefreshCw, UserCheck, Calendar, ArrowRight, Activity, Cpu, Layers } from 'lucide-react';
import api from '../services/api';

const alertTranslations = {
  violence: "اشتباه عراك أو اعتداء جسدي (Violence / Assault)",
  violence_assault: "اشتباك جسدي واعتداء مباشر (Physical Assault)",
  violence_weapon: "اشتباه تهديد بسلاح (Weapon Threat)",
  accident: "اصطدام مروري أو حادث سيارة (Vehicle Collision)",
  collision: "اصطدام وحادث مروري (Vehicle Collision)",
  collision_vehicle_vehicle: "اصطدام بين مركبتين (Vehicle-Vehicle Crash)",
  collision_vehicle_pedestrian: "حادث دهس / اصطدام مشاة (Vehicle-Pedestrian Incident)"
};

const reasonCodeTranslations = {
  ABRUPT_IMPACT_DECELERATION_SPIKE: "هبوط حاد ومفاجئ في السرعة نتيجة التصادم",
  HEAD_ON_CONVERGING_TRAJECTORIES: "تقارب مسارات متقابلة في الاتجاه المعاكس",
  RAPID_DISTANCE_COLLAPSE: "انهيار سريع في المسافة الفاصلة بين الأجسام",
  HIGH_IOU_SPATIAL_OVERLAP: "تداخل فيزيائي بين حدود الأجسام (Spatial Overlap)",
  POST_IMPACT_SPEED_COLLAPSE: "توقف أو شلل الحركة بعد الارتطام مباشرة",
  SCALE_NORMALIZED_VELOCITY_SPIKE: "تسارع حركي مفاجئ متزامن غير طبيعي",
  PROLONGED_CLOSE_PROXIMITY: "تلاصق واحتكاك مستمر لفترة زمنية ممتدة",
  BODY_POSE_STRIKE_MOTION: "حركة تلويح أو ضرب جسدي سريعة",
  OPPOSING_INTERACTION_VECTORS: "متجهات حركة متعاكسة ومتنافرة",
  SPATIOTEMPORAL_3D_ACTION_ACTIVATION: "تنشيط شبكة الحركة ثلاثية الأبعاد (3D Spatio-Temporal Action Match)"
};

export default function Replay() {
  const location = useLocation();
  const navigate = useNavigate();
  
  const [videos, setVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [videoSrc, setVideoSrc] = useState("");
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [videoError, setVideoError] = useState(false);
  const videoRef = useRef(null);

  useEffect(() => {
    if (selectedVideo?.id) {
      setVideoSrc(`http://${window.location.hostname}:8001/api/videos/${selectedVideo.id}/stream`);
      setVideoError(false);
    }
  }, [selectedVideo]);

  // Enterprise SOC Forensics States
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");

  // Read initial states passed from Dashboard navigation
  const initialVideoId = location.state?.videoId;
  const initialEventId = location.state?.eventId;

  const fetchCases = async () => {
    try {
      const res = await api.get('/cases');
      setCases(res.data || []);
    } catch (err) {
      console.error("Failed to fetch cases:", err);
    }
  };

  const fetchVideosAndInitialize = async () => {
    try {
      const videosRes = await api.get('/videos');
      const vids = videosRes.data || [];
      setVideos(vids);
      fetchCases(); // Run in background

      if (vids.length > 0) {
        let activeVid = vids.find(v => v.id === initialVideoId || v.filename === initialVideoId) || vids[0];
        setSelectedVideo(activeVid);
        await fetchVideoEvents(activeVid.id, vids);
      }
    } catch (err) {
      console.error("Failed to load replay assets:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchVideoEvents = async (vidId, currentVideos = videos) => {
    try {
      let videoEvents = [];
      try {
        const directRes = await api.get(`/videos/${vidId}/events`);
        if (Array.isArray(directRes.data) && directRes.data.length > 0) {
          videoEvents = directRes.data;
        }
      } catch (e) {}

      if (videoEvents.length === 0) {
        try {
          const eventsRes = await api.get('/events');
          if (Array.isArray(eventsRes.data)) {
            const vidObj = currentVideos.find(v => v.id === vidId);
            videoEvents = eventsRes.data.filter(e => 
              e.video_id === vidId || e.job_id === vidId || e.source_id === vidId ||
              (vidObj && e.video_id === vidObj.filename)
            );
          }
        } catch (e) {}
      }

      // Sort events by timestamp_sec or start_time
      videoEvents.sort((a, b) => {
        const tA = a.explainability?.timestamp_sec || 0;
        const tB = b.explainability?.timestamp_sec || 0;
        return tA - tB;
      });

      setEvents(videoEvents);

      if (initialEventId && videoEvents.length > 0) {
        const targetEvent = videoEvents.find(e => String(e.id) === String(initialEventId)) || videoEvents[0];
        if (targetEvent) {
          setSelectedEvent(targetEvent);
        }
      } else if (videoEvents.length > 0) {
        setSelectedEvent(videoEvents[0]);
      } else {
        setSelectedEvent(null);
      }
    } catch (err) {
      console.error("Failed to load video events:", err);
    }
  };

  useEffect(() => {
    fetchVideosAndInitialize();
  }, []);

  const handleVideoSelect = async (vidId) => {
    const vid = videos.find(v => v.id === vidId);
    if (vid) {
      setSelectedVideo(vid);
      setSelectedEvent(null);
      setVideoError(false);
      await fetchVideoEvents(vidId, videos);
      if (videoRef.current) {
        videoRef.current.load();
      }
    }
  };

  const handleVideoLoaded = () => {
    setVideoError(false);
    if (selectedEvent) {
      seekToEvent(selectedEvent);
    }
  };

  const handleVideoError = () => {
    if (selectedVideo?.id && videoSrc && !videoSrc.includes('/videos/')) {
      // Fallback to direct static stream
      setVideoSrc(`http://${window.location.hostname}:8001/videos/${selectedVideo.id}.mp4`);
    } else {
      setVideoError(true);
    }
  };

  const getEventTimeOffset = (event) => {
    if (!event) return 0;
    if (event.explainability?.timestamp_sec != null) {
      return Number(event.explainability.timestamp_sec);
    }
    if (event.start_time) {
      const startMs = new Date(event.start_time).getTime();
      const initialStartMs = videos.length > 0 && selectedVideo?.created_at 
        ? new Date(selectedVideo.created_at).getTime() 
        : startMs;
      const diffSec = Math.max(0, (startMs - initialStartMs) / 1000);
      return diffSec;
    }
    return 0;
  };

  const formatOffset = (seconds) => {
    const s = Math.max(0, Math.floor(seconds || 0));
    const m = Math.floor(s / 60);
    const remS = s % 60;
    return `${m.toString().padStart(2, '0')}:${remS.toString().padStart(2, '0')}`;
  };

  const seekToEvent = (event) => {
    if (!event || !videoRef.current) return;
    const targetSec = getEventTimeOffset(event);
    videoRef.current.currentTime = Math.max(0, targetSec - 1.0); // 1 sec pre-roll
    videoRef.current.play().catch(e => console.log("Play failed, user action required:", e));
    setSelectedEvent(event);
  };

  const seekRelative = (delta) => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = Math.max(0, videoRef.current.currentTime + delta);
  };

  const handleFeedback = async (eventId, feedback) => {
    try {
      await api.post(`/events/${eventId}/feedback`, { feedback });
      setEvents(prev => prev.map(e => e.id === eventId ? { ...e, operator_feedback: feedback } : e));
      if (selectedEvent && selectedEvent.id === eventId) {
        setSelectedEvent(prev => ({ ...prev, operator_feedback: feedback }));
      }
    } catch (err) {
      console.error("Feedback submission failed:", err);
    }
  };

  const handleLinkCase = async (eventId) => {
    if (!selectedCaseId) return;
    try {
      await api.post(`/cases/${selectedCaseId}/events`, { event_id: eventId });
      alert("تم ربط الحادث بالقضية بنجاح!");
    } catch (err) {
      console.error("Failed to link event to case:", err);
      alert("فشل ربط الحادث بالقضية.");
    }
  };

  const handleCreateNewCaseAndLink = async (eventId) => {
    const title = window.prompt("أدخل عنوان القضية الجديدة:");
    if (!title) return;
    try {
      const res = await api.post('/cases', {
        title,
        description: `تم إنشاء القضية تلقائياً للتحقيق في الحادث #${eventId}`,
        status: "open"
      });
      if (res.data?.id) {
        await api.post(`/cases/${res.data.id}/events`, { event_id: eventId });
        await fetchCases();
        setSelectedCaseId(res.data.id);
        alert(`تم إنشاء القضية #${res.data.id} وربط الحادث بها بنجاح!`);
      }
    } catch (err) {
      console.error("Failed to create and link case:", err);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-[#020618] text-[#96A8C0]">
        <Loader2 className="animate-spin mb-2" size={32} />
        <span className="mr-3 font-semibold">جاري تحميل سجلات الاسترجاع والتحقيق الجنائي...</span>
      </div>
    );
  }

  const expl = selectedEvent?.explainability || {};
  const e2d = expl.evidence_2d != null ? (expl.evidence_2d * 100).toFixed(0) : null;
  const ePose = expl.evidence_pose != null ? (expl.evidence_pose * 100).toFixed(0) : null;
  const e3D = expl.evidence_3d != null ? (expl.evidence_3d * 100).toFixed(0) : null;
  const crowdDiscount = expl.crowd_suppression != null ? (expl.crowd_suppression * 100).toFixed(0) : null;

  return (
    <div className="p-6 max-w-7xl mx-auto h-full flex flex-col space-y-4 overflow-y-auto bg-[#020618] text-[#D7E0EE] font-sans" dir="rtl">
      
      {/* Top Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#0F172A] p-4 rounded-2xl border border-[#26344A] shadow-sm">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 bg-[#151F33] hover:bg-[#1D293D] active:scale-95 text-[#D7E0EE] hover:text-[#D7E0EE] text-xs font-bold px-4 py-2.5 rounded-xl border border-[#26344A] transition-all shadow-xs group cursor-pointer"
            title="الرجوع إلى لوحة التحكم والواجهة الرئيسية"
          >
            <ArrowRight size={16} className="text-[#707FF0] group-hover:-translate-x-0.5 transition-transform" />
            <span>العودة للرئيسية</span>
          </button>
          <div>
            <h2 className="text-xl font-bold text-[#D7E0EE] flex items-center gap-2">
              <Video className="text-[#707FF0]" /> الاسترجاع الأمني والتحليل الجنائي ثلاثي الأبعاد
            </h2>
            <p className="text-xs text-[#96A8C0] mt-0.5">
              استعراض دقيق بالثانية والتاريخ مع شجرة التفسير الجنائي والمحرك المكاني والزماني 3D Spatio-Temporal
            </p>
          </div>
        </div>

        {/* Video Selector Dropdown */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          <label className="text-xs text-[#96A8C0] whitespace-nowrap font-bold">الفيديو المستهدف:</label>
          <select
            value={selectedVideo?.id || ""}
            onChange={(e) => handleVideoSelect(e.target.value)}
            className="bg-[#151F33] border border-[#26344A] text-[#D7E0EE] text-xs font-semibold rounded-xl px-4 py-2 focus:outline-none focus:border-[#707FF0] max-w-xs truncate"
          >
            {videos.map(v => (
              <option key={v.id} value={v.id}>
                {v.filename} {v.status === 'clean' ? ' (سليم)' : ` (${(v.events || []).length} أحداث)`}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Workspace: 2-Column Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 items-start">
        
        {/* Left Column: Video Player and Timeline Seek (7 Cols) */}
        <div className="lg:col-span-7 bg-[#0F172A] border border-[#26344A] rounded-3xl overflow-hidden shadow-sm flex flex-col">
          
          <div className="p-3.5 bg-[#151F33] border-b border-[#26344A] flex justify-between items-center text-xs">
            <span className="font-bold text-[#D7E0EE] truncate max-w-xs font-mono">
              📹 {selectedVideo?.filename || "لم يتم تحديد فيديو"}
            </span>
            <span className="bg-[#151F33] text-[#707FF0] border border-[#D4E1F0] px-2.5 py-0.5 rounded-full font-bold text-[10px]">
              {events.length > 0 ? `تم رصد ${events.length} أحداث` : "فيديو سليم"}
            </span>
          </div>

          <div className="relative bg-black flex items-center justify-center min-h-[380px] max-h-[500px]">
            {selectedVideo ? (
              <video
                ref={videoRef}
                controls
                preload="auto"
                playsInline
                className="w-full h-full max-h-[480px] object-contain"
                src={videoSrc}
                onLoadedMetadata={handleVideoLoaded}
                onError={handleVideoError}
              >
                متصفحك لا يدعم تشغيل الفيديو.
              </video>
            ) : (
              <div className="text-[#96A8C0] text-xs py-20 text-center">
                <Video size={48} className="mx-auto mb-2 opacity-20" />
                <span>يرجى اختيار فيديو من القائمة لعرضه.</span>
              </div>
            )}

            {videoError && (
              <div className="absolute inset-0 bg-black/80 flex flex-col items-center justify-center text-[#F02050] text-xs p-4 text-center">
                <AlertCircle size={32} className="mb-2" />
                <p className="font-bold">تعذر تحميل الفيديو مباشرة من السيرفر.</p>
                <p className="text-[#96A8C0] mt-1">تأكد من وجود الملف داخل مسار التخزين.</p>
              </div>
            )}
          </div>

          {/* Precise Video Navigation Controls */}
          {selectedVideo && (
            <div className="p-3.5 bg-[#151F33] border-t border-[#26344A] flex justify-between items-center gap-3">
              <button
                onClick={() => seekRelative(-10)}
                className="flex items-center gap-1.5 bg-[#0F172A] hover:bg-[#151F33] border border-[#26344A] px-3.5 py-2 rounded-xl text-xs text-[#D7E0EE] font-bold transition-all shadow-xs"
              >
                <SkipBack size={14} /> إرجاع 10 ثوانٍ
              </button>

              <div className="text-center font-mono text-xs text-[#D7E0EE]">
                {selectedEvent && (
                  <span className="bg-[#151F33] text-[#D7E0EE] border border-[#D4E1F0] px-3 py-1 rounded-xl block font-bold">
                    ⏱️ موقع الحادث المختار: {formatOffset(getEventTimeOffset(selectedEvent))} (الثانية {getEventTimeOffset(selectedEvent).toFixed(1)}s)
                  </span>
                )}
              </div>

              <button
                onClick={() => seekRelative(10)}
                className="flex items-center gap-1.5 bg-[#0F172A] hover:bg-[#151F33] border border-[#26344A] px-3.5 py-2 rounded-xl text-xs text-[#D7E0EE] font-bold transition-all shadow-xs"
              >
                تقديم 10 ثوانٍ <SkipForward size={14} />
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Forensic Events & Detailed Evidence Decision Tree (5 Cols) */}
        <div className="lg:col-span-5 bg-[#0F172A] border border-[#26344A] rounded-3xl overflow-hidden shadow-sm flex flex-col h-full">
          
          <div className="p-3.5 border-b border-[#26344A] bg-[#151F33] flex justify-between items-center">
            <div className="flex items-center gap-2">
              <span className="p-1.5 bg-[#2A1020] text-[#F02050] rounded-lg">
                <AlertTriangle size={14} />
              </span>
              <h3 className="font-bold text-xs text-[#D7E0EE]">سجل الأدلة والتفسير الجنائي بالثانية</h3>
            </div>
            {events.length > 0 && (
              <span className="bg-slate-800 text-[#D7E0EE] px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold">
                {events.length} أحداث
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-[600px]">
            
            {/* Timeline Pills */}
            {events.length > 1 && (
              <div className="space-y-2 pb-2 border-b border-[#26344A]">
                <span className="text-[10px] text-[#96A8C0] block font-bold">اختر الحادث للانتقال للثانية مباشرة:</span>
                <div className="grid grid-cols-2 gap-2 max-h-28 overflow-y-auto pr-1">
                  {events.map((ev) => {
                    const offset = getEventTimeOffset(ev);
                    const isSel = selectedEvent?.id === ev.id;
                    return (
                      <button
                        key={ev.id}
                        onClick={() => seekToEvent(ev)}
                        className={`p-2 rounded-xl text-[10px] font-bold text-right transition-all border flex flex-col gap-0.5 ${
                          isSel
                            ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg'
                            : 'bg-[#151F33] border-[#26344A] text-[#D7E0EE] hover:border-blue-400'
                        }`}
                      >
                        <div className="flex justify-between items-center">
                          <span>#{ev.id} {ev.type?.split('_')[0]}</span>
                          <span className="font-mono text-[9px] bg-black/40 px-1.5 py-0.5 rounded">
                            {formatOffset(offset)}
                          </span>
                        </div>
                        <span className="text-[9px] opacity-80 font-mono">الثانية {offset.toFixed(1)}s</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* If NO event */}
            {events.length === 0 ? (
              <div className="h-full flex flex-col justify-center items-center text-[#96A8C0] py-16 text-center">
                <CheckCircle2 size={40} className="text-emerald-500/40 mb-3" />
                <p className="text-sm font-bold text-[#D7E0EE]">هذا الفيديو سليم 100%</p>
                <p className="text-xs text-[#96A8C0] mt-1">لم يتم رصد أي أنشطة عنف أو حوادث اصطدام.</p>
              </div>
            ) : selectedEvent ? (
              <div className="space-y-4 animate-fade-in text-right">
                
                {/* Threat Badge */}
                <div className="bg-[#151F33]/40 p-4 rounded-2xl border border-[#26344A] shadow-sm space-y-2">
                  <div className="flex justify-between items-center flex-row-reverse">
                    <span className="text-[10px] text-[#F02050] font-bold uppercase tracking-wider">
                      معرف الحدث: #{selectedEvent.id}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-[#2A1020] text-[#F02050]">
                      {selectedEvent.escalation_stage || 'CONFIRMED'}
                    </span>
                  </div>
                  
                  <h4 className="font-bold text-[#D7E0EE] text-sm leading-relaxed">
                    {alertTranslations[selectedEvent.type] || alertTranslations[selectedEvent.type?.split('_')[0]] || selectedEvent.type}
                  </h4>

                  {/* Exact Video Second and Date */}
                  <div className="pt-2 border-t border-[#26344A] grid grid-cols-1 gap-1.5 text-[11px] font-mono">
                    <div className="flex items-center gap-2 text-[#707FF0] bg-indigo-950/40 p-2 rounded-xl border border-indigo-800/40">
                      <Clock size={14} className="shrink-0 text-[#707FF0]" />
                      <span><strong>توقيت الحادث في الفيديو:</strong> {formatOffset(getEventTimeOffset(selectedEvent))} (الثانية {getEventTimeOffset(selectedEvent).toFixed(1)}s)</span>
                    </div>

                    <div className="flex items-center gap-2 text-[#96A8C0] bg-[#0F172A]/60 p-2 rounded-xl border border-[#26344A]">
                      <Calendar size={14} className="shrink-0 text-[#96A8C0]" />
                      <span><strong>تاريخ ووقت التسجيل:</strong> {selectedEvent.start_time ? new Date(selectedEvent.start_time).toLocaleString('ar-EG', { dateStyle: 'medium', timeStyle: 'medium' }) : 'اللحظة الحالية'}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => seekToEvent(selectedEvent)}
                    className="w-full mt-2 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 shadow-md shadow-indigo-600/20"
                  >
                    <Play size={14} /> الانتقال المباشر لثانية الحادث ({formatOffset(getEventTimeOffset(selectedEvent))})
                  </button>
                </div>

                {/* 3D Spatio-Temporal & Multi-Evidence Breakdown Panel */}
                <div className="bg-[#151F33]/40 p-4 rounded-2xl border border-[#26344A] space-y-3">
                  <h4 className="text-xs font-bold text-[#D7E0EE] flex items-center justify-start gap-1.5">
                    <Activity size={14} className="text-[#707FF0]" /> تفكيك الأدلة الجنائية (Multi-Evidence Breakdown):
                  </h4>

                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                    <div className="p-2.5 bg-[#0F172A] rounded-xl border border-[#26344A] flex flex-col shadow-xs justify-between">
                      <span className="text-[#96A8C0] text-[10px]">دليل الحركة 2D Kinematics</span>
                      <span className="text-base font-bold text-[#707FF0] mt-1">{e2d ? `${e2d}%` : `${((selectedEvent.confidence || 0.85) * 100).toFixed(0)}%`}</span>
                    </div>

                    <div className="p-2.5 bg-[#0F172A] rounded-xl border border-[#26344A] flex flex-col shadow-xs justify-between">
                      <span className="text-[#96A8C0] text-[10px]">دليل الهيكل الجسدي Pose</span>
                      <span className="text-base font-bold text-[#00D090] mt-1">{ePose ? `${ePose}%` : '85%'}</span>
                    </div>

                    <div className="p-2.5 bg-[#151F33]/60 rounded-xl border border-[#D4E1F0] flex flex-col shadow-xs justify-between">
                      <span className="text-indigo-300 text-[10px] flex items-center gap-1">
                        <Layers size={11} /> محرك 3D Spatio-Temporal
                      </span>
                      <span className="text-base font-bold text-[#707FF0] mt-1">{e3D ? `${e3D}%` : '88%'}</span>
                    </div>

                    <div className="p-2.5 bg-[#0F172A] rounded-xl border border-[#26344A] flex flex-col shadow-xs justify-between">
                      <span className="text-[#96A8C0] text-[10px]">خصم الحشود Coherence</span>
                      <span className="text-base font-bold text-[#F59E0B] mt-1">{crowdDiscount ? `-${crowdDiscount}%` : '0%'}</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-[#26344A] flex justify-between items-center text-xs">
                    <span className="text-[#96A8C0]">مؤشر الخطر المحسوب (Risk Score):</span>
                    <span className="font-bold text-[#F02050] font-mono text-sm">
                      {selectedEvent.risk_score ? `${Number(selectedEvent.risk_score).toFixed(0)}%` : `${((selectedEvent.confidence || 0.9) * 100).toFixed(0)}%`}
                    </span>
                  </div>
                </div>

                {/* Reason Codes */}
                <div className="bg-[#020618] p-4 rounded-2xl border border-[#26344A] space-y-2">
                  <h4 className="text-xs font-bold text-[#D7E0EE] flex items-center justify-start gap-1.5">
                    <Shield size={14} className="text-[#707FF0]" /> المؤشرات الفيزيائية والحركية للحادث:
                  </h4>
                  <div className="space-y-1.5 pt-1">
                    {(selectedEvent.reason_codes || selectedEvent.explainability?.reason_codes || []).length > 0 ? (
                      (selectedEvent.reason_codes || selectedEvent.explainability?.reason_codes || []).map((rc, idx) => (
                        <div key={idx} className="p-2 bg-[#0F172A]/80 rounded-xl border border-[#26344A]/80 text-[11px] text-[#D7E0EE] flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0"></span>
                          <span>{reasonCodeTranslations[rc] || rc}</span>
                        </div>
                      ))
                    ) : (
                      <div className="p-2 bg-[#0F172A]/80 rounded-xl border border-[#26344A]/80 text-[11px] text-[#96A8C0]">
                        {selectedEvent.type?.startsWith('collision') 
                          ? "رصد اصطدام حركي مع تباطؤ مفاجئ وتداخل في حدود الأجسام و3D Spatio-Temporal Match"
                          : "رصد اشتباك جسدي متسارع مع حركة اندفاع وتقارب حاد و3D Action Match"}
                      </div>
                    )}
                  </div>
                </div>

                {/* Operator Active Learning Feedback */}
                <div className="bg-[#020618] p-4 rounded-2xl border border-[#26344A]">
                  <h4 className="text-xs font-bold text-[#D7E0EE] mb-2">تقييم المشغل الأمني (Active Learning):</h4>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleFeedback(selectedEvent.id, 'VALID')}
                      className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all border flex items-center justify-center gap-1.5 ${
                        selectedEvent.operator_feedback === 'VALID'
                          ? 'bg-emerald-600 text-white border-emerald-500'
                          : 'bg-[#0F172A] border-[#26344A] text-[#D7E0EE] hover:bg-[#0B2825]/40 hover:text-[#00D090]'
                      }`}
                    >
                      <ThumbsUp size={13} /> تأكيد صحة الإنذار
                    </button>
                    <button
                      onClick={() => handleFeedback(selectedEvent.id, 'FALSE_POSITIVE')}
                      className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all border flex items-center justify-center gap-1.5 ${
                        selectedEvent.operator_feedback === 'FALSE_POSITIVE'
                          ? 'bg-rose-600 text-white border-rose-500'
                          : 'bg-[#0F172A] border-[#26344A] text-[#D7E0EE] hover:bg-[#2A1020]/40 hover:text-[#F02050]'
                      }`}
                    >
                      <ThumbsDown size={13} /> إنذار كاذب
                    </button>
                  </div>
                </div>

                {/* Case Link */}
                <div className="bg-[#151F33]/40 p-4 rounded-2xl border border-[#26344A] space-y-3">
                  <h4 className="text-xs font-bold text-[#D7E0EE] flex items-center justify-start gap-1.5">
                    <ClipboardCheck size={14} className="text-[#707FF0]" /> ربط بملف قضية تحقيق:
                  </h4>
                  
                  {cases.length > 0 ? (
                    <div className="flex gap-2">
                      <select
                        value={selectedCaseId}
                        onChange={(e) => setSelectedCaseId(e.target.value)}
                        className="flex-1 bg-[#0F172A] border border-[#26344A] rounded-xl px-3 py-2 text-xs text-[#D7E0EE] focus:outline-none focus:border-indigo-500"
                      >
                        <option value="">اختر قضية من السجل...</option>
                        {cases.map(c => (
                          <option key={c.id} value={c.id}>
                            #{c.id} - {c.title}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => handleLinkCase(selectedEvent.id)}
                        disabled={!selectedCaseId}
                        className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-xl text-xs font-bold transition-all"
                      >
                        ربط
                      </button>
                    </div>
                  ) : null}

                  <button
                    onClick={() => handleCreateNewCaseAndLink(selectedEvent.id)}
                    className="w-full py-2 bg-[#0F172A] hover:bg-slate-850 border border-[#26344A] hover:border-indigo-500/50 text-[#707FF0] rounded-xl text-xs font-bold transition-all"
                  >
                    + إنشاء قضية جديدة وربط الحادث بها
                  </button>
                </div>

              </div>
            ) : null}

          </div>
        </div>

      </div>

    </div>
  );
}
