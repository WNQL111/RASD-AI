# دليل الواجهة الخلفية والخادم المركزي — Backend Subsystem
## RASD AI (رَصْد AI) Backend Architecture & Component Manual

---

## 1. الغرض من المجلد (Purpose)
يمثل مجلد `backend/` النواة المركزية لإدارة البيانات، وتوجيه الطلبات، وتنسيق تدفق الفيديوهات، وبث التنبيهات الأمنية الحية إلى الواجهة الأمامية. تم بناء هذا الجزء باستخدام إطار العمل عالي الأداء **FastAPI** في بيئة **Python 3.10** غير المتزامنة (Asynchronous).

---

## 2. الوظيفة التي يؤديها داخل المشروع
- **بوابة الـ API المركزية**: يستقبل طلبات الـ HTTP من متصفح المستخدم (إدارة الكاميرات، رفع الفيديوهات، مراجعة السجلات، وتعديل القواعد).
- **بث التنبيهات اللحظي (Server-Sent Events - SSE)**: يدفع الأحداث الأمنية المكتشفة إلى غرفة العمليات (SOC) دون تأخير ودون حاجة لتكرار الاستعلام من المتصفح (No Polling).
- **إدارة قاعدة البيانات (ORM Layer)**: تحويل كائنات بايثون إلى سجلات وجداول في قاعدة بيانات SQLite/Postgres عبر مكتبة SQLAlchemy.
- **خدمة بث وتخزين الفيديو (Video Streaming Server)**: تقديم ملفات الفيديو والمقاطع الجنائية المقتطعة مع دعم الترويسة `Range: bytes=` للسماح للمشغل بالقفز الفوري لأي ثانية في الفيديو دون انتظار تحميل الملف كاملاً.
- **التنسيق مع عامل الذكاء الاصطناعي**: استقبال مهام التحليل وتحديث حالة معالجة الفيديو في قاعدة البيانات.

---

## 3. الهيكل الداخلي وأهم المجلدات والملفات

```
backend/
├── Dockerfile                  # تهيئة تشغيل الخادم داخل حاوية Docker
├── requirements.txt            # قائمة التبعيات البرمجية (FastAPI, SQLAlchemy, Uvicorn...)
└── app/
    ├── main.py                 # نقطة الدخول الرئيسية، تهيئة CORS، الترحيلات التلقائية، وبدء الخادم
    ├── core/
    │   └── config.py           # المتغيرات البيئية ومسارات التخزين
    ├── db/
    │   └── database.py         # إعداد محرك الاتصال بـ SQLite/PostgreSQL وإدارة الجلسات
    ├── models/
    │   ├── models.py           # الـ 16 نموذجاً لكيانات قاعدة البيانات (User, Video, Camera, Event, Alert...)
    │   └── verification.py     # نماذج التحقق الخارجي المساعد
    ├── schemas/
    │   └── schemas.py          # نماذج Pydantic للتحقق من صحة المدخلات وضمان أمان البيانات
    ├── services/
    │   ├── broadcaster.py      # إدارة قوائم انتظار بث أحداث الـ SSE الفورية للمتصفحات
    │   ├── redis_listener.py   # الاستماع للرسائل الواردة عبر Redis Pub/Sub عند تفعيله
    │   ├── security.py         # تشفير كلمات المرور والتحقق من التوكنات (JWT & Passlib)
    │   ├── storage.py          # إدارة المجلدات ومسارات حفظ الفيديوهات واللقطات
    │   └── video_processor.py  # معالجة وتحويل الفيديوهات والتأكد من دعمها للبث السلس
    └── api/
        ├── endpoints.py        # مجمع المسارات الرئيسي
        └── routers/            # 8 موجهات فرعية مستقلة ومفصولة بحسب المسؤولية:
            ├── alerts.py       # إدارة التنبيهات الأمنية وبث SSE المباشر
            ├── audit.py        # استعراض سجلات تدقيق نشاطات المشغلين
            ├── auth.py         # تسجيل الدخول وإنشاء المستخدمين
            ├── cameras.py      # إدارة الكاميرات وبدء/إيقاف التحليل
            ├── cases.py        # إنشاء وإدارة القضايا الجنائية وتوثيق الأدلة
            ├── events.py       # سجل الأحداث الأمنية وتغذية المشغل الراجعة
            ├── health.py       # مقاييس صحة النظام والعتاد
            ├── rules.py        # قراءة وتعديل عتبات خوارزميات الذكاء الاصطناعي
            └── videos.py       # رفع الفيديوهات وبدء التحليل الجنائي
```

---

## 4. نقطة الدخول والتشغيل (Entry Point)
- **الملف التنفيذي**: `backend/app/main.py`
- **أمر التشغيل المباشر**:
  ```bash
  cd backend
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
  ```
- **المنافذ المستخدمة**: المنفذ `8001` (لتفادي التعارض مع خوادم الويب الافتراضية على 8000).

---

## 5. أهم الفئات والدوال التي يجب فهمها

1. **`get_db()` في [database.py](file:///e:/final%20project/AI%20Security%20Platform%20V2/backend/app/db/database.py)**:
   - مولد جلسات قاعدة البيانات (Database Session Generator). يفتح جلسة عمل مع كل طلب API ويغلقها تلقائياً بعد انتهاء المعالجة لتفادي تسريب الاتصالات (Connection Leaks).
2. **`Event` و `Alert` و `Camera` في [models.py](file:///e:/final%20project/AI%20Security%20Platform%20V2/backend/app/models/models.py)**:
   - فئات الـ ORM التي تمثل الجداول في قاعدة البيانات وتحدد العلاقات الأجنبية (Foreign Keys) كربط التنبيه بحدث، والحدث بكاميرا أو فيديو.
3. **`alerts_stream()` في [alerts.py](file:///e:/final%20project/AI%20Security%20Platform%20V2/backend/app/api/routers/alerts.py)**:
   - دالة مولدة للبث الحي تعيد `EventSourceResponse` لإبقاء قناة مفتوحة بين المتصفح والخادم ودفع التنبيهات فور تسجيلها في النظام.
4. **`upload_video()` و `analyze_video()` في [videos.py](file:///e:/final%20project/AI%20Security%20Platform%20V2/backend/app/api/routers/videos.py)**:
   - استقبال ملف الفيديو، حفظه محلياً في مجلد `data/videos/`، تسجيله في قاعدة البيانات كـ `pending`، ثم بدء عملية الاستدلال والتحليل.

---

## 6. البيانات التي يستقبلها وينتجها الخادم

- **المدخلات (Inputs)**:
  - ملفات الفيديو الرقمية المرفوعة (تنسيقات MP4, AVI, MKV).
  - طلبات JSON لإنشاء الكاميرات، تعديل عتبات الحساسية، وتدوين ملاحظات القضايا.
  - إشارات التحقق والـ Feedback من مشغلي غرفة المراقبة.
- **المخرجات (Outputs)**:
  - استجابات JSON لبيانات الكاميرات والأحداث والإحصائيات.
  - تدفق نصوص SSE للأحداث الأمنية الفورية.
  - بث وسائط متعددة (Video Stream) مع ترويسات قبول النطاق (Accept-Ranges: bytes).

---

## 7. الأخطاء الشائعة وحلولها

1. **خطأ `sqlite3.OperationalError: database is locked`**:
   - يحدث عندما تحاول عمليات متعددة الكتابة في نفس اللحظة. تم حله في `database.py` بضبط خيار `connect_args={"check_same_thread": False}` واعتماد جلسات منفصلة.
2. **خطأ `CORS Policy Error`**:
   - يحدث عند محاولة الواجهة على المنفذ `4000` التخاطب مع الخادم على `8001`. تم حله في `main.py` بتفعيل وسيط `CORSMiddleware` مع السماح بكافة الترويسات والأساليب.

---

## 8. أسئلة المناقشة الأكاديمية الخاصة بالـ Backend

### س1: لماذا تم اختيار FastAPI بدلاً من Django أو Flask في هذا المشروع؟
**الإجابة النموذجية**:
- لأن FastAPI مبني بالكامل على مكتبة `asyncio` ومعيار `Starlette` و `ASGI`، مما يجعله فائق السرعة في معالجة آلاف الطلبات غير المتزامنة ومثالياً لبث التنبيهات الفورية (SSE) وبث الفيديو دون تجميد خيط المعالجة الرئيسي (Non-blocking I/O). كما يوفر تحققاً تلقائياً من صحة البيانات عبر `Pydantic` وتوثيقاً تفاعلياً تلقائياً عبر Swagger UI.

### س2: كيف يضمن النظام عدم تسريب اتصالات قاعدة البيانات أثناء فتح الجلسات؟
**الإجابة النموذجية**:
- عبر نمط الاعتمادية `Depends(get_db)` في FastAPI، حيث تستخدم الدالة `yield db` داخل كتلة `try...finally` لضمان إغلاق الجلسة وتحريرها وإعادتها لحوض الاتصالات فور اكتمال معالجة الطلب، حتى لو حدث استثناء (Exception).

---

## 9. روابط الشروحات التفصيلية لملفات الـ Backend
- [شرح main.py التفصيلي](file:///e:/final%20project/AI%20Security%20Platform%20V2/docs/file-reference/backend_main.py.md)
- [شرح database.py التفصيلي](file:///e:/final%20project/AI%20Security%20Platform%20V2/docs/file-reference/backend_database.py.md)
- [شرح models.py التفصيلي](file:///e:/final%20project/AI%20Security%20Platform%20V2/docs/file-reference/backend_models.py.md)
- [شرح alerts.py وبث SSE التفصيلي](file:///e:/final%20project/AI%20Security%20Platform%20V2/docs/file-reference/backend_alerts.py.md)
- [شرح videos.py ومعالجة الفيديو التفصيلي](file:///e:/final%20project/AI%20Security%20Platform%20V2/docs/file-reference/backend_videos.py.md)
