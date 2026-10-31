import React, { useEffect, useState } from 'react';
import { Activity, ShieldAlert, Cpu, Database, HardDrive, RefreshCw, BarChart2 } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import api from '../services/api';

export default function HealthPage() {
  const { lang, dir, t } = useLanguage();
  const [metrics, setMetrics] = useState({
    cpu_usage: 0.0,
    ram_usage: 0.0,
    gpu_usage: 0.0,
    vram_usage: 0.0,
    fps: 25.0,
    latency_ms: 12.0,
    dropped_frames: 0,
    services: {
      backend: "checking",
      ai_worker: "checking",
      redis: "checking",
      postgresql: "checking"
    },
    docker_containers: []
  });
  const [loading, setLoading] = useState(true);

  const fetchHealthData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/health/system');
      setMetrics(response.data);
    } catch (err) {
      console.error("Failed to fetch system metrics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthData();
    const interval = setInterval(fetchHealthData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto h-full flex flex-col overflow-y-auto" dir={dir}>
      
      {/* Header */}
      <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-[#26344A] pb-5">
        <div className="flex items-center gap-3">
          {metrics.ai_device && (
            <div className="bg-[#0B2825] border border-emerald-500/30 text-[#00D090] px-3 py-1.5 rounded-xl text-xs font-mono font-bold flex items-center gap-2">
              <Cpu size={14} />
              <span>{lang === "ar" ? `جهاز المعالجة: ${metrics.ai_device}` : `AI Device: ${metrics.ai_device}`}</span>
            </div>
          )}
          <button 
            onClick={fetchHealthData}
            className="bg-[#0F172A] border border-[#26344A] hover:bg-[#151F33] text-[#D7E0EE] px-4 py-2.5 rounded-xl flex items-center gap-2 text-xs font-bold transition-all shadow-sm"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            <span>{lang === "ar" ? "تحديث المؤشرات" : "Refresh Metrics"}</span>
          </button>
        </div>
        <div className={dir === 'rtl' ? 'text-right' : 'text-left'}>
          <h2 className="text-3xl font-bold text-[#D7E0EE] flex items-center gap-3">
            {t('healthTitle')} <Activity className="text-[#F02050]" />
          </h2>
          <p className="text-[#96A8C0] mt-2 text-xs font-medium">{t('healthSub')}</p>
        </div>
      </header>

      {/* Grid: Health Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        
        {/* Card 1: CPU */}
        <div className="bg-[#0F172A] border border-[#26344A] p-5 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <h4 className="text-xs text-[#96A8C0] font-bold uppercase tracking-wider">{lang === "ar" ? "استهلاك المعالج (CPU)" : "CPU Usage"}</h4>
            <p className="text-2xl font-bold text-[#D7E0EE] mt-1 font-mono">{metrics.cpu_usage.toFixed(1)}%</p>
          </div>
          <div className="p-3 bg-[#0B2825] text-[#00D090] rounded-xl">
            <Cpu size={24} />
          </div>
        </div>

        {/* Card 2: RAM */}
        <div className="bg-[#0F172A] border border-[#26344A] p-5 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <h4 className="text-xs text-[#96A8C0] font-bold uppercase tracking-wider">{lang === "ar" ? "استهلاك الذاكرة (RAM)" : "RAM Usage"}</h4>
            <p className="text-2xl font-bold text-[#D7E0EE] mt-1 font-mono">{metrics.ram_usage.toFixed(1)}%</p>
          </div>
          <div className="p-3 bg-indigo-500/10 text-[#707FF0] rounded-xl">
            <HardDrive size={24} />
          </div>
        </div>

        {/* Card 3: GPU */}
        <div className="bg-[#0F172A] border border-[#26344A] p-5 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <h4 className="text-xs text-[#96A8C0] font-bold uppercase tracking-wider">{lang === "ar" ? "كارت الشاشة (GPU)" : "GPU Usage"}</h4>
            <p className="text-2xl font-bold text-[#D7E0EE] mt-1 font-mono">{metrics.gpu_usage.toFixed(1)}%</p>
          </div>
          <div className="p-3 bg-violet-500/10 text-violet-400 rounded-xl">
            <Cpu size={24} />
          </div>
        </div>

        {/* Card 4: VRAM */}
        <div className="bg-[#0F172A] border border-[#26344A] p-5 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <h4 className="text-xs text-[#96A8C0] font-bold uppercase tracking-wider">{lang === "ar" ? "ذاكرة الكارت (VRAM)" : "VRAM Usage"}</h4>
            <p className="text-2xl font-bold text-[#D7E0EE] mt-1 font-mono">{metrics.vram_usage.toFixed(1)}%</p>
          </div>
          <div className="p-3 bg-[#2A2110] text-[#F59E0B] rounded-xl">
            <HardDrive size={24} />
          </div>
        </div>
      </div>

      {/* Services and Performance Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Docker Services */}
        <div className="bg-[#0F172A] border border-[#26344A] rounded-2xl p-6 shadow-sm">
          <h3 className="text-lg font-bold text-[#D7E0EE] mb-6 flex items-center gap-2">
            <Database size={20} className="text-[#707FF0]" /> {lang === "ar" ? "حالة الخدمات وحاويات Docker" : "Docker Services Health"}
          </h3>
          <div className="space-y-4">
            {Object.entries(metrics.services).map(([service, status]) => (
              <div key={service} className="flex justify-between items-center bg-[#151F33] p-4 rounded-xl border border-[#26344A]">
                <span className="font-bold text-[#D7E0EE] capitalize">{service}</span>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  status === 'healthy' || status === 'running' || status === 'ok'
                    ? 'bg-[#0B2825] text-[#00D090] border border-emerald-500/20'
                    : 'bg-[#2A2110] text-[#F59E0B] border border-amber-500/20'
                }`}>
                  {status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* AI Throughput & FPS */}
        <div className="bg-[#0F172A] border border-[#26344A] rounded-2xl p-6 shadow-sm">
          <h3 className="text-lg font-bold text-[#D7E0EE] mb-6 flex items-center gap-2">
            <BarChart2 size={20} className="text-[#707FF0]" /> {lang === "ar" ? "معدلات الأداء والـ FPS للذكاء الاصطناعي" : "AI Throughput & FPS"}
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center bg-[#151F33] p-4 rounded-xl border border-[#26344A]">
              <span className="text-xs font-bold text-[#96A8C0]">{lang === "ar" ? "معدل الفريمات المعالجة (FPS)" : "Processing FPS"}</span>
              <span className="font-mono text-lg font-bold text-[#00D090]">FPS {metrics.fps}</span>
            </div>
            <div className="flex justify-between items-center bg-[#151F33] p-4 rounded-xl border border-[#26344A]">
              <span className="text-xs font-bold text-[#96A8C0]">{lang === "ar" ? "زمن تأخر الاستجابة (Latency)" : "Latency"}</span>
              <span className="font-mono text-lg font-bold text-[#707FF0]">ms {metrics.latency_ms}</span>
            </div>
            <div className="flex justify-between items-center bg-[#151F33] p-4 rounded-xl border border-[#26344A]">
              <span className="text-xs font-bold text-[#96A8C0]">{lang === "ar" ? "الفريمات المهملة والمفقودة (Dropped Frames)" : "Dropped Frames"}</span>
              <span className="font-mono text-lg font-bold text-[#F02050]">{metrics.dropped_frames} {lang === "ar" ? "إطار" : "frames"}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
