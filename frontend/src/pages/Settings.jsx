import React, { useState, useEffect } from 'react';
import { Settings, Shield, Sliders, Cpu, Save, CheckCircle, Plus, Trash2, Video, Camera, Radio, Server, Activity, Car, Zap } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import api from '../services/api';

export default function SettingsPage() {
  const { lang, dir, t } = useLanguage();
  const [success, setSuccess] = useState(false);
  
  // Violence Settings
  const [violenceProx, setViolenceProx] = useState(350);
  const [violenceVel, setViolenceVel] = useState(6);
  const [violenceDur, setViolenceDur] = useState(2);
  const [violenceCooldown, setViolenceCooldown] = useState(15);
  
  // Collision Settings
  const [accidentDecel, setAccidentDecel] = useState(10);
  const [accidentIou, setAccidentIou] = useState(0.08);
  const [accidentProx, setAccidentProx] = useState(120);
  
  // 3D Spatio-Temporal Intelligence Settings
  const [enable3d, setEnable3d] = useState(true);
  const [temporalFrames, setTemporalFrames] = useState(16);
  const [selectedModel, setSelectedModel] = useState("yolov8n.pt");
  const [isLoaded, setIsLoaded] = useState(false);

  // RTSP / Mobile / IP Cameras Management State
  const [cameras, setCameras] = useState([]);
  const [newCamName, setNewCamName] = useState("");
  const [newCamUrl, setNewCamUrl] = useState("");
  const [newCamType, setNewCamType] = useState("mjpeg");
  const [newCamScene, setNewCamScene] = useState("Mall");
  const [newCamSensitivity, setNewCamSensitivity] = useState("Medium");
  const [newCamReplayLength, setNewCamReplayLength] = useState(15);
  const [isAddingCam, setIsAddingCam] = useState(false);

  const fetchConfig = async () => {
    try {
      const rulesRes = await api.get('/rules');
      const rulesMap = {};
      rulesRes.data.forEach(r => {
        rulesMap[r.key] = r.value;
      });

      if (rulesMap['violence_proximity_thresh']) setViolenceProx(Number(rulesMap['violence_proximity_thresh']));
      if (rulesMap['violence_velocity_thresh']) setViolenceVel(Number(rulesMap['violence_velocity_thresh']));
      if (rulesMap['violence_duration_thresh']) setViolenceDur(Number(rulesMap['violence_duration_thresh']));
      if (rulesMap['violence_cooldown_sec']) setViolenceCooldown(Number(rulesMap['violence_cooldown_sec']));
      if (rulesMap['accident_decel_thresh']) setAccidentDecel(Number(rulesMap['accident_decel_thresh']));
      if (rulesMap['accident_iou_thresh']) setAccidentIou(Number(rulesMap['accident_iou_thresh']));
      if (rulesMap['accident_proximity_thresh']) setAccidentProx(Number(rulesMap['accident_proximity_thresh']));
      if (rulesMap['spatiotemporal_3d_enabled']) setEnable3d(rulesMap['spatiotemporal_3d_enabled'] === 'true');
      if (rulesMap['active_ai_model']) setSelectedModel(rulesMap['active_ai_model']);
      
      setIsLoaded(true);
    } catch (err) {
      console.error("Failed to load rules thresholds:", err);
    }

    try {
      const camsRes = await api.get('/cameras');
      setCameras(camsRes.data || []);
    } catch (err) {
      console.error("Failed to fetch cameras:", err);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  useEffect(() => {
    if (!isLoaded) return;
    const delayDebounceFn = setTimeout(async () => {
      try {
        const rules = [
          { key: "violence_proximity_thresh", value: String(violenceProx) },
          { key: "violence_velocity_thresh", value: String(violenceVel) },
          { key: "violence_duration_thresh", value: String(violenceDur) },
          { key: "violence_cooldown_sec", value: String(violenceCooldown) },
          { key: "accident_decel_thresh", value: String(accidentDecel) },
          { key: "accident_iou_thresh", value: String(accidentIou) },
          { key: "accident_proximity_thresh", value: String(accidentProx) },
          { key: "spatiotemporal_3d_enabled", value: String(enable3d) },
          { key: "active_ai_model", value: selectedModel }
        ];

        for (const rule of rules) {
          await api.post('/rules', rule);
        }
        setSuccess(true);
        setTimeout(() => setSuccess(false), 2000);
      } catch (err) {
        console.error("Auto-save failed:", err);
      }
    }, 800);

    return () => clearTimeout(delayDebounceFn);
  }, [violenceProx, violenceVel, violenceDur, violenceCooldown, accidentDecel, accidentIou, accidentProx, enable3d, selectedModel]);

  const handleAddCamera = async (e) => {
    e.preventDefault();
    if (!newCamUrl || !newCamUrl.trim()) return;

    try {
      const res = await api.post('/cameras', {
        name: newCamName?.trim() || undefined,
        stream_url: newCamUrl.trim(),
        model_profile: selectedModel || "yolov8n.pt",
        rules_enabled: ["violence", "collision"]
      });

      setCameras([...cameras, res.data]);
      setNewCamName("");
      setNewCamUrl("");
      setIsAddingCam(false);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2500);
    } catch (err) {
      console.error("Failed to add camera:", err);
      alert(err.response?.data?.detail || "فشل إضافة الكاميرا، يرجى التأكد من الرابط");
    }
  };

  const handleDeleteCamera = async (id) => {
    if (!window.confirm(lang === "ar" ? "هل أنت متأكد من حذف هذه الكاميرا؟" : "Delete this camera stream?")) return;
    try {
      await api.delete(`/cameras/${id}`);
      setCameras(cameras.filter(c => c.id !== id));
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2500);
    } catch (err) {
      console.error("Failed to delete camera:", err);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6 text-[#D7E0EE]" dir={dir}>
      {/* Header */}
      <div className="flex justify-between items-center bg-[#0F172A] p-4 rounded-2xl border border-[#26344A] shadow-sm">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Settings className="text-[#707FF0]" />
            <span>{lang === "ar" ? "إعدادات منصة الذكاء الاصطناعي رَصْد AI (RASD AI)" : "RASD AI Platform Settings (رَصْد AI)"}</span>
          </h2>
          <p className="text-[#96A8C0] text-xs mt-1">
            {lang === "ar" ? "التحكم في عتبات كشف العنف والحوادث، والاستدلال المكاني الزمني 3D" : "Configure Violence, Collision Thresholds and 3D Spatio-Temporal Intelligence"}
          </p>
        </div>

        {success && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0B2825] border border-emerald-500/30 text-[#00D090] rounded-xl text-xs font-semibold animate-pulse">
            <CheckCircle size={14} />
            <span>{lang === "ar" ? "تم الحفظ تلقائياً" : "Auto-Saved"}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Violence Detection Rules */}
        <div className="bg-[#0F172A] p-5 rounded-2xl border border-[#26344A] shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-[#F02050] font-semibold text-sm border-b border-[#26344A]/60 pb-3">
            <Shield size={18} />
            <span>{lang === "ar" ? "عتبات كشف العنف والاشتباك (Violence Domain)" : "Violence Detection Thresholds"}</span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <div className="flex justify-between text-[#D7E0EE] mb-1">
                <span>{lang === "ar" ? "عتبة التقارب الفراغي (بكسل)" : "Proximity Threshold (px)"}</span>
                <span className="font-mono text-[#F02050]">{violenceProx} px</span>
              </div>
              <input 
                type="range" min="100" max="600" step="10"
                value={violenceProx} onChange={e => setViolenceProx(Number(e.target.value))}
                className="w-full accent-rose-500 bg-[#151F33] rounded-lg h-1.5"
              />
            </div>

            <div>
              <div className="flex justify-between text-[#D7E0EE] mb-1">
                <span>{lang === "ar" ? "عتبة تصادم التسارع الحركي (a/h)" : "Kinematic Acceleration Clash"}</span>
                <span className="font-mono text-[#F02050]">{violenceVel} v/h</span>
              </div>
              <input 
                type="range" min="2" max="15" step="0.5"
                value={violenceVel} onChange={e => setViolenceVel(Number(e.target.value))}
                className="w-full accent-rose-500 bg-[#151F33] rounded-lg h-1.5"
              />
            </div>

            <div>
              <div className="flex justify-between text-[#D7E0EE] mb-1">
                <span>{lang === "ar" ? "مدة الثبات الزمني (فريمات)" : "Temporal Persistence (frames)"}</span>
                <span className="font-mono text-[#F02050]">{violenceDur} {lang === "ar" ? "فريم" : "frames"}</span>
              </div>
              <input 
                type="range" min="1" max="10" step="1"
                value={violenceDur} onChange={e => setViolenceDur(Number(e.target.value))}
                className="w-full accent-rose-500 bg-[#151F33] rounded-lg h-1.5"
              />
            </div>
          </div>
        </div>

        {/* Collision & Accident Rules */}
        <div className="bg-[#0F172A] p-5 rounded-2xl border border-[#26344A] shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-[#F59E0B] font-semibold text-sm border-b border-[#26344A]/60 pb-3">
            <Car size={18} />
            <span>{lang === "ar" ? "عتبات كشف الحوادث والاصطدامات (Collision Domain)" : "Collision & Accident Thresholds"}</span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <div className="flex justify-between text-[#D7E0EE] mb-1">
                <span>{lang === "ar" ? "عتبة تباطؤ الصدمة المفاجئ" : "Deceleration Spike Threshold"}</span>
                <span className="font-mono text-[#F59E0B]">{accidentDecel} px/s²</span>
              </div>
              <input 
                type="range" min="3" max="30" step="1"
                value={accidentDecel} onChange={e => setAccidentDecel(Number(e.target.value))}
                className="w-full accent-amber-500 bg-[#151F33] rounded-lg h-1.5"
              />
            </div>

            <div>
              <div className="flex justify-between text-[#D7E0EE] mb-1">
                <span>{lang === "ar" ? "عتبة تداخل الصناديق (IoU Overlap)" : "Bounding Box IoU Overlap"}</span>
                <span className="font-mono text-[#F59E0B]">{accidentIou}</span>
              </div>
              <input 
                type="range" min="0.02" max="0.5" step="0.01"
                value={accidentIou} onChange={e => setAccidentIou(Number(e.target.value))}
                className="w-full accent-amber-500 bg-[#151F33] rounded-lg h-1.5"
              />
            </div>

            <div>
              <div className="flex justify-between text-[#D7E0EE] mb-1">
                <span>{lang === "ar" ? "عتبة تقارب المشاة والمركبات" : "Pedestrian-Vehicle Proximity"}</span>
                <span className="font-mono text-[#F59E0B]">{accidentProx} px</span>
              </div>
              <input 
                type="range" min="50" max="300" step="10"
                value={accidentProx} onChange={e => setAccidentProx(Number(e.target.value))}
                className="w-full accent-amber-500 bg-[#151F33] rounded-lg h-1.5"
              />
            </div>
          </div>
        </div>

        {/* 3D Spatio-Temporal Intelligence Configuration */}
        <div className="bg-[#0F172A] p-5 rounded-2xl border border-[#26344A] shadow-sm space-y-4 md:col-span-2">
          <div className="flex items-center justify-between border-b border-[#26344A]/60 pb-3">
            <div className="flex items-center gap-2 text-[#707FF0] font-semibold text-sm">
              <Zap size={18} />
              <span>{lang === "ar" ? "محرك الاستدلال المكاني الزمني 3D (Local 3D Spatio-Temporal)" : "Local 3D Spatio-Temporal Intelligence"}</span>
            </div>
            <span className="text-xs bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 px-2.5 py-1 rounded-lg">
              100% Local GPU / CPU
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="bg-[#151F33] p-3.5 rounded-xl border border-[#26344A]">
              <label className="block text-[#D7E0EE] font-medium mb-1.5">
                {lang === "ar" ? "تفعيل التحقق الزمني 3D" : "Enable 3D Action Verification"}
              </label>
              <button 
                onClick={() => setEnable3d(!enable3d)}
                className={`w-full py-2 rounded-lg font-semibold transition-all ${
                  enable3d ? 'bg-[#707FF0] text-white' : 'bg-[#151F33] text-[#96A8C0]'
                }`}
              >
                {enable3d ? (lang === "ar" ? "مفعل (Active)" : "Active") : (lang === "ar" ? "معطل (Disabled)" : "Disabled")}
              </button>
            </div>

            <div className="bg-[#151F33] p-3.5 rounded-xl border border-[#26344A]">
              <label className="block text-[#D7E0EE] font-medium mb-1.5">
                {lang === "ar" ? "طول النافذة الزمنية (Temporal Window)" : "Temporal Window Size"}
              </label>
              <div className="text-[#707FF0] font-mono font-bold text-base py-1">
                16 {lang === "ar" ? "فريم (1.0 ثانية)" : "frames (1.0 sec)"}
              </div>
            </div>

            <div className="bg-[#151F33] p-3.5 rounded-xl border border-[#26344A]">
              <label className="block text-[#D7E0EE] font-medium mb-1.5">
                {lang === "ar" ? "نموذج الرصد الأساسي (YOLO Detector)" : "Base YOLO Detector Model"}
              </label>
              <select 
                value={selectedModel} 
                onChange={e => setSelectedModel(e.target.value)}
                className="w-full bg-[#0F172A] border border-[#26344A] rounded-lg p-2 text-[#D7E0EE] focus:border-[#707FF0]"
              >
                <option value="yolov8n.pt">yolov8n.pt (Indoor / High FPS)</option>
                <option value="yolov8m.pt">yolov8m.pt (Outdoor / High Accuracy)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Live Cameras & Stream Management */}
        <div className="bg-[#0F172A] p-5 rounded-2xl border border-[#26344A] shadow-sm space-y-4 md:col-span-2">
          <div className="flex justify-between items-center border-b border-[#26344A]/60 pb-3">
            <div className="flex items-center gap-2 text-cyan-400 font-semibold text-sm">
              <Camera size={18} />
              <span>{lang === "ar" ? "إدارة كاميرات المراقبة المباشرة (RTSP / Live Streams)" : "Live Cameras & RTSP Streams"}</span>
            </div>
            <button 
              onClick={() => setIsAddingCam(!isAddingCam)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-semibold transition-all shadow-md"
            >
              <Plus size={14} />
              <span>{lang === "ar" ? "إضافة كاميرا" : "Add Stream"}</span>
            </button>
          </div>

          {isAddingCam && (
            <form onSubmit={handleAddCamera} className="bg-[#020618] p-5 rounded-2xl border border-[#26344A] space-y-3.5 text-xs shadow-xl">
              <div>
                <label className="block text-[#D7E0EE] font-bold mb-1.5 flex items-center justify-between">
                  <span>{lang === "ar" ? "رابط البث أو عنوان الـ API للكاميرا *" : "Stream URL or Camera API Address *"}</span>
                  <span className="text-[11px] text-cyan-400 font-normal">
                    {lang === "ar" ? "يكفي إدخال الرابط فقط، ويتم ضبط البروتوكول والتهيئة تلقائياً" : "Enter URL only; system auto-configures protocol & stream"}
                  </span>
                </label>
                <div className="flex gap-2">
                  <input 
                    type="text" required 
                    placeholder="http://192.168.8.108:8080/video أو 0 أو rtsp://..."
                    value={newCamUrl} onChange={e => setNewCamUrl(e.target.value)}
                    className="flex-1 bg-[#0F172A] border border-[#26344A] focus:border-[#707FF0] rounded-xl p-2.5 text-[#D7E0EE] font-mono text-xs"
                    autoFocus
                  />
                  <button type="submit" className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl font-bold transition-all shadow-md shrink-0">
                    {lang === "ar" ? "إضافة وبدء البث" : "Add & Stream"}
                  </button>
                </div>
              </div>

              {/* Quick Preset Buttons */}
              <div className="flex items-center gap-2 pt-1 flex-wrap">
                <span className="text-[10px] text-[#96A8C0]">{lang === "ar" ? "خيارات سريعة:" : "Quick Presets:"}</span>
                <button
                  type="button"
                  onClick={() => { setNewCamUrl("0"); setNewCamName(lang === "ar" ? "كاميرا الجهاز المدمجة" : "Built-in Webcam"); }}
                  className="px-2.5 py-1 bg-[#0F172A] hover:bg-[#1D293D] border border-[#26344A] rounded-lg text-[10px] text-[#D7E0EE] transition-all font-mono"
                >
                  0 (كاميرا اللابتوب)
                </button>
                <button
                  type="button"
                  onClick={() => { setNewCamUrl("http://192.168.8.108:8080/video"); setNewCamName(lang === "ar" ? "كاميرا الهاتف الذكي" : "Smartphone Cam"); }}
                  className="px-2.5 py-1 bg-[#0F172A] hover:bg-[#1D293D] border border-[#26344A] rounded-lg text-[10px] text-[#D7E0EE] transition-all font-mono"
                >
                  IP Webcam (8080/video)
                </button>
                <button
                  type="button"
                  onClick={() => { setNewCamUrl("rtsp://192.168.1.100:554/live"); setNewCamName(lang === "ar" ? "كاميرا شبكية RTSP" : "RTSP Cam"); }}
                  className="px-2.5 py-1 bg-[#0F172A] hover:bg-[#1D293D] border border-[#26344A] rounded-lg text-[10px] text-[#D7E0EE] transition-all font-mono"
                >
                  RTSP Stream
                </button>
              </div>

              {/* Optional Name field collapsible/simple */}
              <div className="pt-2 border-t border-[#26344A]/80 flex items-center justify-between">
                <div className="flex-1 max-w-xs">
                  <label className="block text-[11px] text-[#96A8C0] mb-1">{lang === "ar" ? "اسم الكاميرا (اختياري - يولد تلقائياً)" : "Camera Name (Optional)"}</label>
                  <input 
                    type="text" 
                    placeholder={`كاميرا ${cameras.length + 1}`}
                    value={newCamName} onChange={e => setNewCamName(e.target.value)}
                    className="w-full bg-[#0F172A] border border-[#26344A] rounded-lg p-1.5 text-xs text-[#D7E0EE]"
                  />
                </div>
                <button type="button" onClick={() => setIsAddingCam(false)} className="px-3 py-1.5 bg-[#151F33] text-[#96A8C0] hover:text-[#D7E0EE] rounded-lg text-xs mt-3">
                  {lang === "ar" ? "إلغاء" : "Cancel"}
                </button>
              </div>
            </form>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {cameras.map(cam => (
              <div key={cam.id} className="flex justify-between items-center p-3 bg-[#020618]/60 rounded-xl border border-[#26344A] text-xs">
                <div>
                  <div className="font-semibold text-[#D7E0EE]">{cam.name}</div>
                  <div className="text-[#96A8C0] text-[11px] truncate max-w-xs">{cam.stream_url}</div>
                </div>
                <button 
                  onClick={() => handleDeleteCamera(cam.id)}
                  className="p-1.5 text-[#96A8C0] hover:text-[#F02050] hover:bg-[#2A1020]/30 rounded-lg transition-all"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
