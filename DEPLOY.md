# نشر EG Brand أونلاين ببلاش

الخطة دي بتشغّل المنصة كاملة من غير ما تدفع حاجة، وتنفع للديمو ولأول كام عميل. الحدود المجانية بتتغير، فراجعها في صفحة كل خدمة قبل ما تعتمد عليها.

| الجزء | الخدمة | المجاني (وقت كتابة الملف) | ملاحظات |
|---|---|---|---|
| قاعدة البيانات | [Neon](https://neon.tech) Postgres | حوالي 0.5GB | كفاية جداً لمئات البراندات |
| الـ API والـ worker | [Render](https://render.com) Web Service | Free instance | بينام بعد ربع ساعة من غير زيارات، وبنصحّيه بالـ cron تحت |
| الواجهة | [Netlify](https://netlify.com) أو [Vercel](https://vercel.com) | Free | خطة Vercel المجانية للاستخدام الشخصي بس. لما يبقى عندك عملاء بيدفعوا استخدم Netlify أو Vercel Pro |
| تخزين التصميمات | [Cloudflare R2](https://developers.cloudflare.com/r2/) | 10GB ومفيش رسوم تحميل | لازم يكون عام، عشان Instagram بينزّل الصورة من رابط |
| الـ AI للكلام | [Groq](https://console.groq.com) | Free tier بحدود في الدقيقة واليوم | لو اتزنقت ضيف `GEMINI_API_KEY` كـ fallback (عنده Free tier برضه) |
| صور الـ AI | [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) (FLUX schnell) | حصة يومية مجانية | نفس حساب R2 |
| صور حقيقية | [Pexels API](https://www.pexels.com/api/) | مجاني، والاستخدام التجاري مسموح | المنصة بتحفظ اسم المصور وبتعرضه |
| تشغيل المهام كل 5 دقايق | [cron-job.org](https://cron-job.org) | مجاني | بيصحّي Render وبينشر البوستات اللي جه ميعادها |

## 1) قاعدة البيانات (Neon)
1. اعمل project، وانسخ الـ connection string.
2. غيّر أوله من `postgresql://` لـ `postgresql+psycopg://`، وسيب `?sslmode=require` في آخره.
3. ده هيبقى `DATABASE_URL`. الجداول بتتعمل لوحدها أول ما الـ API يشتغل.

## 2) التخزين وصور الـ AI (Cloudflare)
1. **R2:**
   - اعمل bucket (مثلاً `egbrand`).
   - من Settings فعّل **Public access** (r2.dev) أو اربط دومين، وانسخ الرابط العام.
   - من **Manage R2 API Tokens** اعمل token بصلاحية Object Read & Write.
2. **CORS للـ bucket:** الواجهة بترسم الصورة على canvas، فلازم الـ bucket يسمح بالدومين بتاعها:
   ```json
   [{"AllowedOrigins": ["https://your-frontend.netlify.app"], "AllowedMethods": ["GET"], "AllowedHeaders": ["*"]}]
   ```
3. **Workers AI:**
   - انسخ الـ Account ID من الصفحة الرئيسية.
   - اعمل API token من My Profile ← API Tokens بصلاحية **Workers AI: Read/Edit**.

## 3) الـ API (Render)
1. New ← Web Service ← اختار الريبو.
   - Root Directory: `backend`
   - Runtime: Docker
   - Instance: Free
2. Environment، وكل القيم دي بتتحط في Render نفسه، مش في الكود:
   ```
   DATABASE_URL=postgresql+psycopg://...neon.tech/neondb?sslmode=require
   JWT_SECRET=<نص عشوائي طويل>
   TOKEN_ENCRYPTION_KEY=<python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
   EMBEDDED_WORKER=true
   CRON_SECRET=<نص عشوائي>
   CORS_ORIGINS=https://your-frontend.netlify.app
   FRONTEND_URL=https://your-frontend.netlify.app
   PUBLIC_BASE_URL=https://your-api.onrender.com
   GROQ_API_KEY=...
   PEXELS_API_KEY=...
   CF_ACCOUNT_ID=...
   CF_API_TOKEN=...
   STORAGE_BACKEND=s3
   S3_BUCKET=egbrand
   S3_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
   S3_ACCESS_KEY=...
   S3_SECRET_KEY=...
   S3_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev
   META_APP_ID=...
   META_APP_SECRET=...
   ```
3. افتح `https://your-api.onrender.com/api/health`. لازم تلاقي `"ai":"live"` و `"images":"cloudflare"` و `"stock":"pexels"`.

> الديسك على Render المجاني بيتمسح مع كل تشغيل، عشان كده لازم `STORAGE_BACKEND=s3`.

## 4) الواجهة (Netlify أو Vercel)
- Base directory: `frontend`.
- Environment: `NEXT_PUBLIC_API_URL=https://your-api.onrender.com`.
- الاتنين بيتعرفوا على Next.js لوحدهم.

## 5) الـ cron (cron-job.org)
اعمل job بالإعدادات دي:
- **URL:** `https://your-api.onrender.com/api/cron/tick`
- **Method:** POST
- **Header:** `X-Cron-Secret: <نفس CRON_SECRET>`
- **التكرار:** كل 5 دقايق

ده بيخلي الـ API صاحي، وبيشغّل مهام الـ AI، وبينشر أي بوست جه ميعاده.

## 6) قبل ما توري العميل
- [ ] سجّل حساب، واعمل براند، وكمّل الدراسة لحد ما تطلع الاستراتيجية.
- [ ] جرّب "صورة حقيقية" و"صورة بالـ AI" على بوست.
- [ ] اربط صفحة Facebook بالتوكن، وجدول بوست بعد 10 دقايق، واتأكد إنه اتنشر.
- [ ] من صفحة التكلفة، اتأكد إن الاستهلاك بيتسجل.

## لما يبقى فيه فلوس
| النقلة | ليه |
|---|---|
| Render Starter | من غير نوم، والـ worker يبقى شغال لوحده |
| `FAL_KEY` | صور AI أسرع وبمقاسات البوست والستوري بالظبط (حوالي 0.003$ للصورة) |
| مفتاح Anthropic أو OpenAI في آخر سلسلة الـ fallback | جودة أعلى للاستراتيجية |
| Meta App Review | ربط أي عميل من غير ما تضيفه Tester |
