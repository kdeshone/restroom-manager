# 🚻 Restroom Management System
### Multi-teacher, cloud-hosted, fully secure

---

## What This App Does

- Students scan a **barcode** or tap an **NFC card** to check in/out of the restroom
- Live display shows who's out — **green** under 5 min, **red + flashing** over 5 min
- Automatically tracks **violations**, **probation**, **passes**, and **point deductions**
- Generates **parent notification messages** for strikes
- Identifies students eligible for **extra credit** at grading period end
- Each teacher has their **own secure login** — rosters are completely isolated
- All student names are stored in a **private, encrypted Supabase database**

---

## Setup Guide (One-Time, ~15 Minutes)

### STEP 1 — Create a Free Supabase Account

1. Go to **https://supabase.com** and click **Start for Free**
2. Sign up with GitHub or email
3. Click **New Project**, give it a name like `restroom-manager`
4. Set a strong database password (save it somewhere safe)
5. Wait ~2 minutes for the project to spin up

### STEP 2 — Create the Database Tables

1. In your Supabase project, click **SQL Editor** in the left sidebar
2. Click **New Query**
3. Open the file `supabase_setup.sql` from this folder
4. Copy all the contents and paste them into the SQL editor
5. Click **Run** (green button)
6. You should see "Success. No rows returned."

### STEP 3 — Get Your Supabase Credentials

1. In Supabase, go to **Project Settings → API**
2. Copy:
   - **Project URL** (looks like `https://abc123.supabase.co`)
   - **anon / public key** (long string starting with `eyJ...`)

### STEP 4 — Create a Free GitHub Repository

1. Go to **https://github.com** (create a free account if needed)
2. Click **New Repository**, name it `restroom-manager`, set to **Private**
3. Upload these files to the repository:
   - `app.py`
   - `requirements.txt`
   - `supabase_setup.sql` (optional, just for your records)

   > **DO NOT upload** `.streamlit/secrets.toml` — this contains private keys!

### STEP 5 — Deploy on Streamlit Cloud (Free)

1. Go to **https://share.streamlit.io** and sign in with GitHub
2. Click **New App**
3. Select your `restroom-manager` repository
4. Set **Main file path** to `app.py`
5. Click **Advanced Settings → Secrets**
6. Paste this (replacing with your real values from Step 3):

```toml
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_KEY = "your-anon-public-key-here"
```

7. Click **Deploy!**
8. In ~1 minute you'll have a live URL like `https://yourname-restroom-manager.streamlit.app`

---

## First-Time Use

1. Open your app URL
2. Click **Create Account** to register yourself as a teacher
3. Each of the 3 teachers does the same — everyone creates their own account
4. Add students under **Roster** — you'll need each student's barcode/NFC code
5. Start scanning!

---

## How Scanning Works

- **First scan** → student is checked IN, timer starts
- **Second scan** → student is checked OUT, timer stops
- If they were out **more than 5 minutes** → violation recorded, parent message generated
- If a student has **no passes left**, the scan is rejected with a message

---

## Policy Rules (Configurable in app.py)

| Setting | Default |
|---|---|
| Max restroom time | 5 minutes |
| Violations before probation | 2 |
| Probation length | 1 week |
| Passes per cycle | 3 |
| Pass cycle length | 3 weeks |
| Probation auto-deduction | 3 points |
| Restroom use on probation | 2 points |

To change any of these, open `app.py` and edit the constants at the top.

---

## Security Notes

- Passwords are **bcrypt-hashed** — no plain text passwords stored anywhere
- Each teacher's students are **isolated** — Teacher A cannot see Teacher B's roster
- Supabase uses **encrypted PostgreSQL** with SSL
- Student data never leaves Supabase
- The app URL can be kept private — only share it with your teachers

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "No student found with code" | Check the barcode/NFC value matches what was entered in the roster |
| App crashes on startup | Double-check your `secrets.toml` values in Streamlit Cloud |
| Can't connect to database | Verify your Supabase project is active (free tier sleeps after inactivity) |
| Student still showing as active after timeout | Use the Scan page to manually check them out by scanning again |

---

## Questions?
Share your app URL with your 3 teachers and have them create accounts. Each account is fully independent.
