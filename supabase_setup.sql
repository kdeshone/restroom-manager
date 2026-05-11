-- ============================================================
-- RESTROOM MANAGEMENT SYSTEM - Supabase Database Setup
-- Run this entire file in your Supabase SQL Editor (one time)
-- ============================================================

-- 1. TEACHERS TABLE
CREATE TABLE IF NOT EXISTS teachers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. STUDENTS TABLE
CREATE TABLE IF NOT EXISTS students (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    teacher_id UUID REFERENCES teachers(id) ON DELETE CASCADE,
    student_code TEXT NOT NULL,
    full_name TEXT NOT NULL,
    parent_email TEXT,
    violations INTEGER DEFAULT 0,
    on_probation BOOLEAN DEFAULT FALSE,
    probation_end_date TIMESTAMPTZ,
    points_deducted INTEGER DEFAULT 0,
    passes_used_current_cycle INTEGER DEFAULT 0,
    last_pass_reset_date DATE DEFAULT CURRENT_DATE,
    cycle_start_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(teacher_id, student_code)
);

-- 3. RESTROOM VISITS TABLE
CREATE TABLE IF NOT EXISTS restroom_visits (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    teacher_id UUID REFERENCES teachers(id) ON DELETE CASCADE,
    check_in_time TIMESTAMPTZ NOT NULL,
    check_out_time TIMESTAMPTZ,
    duration_minutes FLOAT,
    violation_triggered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. STRIKE LIST TABLE
CREATE TABLE IF NOT EXISTS strikes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    teacher_id UUID REFERENCES teachers(id) ON DELETE CASCADE,
    visit_id UUID REFERENCES restroom_visits(id) ON DELETE CASCADE,
    parent_email TEXT,
    notification_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. ACTIVE USERS TABLE (who is currently in restroom)
CREATE TABLE IF NOT EXISTS active_restroom_users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE UNIQUE,
    teacher_id UUID REFERENCES teachers(id) ON DELETE CASCADE,
    check_in_time TIMESTAMPTZ NOT NULL
);

-- 6. INDEXES for performance
CREATE INDEX IF NOT EXISTS idx_students_teacher ON students(teacher_id);
CREATE INDEX IF NOT EXISTS idx_students_code ON students(student_code);
CREATE INDEX IF NOT EXISTS idx_visits_student ON restroom_visits(student_id);
CREATE INDEX IF NOT EXISTS idx_visits_teacher ON restroom_visits(teacher_id);
CREATE INDEX IF NOT EXISTS idx_active_teacher ON active_restroom_users(teacher_id);
