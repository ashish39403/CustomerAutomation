# Testing Checklist

Testing ke time ye questions puchne ke liye (AI se ya khud se). Ek hi file me sab — scenario, question, aur expected result.

Legend: `[ ]` = not tested, `[x]` = pass, `[!]` = fail

---

## 1. Gmail Poll Flow (`poll_gmail`)

- [ ] `poll_gmail` ek real connected account ke liye chal raha hai? (Neon DB me `gmail_accounts` → sirf 1 row, real email, token `gAAAAABq...` prefix)
- [ ] Poll ke baad naye customer emails `tickets` table me aa rahe hain?
- [ ] Duplicate email dobara poll ho to kya hota hai? (same thread 2 tickets nahi banna chahiye)
- [ ] Main jaisa error sikh lo: `gmail refresh token decrypt failed` → matlab DB me koi fake row hai ya `GOOGLE_TOKEN_ENCRYPTION_KEY` badal gaya
- [ ] Google token revoke/expire ho jaye (ya password change) → job ko DEAD na hokar clear "auth fix" state dena chahiye

Puchne layak question: *"poll_gmail abhi healthy hai? jobs table me kuch dead/retry hai?"*

## 2. Jobs Queue (retry / dead / worker)

- [ ] Transient error pe 5 baar retry hota hai aur phir DEAD? (attempts 1→5, backoff)
- [ ] Dead jobs dashboard me dikh rahe hain aur Retry button kaam karta hai?
- [ ] DB dobara start karne pe queue se jobs dobara pick nahi ho rahe hoBackground me clean reh na chahiye)
- [ ] Worker band ho queue to jobs `queued` me rahein — me perteind (no stuck in "running" forever)

Puchne layak question: *"worker kill karne pe kya hota hai? lease expire hone pe job phir se hota hai?"*

## 3. AI Classification / Agent

- [ ] Naya customer reply naya `AiRun` row create karta hai? (model, classification, confidence)
- [ ] Galti se AI API down ho → job TRANSIENT retry (na crash, na wrong send)
- [ ] Classification galat pe "Needs Review" me dikhta hai (automatic send nahi hua)
- [ ] Model name `.env` me sahi hai? (`CLASSIFIER_MODEL`, `AGENT_MODEL` — anthtropic/`prefix` ka dhyan)

Puchne layak question: *"AI fail ho to lis dwast nahi hota? Review queue me catch hota hai?"*

## 4. Auto-Send / Send Flow

- [ ] Auto-send routinely reply bhej raha hai? `send_attempts` table me status check
- [ ] Gmail reject ho (rate limit/blocked) → `GmailSendRejected` handling, "unknown" state me NA phek tal
- [ ] Ek ticket pe double-send na ho (same thread me duplicate reply)
- [ ] Jaise token expired ho, send… kaunsa message dikhata hai operator ko?

Puchne layak question: *"rejected/unknown send cases me ticket kis status me jaata hai?"*

## 5. Fake/Test Data Pollution (aaj ka bug — aisi future me hua to)

- [ ] Tests `@harborandpine.test` email ke fake accounts DB na chhore — `tests/conftest.py` cleanup fixture chalu?
- [ ] Tests aise chalaye: `& .venv\Scripts\python.exe -m pytest tests/ -q` (aksar `python -m pytest` pure system env/pak use kare to hang ho sakta hai; timeout ka bhi dhyan)
- [ ] Nayan DB me `gmail_accounts` count = **1** (sirf real), tests ke baad bhi

Puchne layak question: *"tests ne DB pollution kia? `gmail_accounts` me count kitna hai?"*

## 6. Dashboard / UI

- [ ] Login (`admin` / password works) → script ka route `admin@...`/`password` padding check (`.env` me `email=admin` `password=admin1234@@@`)
- [ ] Tickets list live update ho (poll ke baad bina reload ke)
- [ ] Chinese/RTL/long email ne UI break š te (long subject line, emoji, zyada im dage kad m)
- [ ] Network fail/error pe UI ne breaking error toast dikha, blank screen NAHI
- [ ] CORS localhost dev pe sahi (`CORS_ORIGINS=http://localhost:5173`)

Puchne layak question: *"UI ko worst-case data do break karke batao"* (≤: long names, 0 emails, emoji, extreme values)

## 7. Infra / DB (Neon)

- [ ] Churning after restart: server start → seed from `.env` (`GOOGLE_REFRESH_TOKEN`) no duplication
- [ ] `GOOGLE_TOKEN_ENCRYPTION_KEY` agar change kiya, existing encrypted tokens invalid ho jayenge — key change karne ke pehle intent karna (old key from tokens re-encrypt / re-seed karke)
- [ ] `.env` value me extra space mat: `DATABASE_URL=⎵postgresql://...` — agar dotenv strip kar b de ye risky padta hai, kaan ke aage remove kar space
- [ ] Neon secrets `.env` me hi rakhte hian, repo me push nahi (`.gitignore` check)

Puchne layak question: *"encryption key rotate karke turant tokens ko superstale to nahi? re-encryption plan batao"*

---

## Quick Sanity Commands

```powershell
# DB me current state (Neon console SQL editor me bhi chalega)
#   SELECT email, status FROM gmail_accounts;
#   SELECT status, count(*) FROM jobs GROUP BY status;   -- dead = problem
#   SELECT status, count(*) FROM send_attempts GROUP BY status;

# Server
& .venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Tests (venv se hi chalao)
& .venv\Scripts\python.exe -m pytest tests/ -q
```
