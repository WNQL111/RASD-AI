# دليل أدوات الفحص والقياس الميداني — Tools & Diagnostic Utilities
## RASD AI (رَصْد AI) System Tools & Benchmarking Manual

---

## 1. الغرض من المجلد (Purpose)
يحتوي مجلد `tools/` على 22 أداة هندسية وسكربت مستقل مخصص لقياس الأداء الحقيقي (Performance Benchmarking)، وفحص الحدود المكانية والزمنية، ومراقبة صحة الخوادم، والتحقق من حوكمة عزل النطاقات الأمنية.

---

## 2. أهم الأدوات ووظائفها

| اسم الأداة | الأمر البرمجي | الوظيفة الهندسية |
| :--- | :--- | :--- |
| **`check_health.py`** | `python tools/check_health.py` | مسبار فحص صحة وجاهزية خادم الـ Backend (منفذ 8001) والواجهة (منفذ 4000) المستخدم في `run.bat`. |
| **`benchmark_models.py`** | `python tools/benchmark_models.py` | قياس زمن استدلال النماذج العصبية بالميلي ثانية ومعدل الإطارات بالثانية (FPS) على الـ GPU والـ CPU. |
| **`benchmark_crowd_behavior.py`** | `python tools/benchmark_crowd_behavior.py` | قياس دقة محرك كبح تيارات الحشود والتحقق من تفريغ رصيد الشبهة عند الحركة الجماعية. |
| **`benchmark_collision.py`** | `python tools/benchmark_collision.py` | اختبار سيناريوهات تصادم المركبات بالمشاة وقياس استجابة خوارزميات التباطؤ الشديد. |
| **`run_video_regression.py`** | `python tools/run_video_regression.py` | تشغيل اختبارات التراجع الأوتوماتيكية على مقاطع الفيديو لضمان عدم تدهور دقة النظام. |
| **`check_domain_boundaries.py`** | `python tools/check_domain_boundaries.py` | فحص حوكمة الكود والتأكد من عدم استيراد دوال العنف داخل منطق الاصطدام أو العكس. |

---

## 3. طريقة استخدام الأدوات للاختبار والقياس

### قياس زمن استدلال النماذج:
```bash
python tools/benchmark_models.py
```
يعرض تقريراً مفصلاً حول:
- استهلاك الذاكرة الرسومية VRAM.
- زمن معالجة كل إطار عبر YOLOv8.
- زمن التحقق الحركي عبر شبكة 3D ResNet.

### فحص صحة النظام التلقائي:
```bash
python tools/check_health.py http://localhost:8001/ http://localhost:4000/ 20
```
يقوم بمراقبة منافذ النظام لمدة 20 ثانية للتأكد من اكتمال إقلاع كافة الخدمات بنجاح.
