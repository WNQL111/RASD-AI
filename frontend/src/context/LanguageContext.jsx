import React, { createContext, useContext, useState, useEffect } from 'react';

const LanguageContext = createContext();

export const translations = {
  ar: {
    // Brand
    platformName: "رَصْد AI",
    platformEnglishName: "RASD AI",
    platformSubtitle: "منصة المراقبة الأمنية والتحليل الجنائي الذاتي",
    platformEnterprise: "مركز العمليات الأمنية والتحليل الجنائي RASD AI",

    // Navigation & Global
    dashboard: "لوحة التحكم والعمليات",
    uploadVideo: "رفع فيديو أمني",
    eventsHistory: "سجل الحوادث الجنائية",
    investigationCases: "إدارة القضايا الجنائية",
    aiStats: "إحصائيات الذكاء الاصطناعي",
    settings: "إعدادات النظام",
    systemHealth: "حالة وأداء الخادم",
    
    // Header
    liveSurveillance: "مركز المراقبة والعمليات المباشرة",
    liveSurveillanceSub: "منظومة الرصد والتحليل الأمني الذاتي لكاميرات المراقبة ومقاطع الفيديو",
    clearAlerts: "مسح التنبيهات المنتهية",
    muteAlerts: "كتم الصوت",
    unmuteAlerts: "تشغيل الصوت",
    aiActive: "محرك الذكاء الاصطناعي نشط",

    // Sections
    activeCamerasGrid: "شبكة كاميرات المراقبة الحية",
    realtimeAlerts: "الإنذارات والتنبيهات المباشرة",
    processedVideos: "الفيديوهات المرفوعة والمعالجة",
    processedVideosStatus: "سجل الفيديوهات المرفوعة والمعالجة",
    chooseVideo: "اختر فيديو أمني للرفع...",
    uploadBtn: "رفع وتحليل الفيديو",
    noAlerts: "لا توجد تهديدات نشطة حالياً، النظام في حالة استقرار تام.",
    noVideos: "لا توجد فيديوهات مسجلة حتى الآن.",
    noCameras: "لا توجد كاميرات متصلة حالياً.",
    
    // Statuses
    processing: "جاري المعالجة والتحليل...",
    healthy: "فيديو سليم",
    videoClean: "هذا الفيديو سليم",
    videoThreatDetected: "احتوى على تهديدات أمنية",
    videoCompletedClean: "فحص سليم - خالي من التهديدات",
    videoCompletedThreat: "تم رصد وتأكيد حوادث أمنية",
    threatDetected: "تهديد مؤكد",
    startAI: "تشغيل الذكاء الاصطناعي",
    stopAI: "إيقاف الذكاء الاصطناعي",
    aiRunning: "بث مباشر نشط",

    // Pages specific
    eventsHistoryTitle: "سجل الحوادث والتهديدات الأمنية",
    eventsHistorySub: "استعراض كافة الحوادث الجنائية المرصودة مع إمكانية التصفية، والتصدير، والربط بالقضايا الجنائية",
    uploadTitle: "مركز رفع وتحليل الفيديوهات الأمنية",
    uploadSub: "رفع المقاطع الأمنية لإجراء الاستدلال الجنائي واستخراج ملامح الحركة ثنائية وثلاثية الأبعاد",
    settingsTitle: "إعدادات وتكوين منظومة RASD AI",
    settingsSub: "إدارة الكاميرات، ضبط عتبات حساسية العنف والتصادم، وإعدادات المعالجة المحلية",
    healthTitle: "مؤشرات أداء الموارد وعتاد الخادم",
    healthSub: "مراقبة استهلاك المعالجات (CPU)، بطاقة الرسومات (GPU)، الذاكرة (RAM/VRAM)، ومعدل الإطارات (FPS)",
    replayTitle: "الاسترجاع الأمني والتحليل الجنائي الرقمي",
    replaySub: "تحليل دقيق للإطارات والمحرك المكاني والزماني ثلاثي الأبعاد 3D Spatio-Temporal",

    // Alert Card translations
    theft: "اشتباه سرقة أو استيلاء على ممتلكات",
    violence: "اشتباه عراك أو اعتداء جسدي",
    accident: "اصطدام مروري أو حادث سيارة"
  },
  en: {
    // Brand
    platformName: "RASD AI",
    platformEnglishName: "RASD AI",
    platformSubtitle: "AI-Powered Video Surveillance & Forensic Analysis Platform",
    platformEnterprise: "RASD AI Enterprise Security Operations Center",

    // Navigation & Global
    dashboard: "Operations Dashboard",
    uploadVideo: "Upload Security Video",
    eventsHistory: "Security Events Log",
    investigationCases: "Investigation Cases",
    aiStats: "AI Confidence Stats",
    settings: "System Settings",
    systemHealth: "System Health & Telemetry",

    // Header
    liveSurveillance: "Live Surveillance Operations Center",
    liveSurveillanceSub: "Autonomous CCTV Video Analytics & Forensic Intelligence Platform",
    clearAlerts: "Clear Dismissed Alerts",
    muteAlerts: "Mute Audio",
    unmuteAlerts: "Unmute Audio",
    aiActive: "AI ENGINE ONLINE",

    // Sections
    activeCamerasGrid: "ACTIVE SURVEILLANCE CAMERAS GRID",
    realtimeAlerts: "REAL-TIME INCIDENT ALERTS",
    processedVideos: "Processed Videos",
    processedVideosStatus: "PROCESSED VIDEOS & FORENSIC STATUS",
    chooseVideo: "Select surveillance video...",
    uploadBtn: "Upload & Ingest",
    noAlerts: "No active anomalous threats detected. System is nominal.",
    noVideos: "No surveillance videos uploaded yet.",
    noCameras: "No active IP camera streams connected.",

    // Statuses
    processing: "Processing...",
    healthy: "Nominal / Clean",
    videoClean: "Clean Surveillance Video",
    videoThreatDetected: "Security Threat Confirmed",
    videoCompletedClean: "Completed (No Threats)",
    videoCompletedThreat: "Completed (Threats Found)",
    threatDetected: "Confirmed Incident",
    startAI: "START INFERENCE",
    stopAI: "STOP INFERENCE",
    aiRunning: "LIVE ANALYTICS ACTIVE",

    // Pages specific
    eventsHistoryTitle: "Security Events & Forensic Log",
    eventsHistorySub: "Review recorded incidents with multi-parameter filtering, CSV export, and case linking",
    uploadTitle: "Video Forensic Upload Center",
    uploadSub: "Upload surveillance video files for automated edge computer vision and kinematic analysis",
    settingsTitle: "RASD AI Platform Settings",
    settingsSub: "Configure stream sources, kinematic velocity thresholds, and local inference models",
    healthTitle: "Hardware Telemetry & Server Resources",
    healthSub: "Real-time CPU, GPU acceleration, VRAM allocation, FPS throughput, and container readiness",
    replayTitle: "Forensic Video Replay & 3D Investigation",
    replaySub: "Frame-accurate evidence playback with 3D Spatio-Temporal action verification",

    // Alert Card translations
    theft: "Suspected Theft / Larceny",
    violence: "Suspected Physical Violence / Assault",
    accident: "Vehicle Collision / Accident"
  }
};

export const LanguageProvider = ({ children }) => {
  const [lang, setLang] = useState(() => localStorage.getItem("rasd_lang") || localStorage.getItem("asis_lang") || "ar");

  const toggleLang = () => {
    setLang(prev => {
      const next = prev === "ar" ? "en" : "ar";
      localStorage.setItem("rasd_lang", next);
      return next;
    });
  };

  const dir = lang === "ar" ? "rtl" : "ltr";

  useEffect(() => {
    document.documentElement.dir = dir;
    document.documentElement.lang = lang;
  }, [lang, dir]);

  const t = (key) => {
    return translations[lang]?.[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, toggleLang, dir, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
