# EG Brand: الـ MVP

منصة عربية بتحوّل فكرة المشروع لهوية براند كاملة، وبعدها بتطلّع محتوى كل شهر وتجدوله وتنشره، وبتخطط الإعلانات، وبتحسب تكلفة الـ AI لكل شركة.

## الستاك

| الطبقة | التقنية |
|---|---|
| Frontend | Next.js 15 + React 19 + TypeScript، والواجهة كلها عربي RTL |
| Backend | Python 3.13 + FastAPI + SQLAlchemy 2 |
| قاعدة البيانات | PostgreSQL، أو SQLite للتجربة السريعة |
| الشغل في الخلفية | Worker بيقرا طابور المهام من Postgres (`SKIP LOCKED`): توليد الـ AI والنشر المجدول |
| AI | LiteLLM كـ gateway: سلسلة fallback بين الموديلات، وتسجيل التوكنز والتكلفة لكل شركة، وحد ميزانية شهري |
| التصميم | الشعارات والبوستات بتترسم بالكود على canvas بخطوط عربية حقيقية، فمفيش حروف مشوّهة |
| النشر | Meta Graph API لـ Facebook و Instagram، وربط تجريبي (mock) لباقي المنصات |
| الإعلانات | Meta Marketing API: الحملة بتتعمل **موقوفة**، فمفيش صرف من غير موافقة صاحب الحساب |
| التخزين | محلي، أو S3 / Cloudflare R2 |

```
frontend/ (Next.js)  ──►  backend/app/main.py (FastAPI)
                              ├── routers/   auth · brands · posts · social · ads · usage · jobs
                              ├── ai/        llm.py (gateway) · prompts.py · services.py · occasions.py · mock.py
                              ├── social/    meta.py · publisher.py
                              ├── jobs.py    طابور المهام + النشر المجدول
                              └── worker.py  python -m app.worker
```

## التشغيل محلياً

### الطريقة 1: Docker
```bash
cp backend/.env.example backend/.env   # اختياري: حط مفاتيح الـ AI و Meta
docker compose up --build
```
الواجهة على http://localhost:3000، والـ API على http://localhost:8000/docs

### الطريقة 2: من غير Docker
```bash
# Backend
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000     # الـ worker شغال جوه الـ API (EMBEDDED_WORKER=true)

# Frontend (في terminal تاني)
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

**من غير أي مفاتيح** كل حاجة شغالة: الـ AI بيرجّع بيانات تجريبية ثابتة، والحسابات بتتربط ربط تجريبي. ده مناسب للتطوير والـ tests.

### تشغيل الـ AI الحقيقي
حط مفتاح واحد على الأقل في `backend/.env` (مثلاً `GROQ_API_KEY` أو `ANTHROPIC_API_KEY`)، وظبط الموديلات:
```
LLM_FAST_MODELS=groq/openai/gpt-oss-20b
LLM_QUALITY_MODELS=groq/openai/gpt-oss-120b,groq/qwen/qwen3.8-27b
```
- Groq بيغيّر الموديلات المتاحة باستمرار. اعرف المتاح على حسابك من `https://api.groq.com/openai/v1/models`.
- كل سلسلة بتتجرب بالترتيب: لو موديل وقع، الطلب بيروح للي بعده.
- لو LiteLLM ما يعرفش سعر موديل، حط سعره في `LLM_PRICE_OVERRIDES`، وإلا التكلفة هتتسجل صفر.

### تشغيل النشر الحقيقي على Meta
1. اعمل App على developers.facebook.com وضيف Facebook Login.
2. ضيف الـ Redirect URI: `{PUBLIC_BASE_URL}/api/social/meta/callback`
3. اطلب الصلاحيات دي في App Review: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `business_management`, `ads_management`, `ads_read`.
4. حط `META_APP_ID` و `META_APP_SECRET` في `.env`.
5. **Instagram بينزّل الصورة من رابط عام**، فلازم `STORAGE_BACKEND=s3` مع bucket عام (R2 مثلاً). `localhost` مش هينفع.

## الـ Tests
```bash
cd backend && . .venv/bin/activate && python -m pytest -q
```
بتغطي الرحلة كاملة: تسجيل ← براند ← هوية ← خطة الشهر ← تعديل واعتماد ورفع التصميم ← جدولة ← الـ worker ينشر ← خطة إعلانية ← التكلفة. وكمان عزل الشركات عن بعض، وحد الميزانية، والـ fallback وحساب التكلفة في مسار الـ AI الحقيقي.

## الحالة: إيه اللي شغال وإيه اللي لسه

| الجزء | الحالة |
|---|---|
| تسجيل وشركات (multi-tenant) | ✅ |
| هوية البراند بالـ AI + تعديلها | ✅ |
| خطة محتوى شهرية + مناسبات مصر والسعودية | ✅ (التواريخ الهجرية تقريبية ومحتاجة تتحدث كل سنة في `ai/occasions.py`) |
| تعديل البوست وإعادة صياغته بالـ AI والاعتماد | ✅ |
| جدولة ونشر تلقائي (الربط التجريبي) | ✅ ومتجرب في الـ tests والمتصفح |
| نشر حقيقي على Facebook و Instagram | ⚠️ الكود موجود ومحتاج تطبيق Meta عدّى App Review عشان يتجرب |
| إنشاء حملة إعلانية في Meta (موقوفة) + قراءة النتايج | ⚠️ نفس الكلام: محتاج صلاحية `ads_management` |
| TikTok و Snapchat و X | ❌ ربط تجريبي بس (TikTok محتاج Audit) |
| تكلفة الـ AI لكل شركة + حساب هامش الربح | ✅ |
| Migrations للـ Database | ❌ الجداول بتتعمل بـ `create_all`. ضيفوا Alembic قبل أول عميل حقيقي |
| تجديد توكنز Meta | ❌ توكن الصفحة طويل العمر، بس محتاجين نتعامل مع إلغاء الصلاحية |
