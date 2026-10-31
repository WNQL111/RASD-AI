import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, ShieldAlert, Loader2, Download, Eye, Calendar, Tag, Shield, Info, ClipboardList, Link2, Unlink, Plus } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import api from '../services/api';

export default function Events() {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [expandedEventId, setExpandedEventId] = useState(null);

  const fetchEventsAndCases = async () => {
    try {
      const [eventsRes, casesRes] = await Promise.all([
        api.get('/events'),
        api.get('/cases').catch(() => ({ data: [] }))
      ]);
      setEvents((eventsRes.data || []).sort((a, b) => new Date(b.start_time) - new Date(a.start_time)));
      setCases(casesRes.data || []);
    } catch (err) {
      console.error("Failed to fetch events:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEventsAndCases();
  }, []);

  const handleExportCSV = () => {
    if (events.length === 0) return;
    
    const headers = ["Event ID", "Type", "Confidence", "Severity", "Status", "Timestamp", "Video ID", "Camera ID"];
    const rows = events.map(e => [
      e.id,
      e.type,
      e.confidence,
      e.severity || 'high',
      e.status || 'unread',
      e.start_time,
      e.video_id || '',
      e.camera_id || ''
    ]);

    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `RASD_AI_Events_Export_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredEvents = events.filter(e => {
    const matchesSearch = e.id.toString().includes(searchTerm) || 
      (e.video_id && e.video_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (e.type && e.type.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesType = typeFilter === "all" || e.type.startsWith(typeFilter);
    const matchesSeverity = severityFilter === "all" || (e.severity || 'high') === severityFilter;

    return matchesSearch && matchesType && matchesSeverity;
  });

  const handleAssignEventToCase = async (eventId, caseId) => {
    try {
      await api.post(`/events/${eventId}/link-case/${caseId}`);
      fetchEventsAndCases();
    } catch (err) {
      console.error("Failed to link event to case:", err);
      alert(err.response?.data?.detail || "فشل ربط الحادث بالقضية");
    }
  };

  const handleCreateCaseFromEvent = (event) => {
    navigate('/cases', { state: { fromEvent: event } });
  };

  const { lang, dir, t } = useLanguage();

  return (
    <div className="p-8 max-w-7xl mx-auto h-full flex flex-col overflow-y-auto bg-[#020618] text-[#D7E0EE]" dir={dir}>
      <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className={dir === 'rtl' ? 'text-right' : 'text-left'}>
          <h2 className="text-3xl font-bold text-[#D7E0EE] tracking-tight">{t('eventsHistoryTitle')}</h2>
          <p className="text-[#96A8C0] mt-2 text-sm">{t('eventsHistorySub')}</p>
        </div>
        
        <div className="flex gap-3 w-full md:w-auto">
          <button 
            onClick={handleExportCSV}
            disabled={filteredEvents.length === 0}
            className="bg-[#0F172A] border border-[#26344A] text-[#D7E0EE] px-4 py-2.5 rounded-xl flex items-center gap-2 hover:bg-[#151F33] hover:border-[#26344A] disabled:opacity-40 transition-colors text-sm font-semibold shadow-sm"
          >
            <Download size={16} /> Export CSV
          </button>
        </div>
      </header>

      {/* Advanced Filters Panel */}
      <div className="bg-[#0F172A] border border-[#26344A] p-4 rounded-2xl mb-6 grid grid-cols-1 md:grid-cols-4 gap-4 shadow-sm">
        <div className="relative col-span-1 md:col-span-2">
          <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#96A8C0]" />
          <input 
            type="text" 
            placeholder="Search Event ID, Type or Video ID..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#151F33] border border-[#26344A] rounded-xl pl-11 pr-4 py-2.5 text-sm text-[#D7E0EE] placeholder-slate-400 focus:outline-none focus:bg-[#0F172A] focus:border-[#707FF0] transition-colors"
          />
        </div>
        
        <div>
          <select 
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="w-full bg-[#151F33] border border-[#26344A] rounded-xl px-4 py-2.5 text-sm text-[#D7E0EE] focus:outline-none focus:bg-[#0F172A] focus:border-[#707FF0]"
          >
            <option value="all">All Types</option>
            <option value="violence">Violence</option>
            <option value="collision">Collision / Accident</option>
            <option value="accident">Accident</option>
          </select>
        </div>

        <div>
          <select 
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="w-full bg-[#151F33] border border-[#26344A] rounded-xl px-4 py-2.5 text-sm text-[#D7E0EE] focus:outline-none focus:bg-[#0F172A] focus:border-[#707FF0]"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-[#0F172A] border border-[#26344A] rounded-2xl shadow-sm overflow-hidden flex flex-col flex-1">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#26344A] bg-[#151F33]">
                <th className="p-4 text-xs font-bold uppercase tracking-wider text-[#96A8C0] w-16"></th>
                <th className="p-4 text-xs font-bold uppercase tracking-wider text-[#96A8C0]">Event ID</th>
                <th className="p-4 text-xs font-bold uppercase tracking-wider text-[#96A8C0]">Type</th>
                <th className="p-4 text-xs font-bold uppercase tracking-wider text-[#96A8C0]">Severity</th>
                <th className="p-4 text-xs font-bold uppercase tracking-wider text-[#96A8C0]">Confidence</th>
                <th className="p-4 text-xs font-bold uppercase tracking-wider text-[#96A8C0]">Timestamp</th>
                <th className="p-4 text-xs font-bold uppercase tracking-wider text-[#96A8C0]">Source</th>
                <th className="p-4 text-xs font-bold uppercase tracking-wider text-[#96A8C0]">القضية (Case)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#26344A]">
              {loading ? (
                <tr>
                  <td colSpan="8" className="p-12 text-center text-[#96A8C0]">
                    <Loader2 size={32} className="animate-spin mx-auto mb-4 opacity-50 text-[#707FF0]" />
                    <p>Loading historical events...</p>
                  </td>
                </tr>
              ) : filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan="8" className="p-12 text-center text-[#96A8C0]">
                    <ShieldAlert size={32} className="mx-auto mb-4 opacity-30 text-[#F02050]" />
                    <p>No historical events matching filters found.</p>
                  </td>
                </tr>
              ) : (
                filteredEvents.map((event) => {
                  const isExpanded = expandedEventId === event.id;
                  const severity = event.severity || 'high';
                  const isCritical = severity === 'critical';
                  const isHigh = severity === 'high';
                  const linkedCase = cases.find(c => c.id === event.case_id);

                  return (
                    <React.Fragment key={event.id}>
                      <tr 
                        className={`hover:bg-[#151F33]/30 transition-colors cursor-pointer ${isExpanded ? 'bg-[#151F33]/50' : ''}`}
                        onClick={() => setExpandedEventId(isExpanded ? null : event.id)}
                      >
                        <td className="p-4 text-center">
                          <Eye size={16} className={`text-[#96A8C0] transition-transform ${isExpanded ? 'text-[#707FF0] scale-110' : ''}`} />
                        </td>
                        <td className="p-4 font-mono text-sm text-[#D7E0EE] font-semibold">#{event.id}</td>
                        <td className="p-4">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-widest border ${
                            event.type.startsWith('violence') ? 'bg-[#2A1020] text-[#F02050] border border-[#B91C3B]' :
                            event.type.startsWith('theft') ? 'bg-[#2A2110] text-[#F59E0B] border border-[#C09020]' :
                            'bg-sky-500/10 text-sky-400 border-sky-500/20'
                          }`}>
                            {event.type}
                          </span>
                        </td>
                        <td className="p-4">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            isCritical ? 'bg-[#2A1020] text-[#F02050] border border-[#B91C3B]' :
                            isHigh ? 'bg-[#2A2110] text-[#F59E0B] border border-[#C09020]' :
                            'bg-slate-700 text-[#D7E0EE]'
                          }`}>
                            {severity}
                          </span>
                        </td>
                        <td className="p-4">
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-[#D7E0EE] font-medium font-mono">{(event.confidence * 100).toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="p-4 text-sm text-[#96A8C0] font-mono">
                          {new Date(event.start_time).toLocaleString()}
                        </td>
                        <td className="p-4 text-xs text-[#96A8C0] font-mono">
                          {event.camera_id ? `CAM_${event.camera_id}` : event.video_id ? 'Video Upload' : 'N/A'}
                        </td>
                        <td className="p-4" onClick={(e) => e.stopPropagation()}>
                          {linkedCase ? (
                            <button
                              onClick={() => navigate('/cases')}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold bg-[#151F33] hover:bg-blue-100 text-[#707FF0] border border-[#D4E1F0] transition-all max-w-[160px] truncate"
                              title={`مرتبط بالقضية: ${linkedCase.title}`}
                            >
                              <ClipboardList size={13} className="shrink-0" />
                              <span className="truncate">قضية #{linkedCase.id}</span>
                            </button>
                          ) : (
                            <button
                              onClick={() => handleCreateCaseFromEvent(event)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-[#151F33] hover:bg-[#707FF0] text-[#D7E0EE] hover:text-white border border-[#26344A] transition-all"
                            >
                              <Plus size={12} />
                              <span>فتح قضية</span>
                            </button>
                          )}
                        </td>
                      </tr>

                      {/* Expandable Forensics Panel */}
                      {isExpanded && (
                        <tr className="bg-[#151F33]/40">
                          <td colSpan="8" className="p-6 border-t border-b border-[#26344A]">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                              <div>
                                <h4 className="text-xs font-bold text-[#96A8C0] uppercase tracking-widest mb-3 flex items-center gap-1.5">
                                  <Info size={14} className="text-[#707FF0]" /> Forensic Evidence Snapshot
                                </h4>
                                {event.snapshots && event.snapshots.length > 0 ? (
                                  <div className="relative border border-[#26344A] rounded-xl overflow-hidden shadow-2xl">
                                    <img 
                                      src={`http://${window.location.hostname}:8001${event.snapshots[0].image_path}`} 
                                      alt="Evidence snapshot" 
                                      className="w-full h-auto object-cover max-h-56"
                                    />
                                    <div className="absolute bottom-2 left-2 bg-[#0F172A]/90 px-3 py-1 rounded text-[10px] text-[#D7E0EE] font-mono border border-[#26344A]">
                                      ID: {event.snapshots[0].id}
                                    </div>
                                  </div>
                                ) : (
                                  <div className="bg-[#0F172A]/40 border border-slate-850 p-6 rounded-xl flex items-center justify-center text-xs text-[#96A8C0] italic">
                                    No photo snapshot captured for this event.
                                  </div>
                                )}
                              </div>

                              <div>
                                <h4 className="text-xs font-bold text-[#96A8C0] uppercase tracking-widest mb-3 flex items-center gap-1.5">
                                  <Shield size={14} className="text-[#707FF0]" /> Event Details & Case Management
                                </h4>
                                <div className="space-y-3 text-xs">
                                  <div className="p-3 bg-[#0F172A] rounded-xl border border-[#26344A] shadow-sm space-y-1">
                                    <div className="text-[#96A8C0] font-medium">Description:</div>
                                    <p className="text-[#D7E0EE] text-sm">
                                      {event.type.startsWith('theft') ? `Asset theft of portable item reported.` : 
                                       event.type.startsWith('collision') ? `Traffic collision event detected.` :
                                       `Aggressive fighting or violence observed.`}
                                    </p>
                                  </div>
                                  
                                  <div className="grid grid-cols-2 gap-4">
                                    <div className="p-3 bg-[#0F172A] rounded-xl border border-[#26344A] shadow-sm">
                                      <div className="text-[#96A8C0]">Involved Track IDs</div>
                                      <div className="text-[#D7E0EE] font-mono mt-1 text-sm">{JSON.stringify(event.involved_track_ids)}</div>
                                    </div>
                                    <div className="p-3 bg-[#0F172A] rounded-xl border border-[#26344A] shadow-sm">
                                      <div className="text-[#96A8C0]">Clip Recorded</div>
                                      <div className="text-[#D7E0EE] mt-1 font-semibold">
                                        {event.clips && event.clips.length > 0 ? (
                                          <a 
                                            href={`http://${window.location.hostname}:8001${event.clips[0].clip_path}`} 
                                            target="_blank" 
                                            rel="noopener noreferrer"
                                            className="text-[#707FF0] hover:underline"
                                          >
                                            View Video Clip (15s)
                                          </a>
                                        ) : (
                                          'No Clip Available'
                                        )}
                                      </div>
                                    </div>
                                  </div>

                                  {/* Direct Case Actions Block */}
                                  <div className="p-3.5 bg-[#151F33]/60 border border-[#D4E1F0] rounded-xl space-y-2.5">
                                    <div className="flex justify-between items-center">
                                      <span className="font-bold text-[#D7E0EE] flex items-center gap-1.5">
                                        <ClipboardList size={14} /> ملف التحقيق الجنائي
                                      </span>
                                      {linkedCase && (
                                        <span className="text-[10px] bg-blue-100 text-[#D7E0EE] px-2 py-0.5 rounded-full font-mono">
                                          Case #{linkedCase.id}
                                        </span>
                                      )}
                                    </div>

                                    {linkedCase ? (
                                      <div className="flex items-center justify-between gap-2 pt-1">
                                        <span className="text-[#D7E0EE] truncate font-semibold">
                                          {linkedCase.title}
                                        </span>
                                        <div className="flex items-center gap-2 shrink-0">
                                          <button
                                            onClick={() => navigate('/cases')}
                                            className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-[11px] font-bold transition-all"
                                          >
                                            عرض القضية
                                          </button>
                                          <button
                                            onClick={() => handleAssignEventToCase(event.id, 0)}
                                            className="px-2 py-1 bg-slate-800 hover:bg-[#2A1020]/40 text-[#96A8C0] hover:text-[#F02050] rounded-lg text-[11px] transition-all"
                                            title="فك ارتباط الحادث عن هذه القضية"
                                          >
                                            <Unlink size={13} />
                                          </button>
                                        </div>
                                      </div>
                                    ) : (
                                      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 pt-1">
                                        <button
                                          onClick={() => handleCreateCaseFromEvent(event)}
                                          className="flex-1 px-3 py-1.5 bg-[#707FF0] hover:bg-[#3935A8] text-white rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 shadow-sm shadow-slate-500/10"
                                        >
                                          <Plus size={14} />
                                          <span>إنشاء قضية جديدة من هذا الحادث</span>
                                        </button>

                                        {cases.length > 0 && (
                                          <select
                                            defaultValue=""
                                            onChange={(e) => {
                                              if (e.target.value) {
                                                handleAssignEventToCase(event.id, Number(e.target.value));
                                              }
                                            }}
                                            className="bg-[#0F172A] border border-[#26344A] rounded-lg px-2.5 py-1.5 text-xs text-[#D7E0EE] focus:outline-none focus:border-[#707FF0] shadow-sm"
                                          >
                                            <option value="">-- أو ربط بقضية مفتوحة --</option>
                                            {cases.map(c => (
                                              <option key={c.id} value={c.id}>
                                                Case #{c.id}: {c.title}
                                              </option>
                                            ))}
                                          </select>
                                        )}
                                      </div>
                                    )}
                                  </div>

                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
