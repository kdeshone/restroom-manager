"""
Streamlit web application for Restroom Management System
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from restroom_system import RestroomManagementSystem, Config

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="🚽 Restroom Management System",
    page_icon="🚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== SESSION STATE INITIALIZATION ====================
if 'system' not in st.session_state:
    st.session_state.system = RestroomManagementSystem()

if 'scan_message' not in st.session_state:
    st.session_state.scan_message = None


# ==================== UTILITY FUNCTIONS ====================
def format_duration(minutes: float) -> str:
    """Format duration in minutes to readable string"""
    return f"{minutes:.1f} minutes"


def get_status_color(minutes: float) -> str:
    """Get color based on violation threshold"""
    if minutes > Config.VIOLATION_THRESHOLD_MINUTES:
        return "🔴"
    else:
        return "🟢"


def render_active_users():
    """Render currently active students in restroom"""
    active_visits = st.session_state.system.logs.get_active_visits()
    
    if not active_visits:
        st.info("✅ No students currently in the restroom")
        return
    
    st.subheader("📍 Currently in Restroom")
    
    cols = st.columns(1)
    for student_id, visit in active_visits.items():
        student = st.session_state.system.students.get_student(student_id)
        elapsed = (datetime.now() - visit.check_in_time).total_seconds() / 60
        color = get_status_color(elapsed)
        
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"{color} **{student.name}**")
            with col2:
                st.write(f"⏱️ {format_duration(elapsed)}")
            with col3:
                if elapsed > Config.VIOLATION_THRESHOLD_MINUTES:
                    st.write("⚠️ Over time")


# ==================== MAIN APP ====================
def main():
    st.title("🏫 Restroom Management System")
    st.markdown("---")
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🎫 Student Scan", "📊 Teacher Dashboard", "⚙️ Settings"])
    
    # ==================== STUDENT TAB ====================
    with tab1:
        st.header("Student Check-In/Out")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            student_id = st.text_input(
                "Scan Barcode / Enter Student ID:",
                placeholder="Enter or scan ID...",
                key="student_scan"
            )
        
        with col2:
            scan_button = st.button("🔍 Process Scan", use_container_width=True)
        
        if scan_button and student_id:
            result = st.session_state.system.handle_scan(student_id)
            
            if result['success']:
                st.success(result['message'])
                st.balloons()
            else:
                st.error(result['message'])
            
            # Clear input
            st.rerun()
        
        # Display active students
        st.markdown("---")
        render_active_users()
        
        # Recent activity
        st.markdown("---")
        st.subheader("📋 Recent Activity")
        all_logs = st.session_state.system.logs.get_logs()
        
        if all_logs:
            recent_logs = all_logs[-10:]  # Last 10
            log_data = []
            for log in reversed(recent_logs):
                student = st.session_state.system.students.get_student(log.student_id)
                log_data.append({
                    'Student': student.name if student else 'Unknown',
                    'Check-In': log.check_in_time.strftime('%H:%M:%S'),
                    'Check-Out': log.check_out_time.strftime('%H:%M:%S') if log.check_out_time else 'Active',
                    'Duration': format_duration(log.duration_minutes),
                    'Status': '⚠️ Violation' if log.violation_triggered else '✅ OK'
                })
            
            st.dataframe(pd.DataFrame(log_data), use_container_width=True)
        else:
            st.info("No activity yet")
    
    # ==================== TEACHER TAB ====================
    with tab2:
        st.header("Teacher Dashboard")
        
        # Authentication
        password = st.sidebar.text_input("Enter Teacher Password:", type="password")
        
        if password != "teacher123":
            st.warning("⛔ Please enter the correct password in the sidebar to access the dashboard")
            return
        
        # Dashboard tabs
        dash_tab1, dash_tab2, dash_tab3, dash_tab4 = st.tabs(
            ["📈 Overview", "👥 Students", "📋 Logs", "⚠️ Violations"]
        )
        
        with dash_tab1:
            st.subheader("System Overview")
            
            dashboard_data = st.session_state.system.get_dashboard_data()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Students",
                    len(dashboard_data['all_students']),
                    help="Total number of students in the system"
                )
            
            with col2:
                st.metric(
                    "Active Now",
                    len(dashboard_data['active_users']),
                    help="Students currently in restroom"
                )
            
            with col3:
                st.metric(
                    "On Probation",
                    len(dashboard_data['deduction_list']),
                    help="Students currently on probation"
                )
            
            with col4:
                st.metric(
                    "Violations Today",
                    len([s for s in dashboard_data['strike_list'] if s['timestamp'].date() == datetime.now().date()]),
                    help="Violations recorded today"
                )
            
            # Current activity
            st.subheader("Current Activity")
            render_active_users()
        
        with dash_tab2:
            st.subheader("Student Management")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("### Add Student")
                new_id = st.text_input("Student ID (Barcode/NFC):")
                new_name = st.text_input("Student Name:")
                new_email = st.text_input("Parent Email:")
                
                if st.button("➕ Add Student", use_container_width=True):
                    if st.session_state.system.students.add_student(new_id, new_name, new_email):
                        st.success(f"✅ Added {new_name}")
                        st.rerun()
                    else:
                        st.error("❌ Student ID already exists")
            
            with col2:
                st.write("### Quick Search")
                search_id = st.text_input("Search by Student ID:")
                
                if search_id:
                    student = st.session_state.system.students.get_student(search_id)
                    if student:
                        st.write(f"**Name:** {student.name}")
                        st.write(f"**Email:** {student.parent_email or 'N/A'}")
                        st.write(f"**Violations:** {student.violations}")
                        st.write(f"**On Probation:** {'Yes' if student.on_probation else 'No'}")
                        st.write(f"**Passes Used:** {student.passes_used_current_cycle}/{Config.PASSES_PER_CYCLE}")
                        
                        if st.button("🗑️ Delete Student"):
                            if st.session_state.system.students.delete_student(search_id):
                                st.success("✅ Student deleted")
                                st.rerun()
                    else:
                        st.error("❌ Student not found")
            
            # All students table
            st.write("### All Students")
            all_students = st.session_state.system.students.get_all_students()
            
            if all_students:
                student_data = []
                for sid, student in all_students.items():
                    student_data.append({
                        'ID': sid,
                        'Name': student.name,
                        'Violations': student.violations,
                        'On Probation': '⚠️ Yes' if student.on_probation else '✅ No',
                        'Passes Used': f"{student.passes_used_current_cycle}/{Config.PASSES_PER_CYCLE}",
                        'Email': student.parent_email or 'N/A'
                    })
                
                st.dataframe(pd.DataFrame(student_data), use_container_width=True)
        
        with dash_tab3:
            st.subheader("Restroom Visit Logs")
            
            # Filter options
            col1, col2 = st.columns(2)
            
            with col1:
                filter_type = st.radio("Filter by:", ["All", "Student ID"], horizontal=True)
            
            if filter_type == "Student ID":
                with col2:
                    filter_id = st.text_input("Enter Student ID:")
                    logs = st.session_state.system.logs.get_logs(filter_id) if filter_id else []
            else:
                logs = st.session_state.system.logs.get_logs()
            
            if logs:
                log_data = []
                for log in reversed(logs):
                    student = st.session_state.system.students.get_student(log.student_id)
                    log_data.append({
                        'Date': log.check_in_time.strftime('%m/%d/%Y'),
                        'Time In': log.check_in_time.strftime('%H:%M:%S'),
                        'Time Out': log.check_out_time.strftime('%H:%M:%S') if log.check_out_time else 'Active',
                        'Duration': format_duration(log.duration_minutes),
                        'Student': student.name if student else 'Unknown',
                        'Status': '⚠️ Violation' if log.violation_triggered else '✅ OK'
                    })
                
                st.dataframe(pd.DataFrame(log_data), use_container_width=True)
                
                # Export option
                csv = pd.DataFrame(log_data).to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"restroom_logs_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No logs to display")
        
        with dash_tab4:
            st.subheader("Violations & Probation")
            
            dashboard_data = st.session_state.system.get_dashboard_data()
            
            # Strikes
            if dashboard_data['strike_list']:
                st.write("### Strike List")
                strike_data = []
                for strike in reversed(dashboard_data['strike_list']):
                    strike_data.append({
                        'Date': strike['timestamp'].strftime('%m/%d/%Y %H:%M'),
                        'Student': strike['student_name'],
                        'Violations': strike['violation_count'],
                        'Email': strike['parent_email'] or 'N/A'
                    })
                
                st.dataframe(pd.DataFrame(strike_data), use_container_width=True)
            else:
                st.info("No strikes recorded")
            
            # Probation
            if dashboard_data['deduction_list']:
                st.write("### Currently on Probation")
                probation_data = []
                for sid in dashboard_data['deduction_list']:
                    student = st.session_state.system.students.get_student(sid)
                    if student:
                        probation_data.append({
                            'Name': student.name,
                            'Ends': student.probation_end_date.strftime('%m/%d/%Y') if student.probation_end_date else 'N/A',
                            'Days Left': (student.probation_end_date - datetime.now()).days if student.probation_end_date else 0,
                            'Points Deducted': student.points_deducted
                        })
                
                st.dataframe(pd.DataFrame(probation_data), use_container_width=True)
            else:
                st.info("No students on probation")
            
            # Extra Credit
            if dashboard_data['extra_credit_list']:
                st.write("### Extra Credit Candidates")
                st.info(f"Students with unused passes: {len(dashboard_data['extra_credit_list'])}")
                
                for sid in dashboard_data['extra_credit_list']:
                    student = st.session_state.system.students.get_student(sid)
                    if student:
                        st.write(f"✅ {student.name} - {Config.PASSES_PER_CYCLE - student.passes_used_current_cycle} unused passes")
    
    # ==================== SETTINGS TAB ====================
    with tab3:
        st.header("System Settings")
        
        st.write("### Policy Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Violation Threshold", f"{Config.VIOLATION_THRESHOLD_MINUTES} minutes")
            st.metric("Probation Duration", f"{Config.PROBATION_PERIOD_DAYS} days")
            st.metric("Probation Auto Deduction", f"{Config.PROBATION_AUTO_DEDUCTION} points")
        
        with col2:
            st.metric("Passes Per Cycle", f"{Config.PASSES_PER_CYCLE} passes")
            st.metric("Pass Cycle Duration", f"{Config.PASS_CYCLE_DAYS} days")
            st.metric("Deduction on Probation", f"{Config.RESTROOM_DEDUCTION_ON_PROBATION} points")
        
        st.info("💡 To change settings, modify the Config class in restroom_system.py")
        
        # Maintenance
        st.write("### Maintenance")
        
        if st.button("🔄 Update Pass Cycles (Manual)"):
            reset_students = st.session_state.system.update_pass_cycles()
            if reset_students:
                st.success(f"✅ Reset passes for {len(reset_students)} students")
            else:
                st.info("No students needed pass reset")
        
        if st.button("🛡️ Check Probation Status (Manual)"):
            lifted = st.session_state.system.check_and_lift_probation()
            if lifted:
                st.success(f"✅ Lifted probation for {len(lifted)} students")
            else:
                st.info("No probation periods to lift")
        
        # Data management
        st.write("### Data Management")
        st.warning("⚠️ These actions cannot be undone!")
        
        if st.button("🗑️ Export All Data"):
            data = st.session_state.system.get_dashboard_data()
            st.json({
                'students': {k: v.to_dict() for k, v in data['all_students'].items()},
                'logs': [log.to_dict() for log in data['all_logs']],
                'strikes': data['strike_list']
            })


if __name__ == "__main__":
    main()
