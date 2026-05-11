"""
Restroom Management System
Multi-teacher, Supabase-backed, bcrypt-secured Streamlit app.
"""

import streamlit as st
import bcrypt
import pandas as pd
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
import time
import os

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
VIOLATION_MINUTES       = 5
PROBATION_VIOLATIONS    = 2
PROBATION_WEEKS         = 1
PASSES_PER_CYCLE        = 3
PASS_CYCLE_WEEKS        = 3
PROBATION_AUTO_PTS      = 3
PROBATION_USE_PTS       = 2

st.set_page_config(
    page_title="Restroom Manager",
    page_icon="🚻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CUSTOM CSS  (clean school-admin aesthetic)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* ── page background ── */
.stApp { background: #0f1117; color: #e8eaf0; }

/* ── sidebar ── */
section[data-testid="stSidebar"] {
    background: #161b27;
    border-right: 1px solid #252d3d;
}
section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: transparent;
    border: 1px solid #2e3a52;
    color: #a0aec0;
    border-radius: 8px;
    font-size: 0.85rem;
    margin-bottom: 4px;
    transition: all .2s;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #1e2a3e;
    border-color: #4a90e2;
    color: #fff;
}

/* ── metric cards ── */
.metric-card {
    background: #161b27;
    border: 1px solid #252d3d;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    text-align: center;
}
.metric-card .num { font-size: 2rem; font-weight: 700; color: #4a90e2; }
.metric-card .lbl { font-size: 0.78rem; color: #6b7a99; text-transform: uppercase; letter-spacing: .08em; }

/* ── live-status cards ── */
.student-card {
    border-radius: 12px;
    padding: 1rem 1.4rem;
    margin-bottom: .75rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: 'DM Mono', monospace;
    font-size: 1rem;
    font-weight: 500;
    animation: fadeIn .4s ease;
}
.student-card.green {
    background: #0d2818;
    border: 1.5px solid #1a7a3e;
    color: #4ade80;
}
.student-card.red {
    background: #2a0d0d;
    border: 1.5px solid #7a1a1a;
    color: #f87171;
    animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
    0%,100% { opacity: 1; }
    50%      { opacity: 0.55; }
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── section headers ── */
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #c5cfe8;
    border-bottom: 1px solid #252d3d;
    padding-bottom: .5rem;
    margin-bottom: 1rem;
}

/* ── tables ── */
.dataframe thead th { background:#161b27 !important; color:#6b7a99 !important; font-size:.8rem; }
.dataframe tbody td { background:#0f1117 !important; color:#c5cfe8 !important; font-size:.85rem; }

/* ── login card ── */
.login-wrap {
    max-width: 400px;
    margin: 6vh auto 0;
    background: #161b27;
    border: 1px solid #252d3d;
    border-radius: 16px;
    padding: 2.5rem 2rem;
}
.login-title {
    text-align: center;
    font-size: 1.5rem;
    font-weight: 700;
    color: #e8eaf0;
    margin-bottom: .25rem;
}
.login-sub {
    text-align: center;
    font-size: .85rem;
    color: #6b7a99;
    margin-bottom: 1.8rem;
}

/* ── primary button ── */
.stButton > button[kind="primary"] {
    background: #4a90e2 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
    background: #3478c9 !important;
}

/* ── badge ── */
.badge {
    display:inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: .75rem;
    font-weight: 600;
}
.badge.prob  { background:#7a1a1a; color:#fca5a5; }
.badge.ok    { background:#0d2818; color:#4ade80; }
.badge.warn  { background:#3a2a00; color:#fbbf24; }

/* ── scan input glow ── */
input[data-testid="stTextInput"] {
    background: #1a2133 !important;
    border: 1.5px solid #2e3a52 !important;
    color: #e8eaf0 !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 1.1rem !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SUPABASE CONNECTION
# ─────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()


# ─────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())

def login(username: str, password: str):
    res = supabase.table("teachers").select("*").eq("username", username).execute()
    if not res.data:
        return None
    teacher = res.data[0]
    if verify_password(password, teacher["password_hash"]):
        return teacher
    return None

def register_teacher(username, password, full_name, email=""):
    existing = supabase.table("teachers").select("id").eq("username", username).execute()
    if existing.data:
        return False, "Username already exists."
    pw_hash = hash_password(password)
    supabase.table("teachers").insert({
        "username": username,
        "password_hash": pw_hash,
        "full_name": full_name,
        "email": email
    }).execute()
    return True, "Account created!"


# ─────────────────────────────────────────────
# STUDENT HELPERS
# ─────────────────────────────────────────────
def get_students(teacher_id):
    res = supabase.table("students").select("*").eq("teacher_id", teacher_id).order("full_name").execute()
    return res.data or []

def get_student_by_code(teacher_id, code):
    res = supabase.table("students").select("*").eq("teacher_id", teacher_id).eq("student_code", code.strip()).execute()
    return res.data[0] if res.data else None

def add_student(teacher_id, code, name, parent_email):
    supabase.table("students").insert({
        "teacher_id": teacher_id,
        "student_code": code.strip(),
        "full_name": name.strip(),
        "parent_email": parent_email.strip() if parent_email else None
    }).execute()

def update_student(student_id, updates: dict):
    supabase.table("students").update(updates).eq("id", student_id).execute()

def delete_student(student_id):
    supabase.table("students").delete().eq("id", student_id).execute()


# ─────────────────────────────────────────────
# ACTIVE RESTROOM HELPERS
# ─────────────────────────────────────────────
def get_active_users(teacher_id):
    res = (supabase.table("active_restroom_users")
           .select("*, students(full_name, on_probation, violations)")
           .eq("teacher_id", teacher_id)
           .execute())
    return res.data or []

def is_student_active(student_id):
    res = supabase.table("active_restroom_users").select("id").eq("student_id", student_id).execute()
    return bool(res.data)

def check_in(teacher_id, student_id):
    supabase.table("active_restroom_users").insert({
        "teacher_id": teacher_id,
        "student_id": student_id,
        "check_in_time": datetime.now(timezone.utc).isoformat()
    }).execute()

def check_out(teacher_id, student_id) -> dict:
    """Remove from active, create visit record, run policy logic. Returns visit dict."""
    res = supabase.table("active_restroom_users").select("*").eq("student_id", student_id).execute()
    if not res.data:
        return None
    active = res.data[0]
    check_in_dt = datetime.fromisoformat(active["check_in_time"])
    check_out_dt = datetime.now(timezone.utc)
    duration = (check_out_dt - check_in_dt).total_seconds() / 60

    # Insert visit log
    visit_res = supabase.table("restroom_visits").insert({
        "student_id": student_id,
        "teacher_id": teacher_id,
        "check_in_time": check_in_dt.isoformat(),
        "check_out_time": check_out_dt.isoformat(),
        "duration_minutes": round(duration, 2),
        "violation_triggered": duration > VIOLATION_MINUTES
    }).execute()
    visit_id = visit_res.data[0]["id"] if visit_res.data else None

    # Remove from active
    supabase.table("active_restroom_users").delete().eq("student_id", student_id).execute()

    # Apply policy
    apply_policy(teacher_id, student_id, duration, visit_id)

    return {"duration": duration, "violation": duration > VIOLATION_MINUTES}


# ─────────────────────────────────────────────
# POLICY ENGINE
# ─────────────────────────────────────────────
def apply_policy(teacher_id, student_id, duration_minutes, visit_id):
    s_res = supabase.table("students").select("*").eq("id", student_id).execute()
    if not s_res.data:
        return
    s = s_res.data[0]
    updates = {}

    # ── Pass cycle reset ──
    cycle_start = datetime.fromisoformat(s["cycle_start_date"]).replace(tzinfo=timezone.utc) \
        if s["cycle_start_date"] else datetime.now(timezone.utc)
    weeks_elapsed = (datetime.now(timezone.utc) - cycle_start).days / 7
    if weeks_elapsed >= PASS_CYCLE_WEEKS:
        updates["passes_used_current_cycle"] = 0
        updates["cycle_start_date"] = datetime.now(timezone.utc).date().isoformat()

    # ── Probation expiry ──
    if s["on_probation"] and s["probation_end_date"]:
        prob_end = datetime.fromisoformat(s["probation_end_date"]).replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > prob_end:
            updates["on_probation"] = False
            updates["probation_end_date"] = None
            updates["violations"] = 0

    # ── Count pass ──
    updates["passes_used_current_cycle"] = (updates.get("passes_used_current_cycle")
                                            or s["passes_used_current_cycle"]) + 1

    # ── Violation ──
    if duration_minutes > VIOLATION_MINUTES:
        new_violations = s["violations"] + 1
        updates["violations"] = new_violations

        # Strike / parent notification
        if s.get("parent_email"):
            msg = build_parent_message(s["full_name"], duration_minutes, new_violations)
            supabase.table("strikes").insert({
                "student_id": student_id,
                "teacher_id": teacher_id,
                "visit_id": visit_id,
                "parent_email": s["parent_email"],
                "notification_message": msg
            }).execute()

        # Probation trigger
        if not s["on_probation"] and new_violations >= PROBATION_VIOLATIONS:
            updates["on_probation"] = True
            updates["probation_end_date"] = (
                datetime.now(timezone.utc) + timedelta(weeks=PROBATION_WEEKS)
            ).isoformat()
            updates["points_deducted"] = s["points_deducted"] + PROBATION_AUTO_PTS

    # ── Points deduction while on probation ──
    is_on_probation = updates.get("on_probation", s["on_probation"])
    if is_on_probation:
        updates["points_deducted"] = (updates.get("points_deducted") or s["points_deducted"]) + PROBATION_USE_PTS

    if updates:
        supabase.table("students").update(updates).eq("id", student_id).execute()


def build_parent_message(name, duration, violation_count):
    return (
        f"Dear Parent/Guardian,\n\n"
        f"This message is to inform you that {name} has received a restroom strike for exceeding "
        f"the {VIOLATION_MINUTES}-minute restroom limit. They were out for {duration:.1f} minutes "
        f"(Strike #{violation_count}).\n\n"
        f"{'If they receive one more violation, they will be placed on a one-week probationary period ' + chr(10) + 'that includes point deductions.' if violation_count < PROBATION_VIOLATIONS else name + ' has been placed on a one-week probationary period with point deductions.'}\n\n"
        f"Please speak with your student about the importance of following restroom policy.\n\n"
        f"Sincerely,\nSchool Administration"
    )


# ─────────────────────────────────────────────
# PASS / EXTRA CREDIT HELPERS
# ─────────────────────────────────────────────
def get_extra_credit_students(teacher_id):
    """Students who have passes left at end of grading period."""
    students = get_students(teacher_id)
    return [s for s in students if s["passes_used_current_cycle"] < PASSES_PER_CYCLE]

def reset_all_passes(teacher_id):
    supabase.table("students").update({
        "passes_used_current_cycle": 0,
        "cycle_start_date": datetime.now(timezone.utc).date().isoformat()
    }).eq("teacher_id", teacher_id).execute()


# ─────────────────────────────────────────────
# UI: LOGIN PAGE
# ─────────────────────────────────────────────
def show_login():
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">🚻 Restroom Manager</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Sign in to your teacher account</div>', unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Sign In", type="primary", use_container_width=True):
            teacher = login(username, password)
            if teacher:
                st.session_state.teacher = teacher
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab_register:
        st.caption("First-time setup: create your teacher account.")
        r_name     = st.text_input("Full Name",    key="reg_name")
        r_email    = st.text_input("Email (optional)", key="reg_email")
        r_user     = st.text_input("Choose Username", key="reg_user")
        r_pass     = st.text_input("Choose Password", type="password", key="reg_pass")
        r_pass2    = st.text_input("Confirm Password", type="password", key="reg_pass2")
        if st.button("Create Account", type="primary", use_container_width=True):
            if not r_name or not r_user or not r_pass:
                st.error("Name, username, and password are required.")
            elif r_pass != r_pass2:
                st.error("Passwords do not match.")
            elif len(r_pass) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                ok, msg = register_teacher(r_user, r_pass, r_name, r_email)
                if ok:
                    st.success(msg + " Please sign in.")
                else:
                    st.error(msg)

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# UI: LIVE RESTROOM DISPLAY
# ─────────────────────────────────────────────
def show_live_display(teacher_id):
    st.markdown('<div class="section-header">🟢 Live Restroom Status</div>', unsafe_allow_html=True)
    active = get_active_users(teacher_id)

    if not active:
        st.info("No students are currently in the restroom.")
    else:
        now = datetime.now(timezone.utc)
        for row in active:
            check_in_dt = datetime.fromisoformat(row["check_in_time"]).replace(tzinfo=timezone.utc)
            elapsed = (now - check_in_dt).total_seconds() / 60
            name = row["students"]["full_name"]
            css_class = "red" if elapsed >= VIOLATION_MINUTES else "green"
            icon = "🔴" if elapsed >= VIOLATION_MINUTES else "🟢"
            st.markdown(
                f'<div class="student-card {css_class}">'
                f'<span>{icon} {name}</span>'
                f'<span>{elapsed:.1f} min out</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.caption("Page auto-refreshes every 30 seconds. You can also manually refresh.")

    if st.button("🔄 Refresh Display"):
        st.rerun()

    # Auto-refresh every 30s using Streamlit's experimental rerun
    time.sleep(0)
    st.markdown("""
    <script>
    setTimeout(function(){ window.location.reload(); }, 30000);
    </script>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# UI: SCAN / CHECK-IN PAGE
# ─────────────────────────────────────────────
def show_scan_page(teacher_id):
    st.markdown('<div class="section-header">📷 Scan Barcode / Tap NFC</div>', unsafe_allow_html=True)
    st.caption("Focus this field and scan the barcode or tap the NFC card.")

    scan_val = st.text_input("Student ID / Barcode", key="scan_input", placeholder="Scan or type student code…")

    if st.button("Process Scan", type="primary") and scan_val:
        student = get_student_by_code(teacher_id, scan_val)
        if not student:
            st.error(f"No student found with code: **{scan_val}**")
        else:
            name = student["full_name"]
            sid = student["id"]

            if is_student_active(sid):
                # ── CHECK OUT ──
                result = check_out(teacher_id, sid)
                dur = result["duration"]
                if result["violation"]:
                    st.error(
                        f"⚠️ **{name}** checked out after **{dur:.1f} min** — VIOLATION recorded. "
                        f"({'Parent notified.' if student['parent_email'] else 'No parent email on file.'})"
                    )
                else:
                    st.success(f"✅ **{name}** checked out. Time: {dur:.1f} min. All good!")
            else:
                # ── CHECK IN ──
                # Pass limit check
                passes_left = PASSES_PER_CYCLE - student["passes_used_current_cycle"]
                if passes_left <= 0 and not student["on_probation"]:
                    st.warning(f"🚫 **{name}** has used all {PASSES_PER_CYCLE} passes this cycle.")
                else:
                    check_in(teacher_id, sid)
                    prob_note = " ⚠️ *On probation — points will be deducted.*" if student["on_probation"] else ""
                    st.success(f"🚽 **{name}** checked IN. Passes left: {max(passes_left-1,0)}.{prob_note}")

        st.rerun()

    # Show live status below scan
    st.divider()
    show_live_display(teacher_id)


# ─────────────────────────────────────────────
# UI: ROSTER MANAGEMENT
# ─────────────────────────────────────────────
def show_roster(teacher_id):
    st.markdown('<div class="section-header">👥 Student Roster</div>', unsafe_allow_html=True)

    with st.expander("➕ Add New Student"):
        c1, c2 = st.columns(2)
        new_code  = c1.text_input("Barcode / NFC Code", key="new_code")
        new_name  = c2.text_input("Full Name", key="new_name")
        new_email = st.text_input("Parent Email (optional)", key="new_email")
        if st.button("Add Student", type="primary"):
            if not new_code or not new_name:
                st.error("Code and name are required.")
            else:
                try:
                    add_student(teacher_id, new_code, new_name, new_email)
                    st.success(f"Added {new_name}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    students = get_students(teacher_id)
    if not students:
        st.info("No students yet. Add one above.")
        return

    # Build display table
    rows = []
    for s in students:
        status = "🔴 Probation" if s["on_probation"] else "🟡 Warning" if s["violations"] >= 1 else "🟢 OK"
        passes_left = max(0, PASSES_PER_CYCLE - s["passes_used_current_cycle"])
        rows.append({
            "Name": s["full_name"],
            "Code": s["student_code"],
            "Status": status,
            "Violations": s["violations"],
            "Passes Left": passes_left,
            "Pts Deducted": s["points_deducted"],
            "Parent Email": s["parent_email"] or "—",
            "ID": s["id"]
        })
    df = pd.DataFrame(rows)

    # Filters
    fc1, fc2 = st.columns(2)
    filter_prob = fc1.checkbox("Show probation only")
    filter_warn = fc2.checkbox("Show violations only")
    if filter_prob:
        df = df[df["Status"].str.contains("Probation")]
    elif filter_warn:
        df = df[df["Violations"] > 0]

    st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

    # Edit / Delete
    with st.expander("✏️ Edit or Remove a Student"):
        student_names = {s["full_name"]: s for s in students}
        sel_name = st.selectbox("Select student", list(student_names.keys()))
        if sel_name:
            sel_s = student_names[sel_name]
            e1, e2 = st.columns(2)
            edit_name  = e1.text_input("Full Name",   value=sel_s["full_name"],    key="edit_name")
            edit_code  = e2.text_input("Code",        value=sel_s["student_code"], key="edit_code")
            edit_email = st.text_input("Parent Email", value=sel_s["parent_email"] or "", key="edit_email")
            col_save, col_del = st.columns(2)
            if col_save.button("💾 Save Changes"):
                update_student(sel_s["id"], {
                    "full_name": edit_name,
                    "student_code": edit_code,
                    "parent_email": edit_email or None
                })
                st.success("Updated.")
                st.rerun()
            if col_del.button("🗑️ Delete Student", type="primary"):
                delete_student(sel_s["id"])
                st.success(f"{sel_name} removed.")
                st.rerun()


# ─────────────────────────────────────────────
# UI: VISIT LOG / HALL PASS HISTORY
# ─────────────────────────────────────────────
def show_visit_log(teacher_id):
    st.markdown('<div class="section-header">📋 Visit History</div>', unsafe_allow_html=True)

    res = (supabase.table("restroom_visits")
           .select("*, students(full_name)")
           .eq("teacher_id", teacher_id)
           .order("check_in_time", desc=True)
           .limit(200)
           .execute())
    visits = res.data or []

    if not visits:
        st.info("No visits recorded yet.")
        return

    rows = []
    for v in visits:
        rows.append({
            "Student": v["students"]["full_name"] if v.get("students") else "Unknown",
            "Check In":  v["check_in_time"][:16].replace("T", " "),
            "Check Out": v["check_out_time"][:16].replace("T", " ") if v["check_out_time"] else "Active",
            "Duration":  f"{v['duration_minutes']:.1f} min" if v["duration_minutes"] else "—",
            "Violation": "⚠️ YES" if v["violation_triggered"] else "✅ No"
        })
    df = pd.DataFrame(rows)

    violations_only = st.checkbox("Show violations only")
    if violations_only:
        df = df[df["Violation"].str.contains("YES")]

    st.dataframe(df, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# UI: STRIKE LIST & NOTIFICATIONS
# ─────────────────────────────────────────────
def show_strikes(teacher_id):
    st.markdown('<div class="section-header">⚠️ Strike List & Parent Notifications</div>', unsafe_allow_html=True)

    res = (supabase.table("strikes")
           .select("*, students(full_name)")
           .eq("teacher_id", teacher_id)
           .order("created_at", desc=True)
           .execute())
    strikes = res.data or []

    if not strikes:
        st.info("No strikes on record. Great class! 🎉")
        return

    for s in strikes:
        name = s["students"]["full_name"] if s.get("students") else "Unknown"
        ts   = s["created_at"][:16].replace("T", " ")
        with st.expander(f"⚠️ {name} — {ts}"):
            st.caption(f"Parent email: {s['parent_email'] or 'N/A'}")
            st.code(s["notification_message"], language=None)


# ─────────────────────────────────────────────
# UI: EXTRA CREDIT & REPORTS
# ─────────────────────────────────────────────
def show_reports(teacher_id):
    st.markdown('<div class="section-header">📊 Reports & Extra Credit</div>', unsafe_allow_html=True)

    tab_ec, tab_prob, tab_summary = st.tabs(["Extra Credit", "Probation List", "Class Summary"])

    with tab_ec:
        st.markdown("Students who have **not used all passes** this cycle (eligible for extra credit):")
        ec_students = get_extra_credit_students(teacher_id)
        if not ec_students:
            st.info("No students eligible yet, or all passes have been used.")
        else:
            rows = [{"Name": s["full_name"], "Passes Used": s["passes_used_current_cycle"],
                     "Passes Remaining": PASSES_PER_CYCLE - s["passes_used_current_cycle"]} for s in ec_students]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.divider()
        if st.button("🔄 Reset All Pass Counts (new grading period)"):
            reset_all_passes(teacher_id)
            st.success("All pass counts reset. New cycle started.")

    with tab_prob:
        students = get_students(teacher_id)
        prob = [s for s in students if s["on_probation"]]
        if not prob:
            st.info("No students currently on probation.")
        else:
            rows = []
            for s in prob:
                end = s["probation_end_date"][:10] if s["probation_end_date"] else "—"
                rows.append({"Name": s["full_name"], "Pts Deducted": s["points_deducted"],
                              "Probation Until": end})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab_summary:
        students = get_students(teacher_id)
        if not students:
            st.info("No students on roster.")
            return
        total = len(students)
        prob_count = sum(1 for s in students if s["on_probation"])
        violation_count = sum(1 for s in students if s["violations"] > 0)
        passes_left = sum(max(0, PASSES_PER_CYCLE - s["passes_used_current_cycle"]) for s in students)

        c1, c2, c3, c4 = st.columns(4)
        for col, num, lbl in [
            (c1, total,           "Total Students"),
            (c2, prob_count,      "On Probation"),
            (c3, violation_count, "Have Violations"),
            (c4, passes_left,     "Passes Remaining (class total)")
        ]:
            col.markdown(f'<div class="metric-card"><div class="num">{num}</div><div class="lbl">{lbl}</div></div>',
                         unsafe_allow_html=True)


# ─────────────────────────────────────────────
# UI: SIDEBAR & NAV
# ─────────────────────────────────────────────
def show_sidebar(teacher):
    with st.sidebar:
        st.markdown(f"### 👋 {teacher['full_name']}")
        st.caption(f"@{teacher['username']}")
        st.divider()

        pages = {
            "📷 Scan / Check In":    "scan",
            "🟢 Live Display":       "live",
            "👥 Roster":             "roster",
            "📋 Visit History":      "log",
            "⚠️ Strikes":           "strikes",
            "📊 Reports":            "reports",
        }
        if "page" not in st.session_state:
            st.session_state.page = "scan"

        for label, key in pages.items():
            if st.button(label, key=f"nav_{key}"):
                st.session_state.page = key
                st.rerun()

        st.divider()
        if st.button("🚪 Sign Out"):
            del st.session_state.teacher
            st.rerun()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    if "teacher" not in st.session_state:
        show_login()
        return

    teacher = st.session_state.teacher
    tid     = teacher["id"]

    show_sidebar(teacher)

    page = st.session_state.get("page", "scan")

    if page == "scan":
        show_scan_page(tid)
    elif page == "live":
        show_live_display(tid)
    elif page == "roster":
        show_roster(tid)
    elif page == "log":
        show_visit_log(tid)
    elif page == "strikes":
        show_strikes(tid)
    elif page == "reports":
        show_reports(tid)


if __name__ == "__main__":
    main()
