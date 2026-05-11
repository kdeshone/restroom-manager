"""
Core business logic for the Restroom Management System.
Handles student data, check-in/out operations, violations, and probation management.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import json


# ==================== CONFIGURATION ====================
class Config:
    """Policy configuration constants"""
    VIOLATION_THRESHOLD_MINUTES = 5
    PROBATION_THRESHOLD_VIOLATIONS = 2
    PROBATION_PERIOD_DAYS = 7
    PASSES_PER_CYCLE = 3
    PASS_CYCLE_DAYS = 21
    PROBATION_AUTO_DEDUCTION = 3
    RESTROOM_DEDUCTION_ON_PROBATION = 2
    WARNING_COLOR = "red"
    NORMAL_COLOR = "green"
    MAX_DISPLAY_TIME_MINUTES = 10


# ==================== DATA STRUCTURES ====================
@dataclass
class Student:
    """Student record with all relevant attributes"""
    student_id: str
    name: str
    parent_email: Optional[str] = None
    violations: int = 0
    on_probation: bool = False
    probation_end_date: Optional[datetime] = None
    points_deducted: int = 0
    passes_used_current_cycle: int = 0
    last_pass_reset_date: Optional[datetime] = None

    def __post_init__(self):
        """Ensure ID is string, initialize dates"""
        self.student_id = str(self.student_id)
        if self.last_pass_reset_date is None:
            self.last_pass_reset_date = datetime.now()

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['probation_end_date'] = data['probation_end_date'].isoformat() if data['probation_end_date'] else None
        data['last_pass_reset_date'] = data['last_pass_reset_date'].isoformat() if data['last_pass_reset_date'] else None
        return data


@dataclass
class RestroomVisit:
    """Record of a single restroom visit"""
    student_id: str
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    duration_minutes: float = 0.0
    violation_triggered: bool = False

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'student_id': self.student_id,
            'check_in_time': self.check_in_time.isoformat(),
            'check_out_time': self.check_out_time.isoformat() if self.check_out_time else None,
            'duration_minutes': self.duration_minutes,
            'violation_triggered': self.violation_triggered
        }


# ==================== STUDENT MANAGER ====================
class StudentManager:
    """Manages student database and persistence"""
    
    def __init__(self, db_file: str = 'students.json'):
        self.db_file = db_file
        self.students: Dict[str, Student] = {}
        self.load()

    def load(self):
        """Load students from JSON file"""
        try:
            with open(self.db_file, 'r') as f:
                data = json.load(f)
                for sid, student_data in data.items():
                    # Parse dates
                    if student_data.get('probation_end_date'):
                        student_data['probation_end_date'] = datetime.fromisoformat(student_data['probation_end_date'])
                    if student_data.get('last_pass_reset_date'):
                        student_data['last_pass_reset_date'] = datetime.fromisoformat(student_data['last_pass_reset_date'])
                    self.students[sid] = Student(**student_data)
        except FileNotFoundError:
            # Initialize with sample students if file doesn't exist
            self._init_sample_students()
            self.save()

    def _init_sample_students(self):
        """Initialize with sample data"""
        self.students = {
            '1001': Student('1001', 'Alice Wonderland', 'alice.p@example.com'),
            '1002': Student('1002', 'Bob The Builder', 'bob.b@example.com'),
            '1003': Student('1003', 'Charlie Chaplin', 'charlie.c@example.com'),
        }

    def save(self):
        """Save students to JSON file"""
        data = {sid: student.to_dict() for sid, student in self.students.items()}
        with open(self.db_file, 'w') as f:
            json.dump(data, f, indent=2)

    def add_student(self, student_id: str, name: str, parent_email: Optional[str] = None) -> bool:
        """Add a new student"""
        if student_id in self.students:
            return False
        self.students[student_id] = Student(student_id, name, parent_email)
        self.save()
        return True

    def get_student(self, student_id: str) -> Optional[Student]:
        """Get student by ID"""
        return self.students.get(str(student_id))

    def update_student(self, student: Student):
        """Update student record"""
        self.students[student.student_id] = student
        self.save()

    def delete_student(self, student_id: str) -> bool:
        """Delete student"""
        if str(student_id) in self.students:
            del self.students[str(student_id)]
            self.save()
            return True
        return False

    def get_all_students(self) -> Dict[str, Student]:
        """Get all students"""
        return self.students.copy()


# ==================== RESTROOM LOG MANAGER ====================
class RestroomLogManager:
    """Manages restroom visit logs"""
    
    def __init__(self, log_file: str = 'restroom_logs.json'):
        self.log_file = log_file
        self.logs: List[RestroomVisit] = []
        self.active_visits: Dict[str, RestroomVisit] = {}
        self.load()

    def load(self):
        """Load logs from JSON file"""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
                for log_data in data:
                    log_data['check_in_time'] = datetime.fromisoformat(log_data['check_in_time'])
                    if log_data.get('check_out_time'):
                        log_data['check_out_time'] = datetime.fromisoformat(log_data['check_out_time'])
                    self.logs.append(RestroomVisit(**log_data))
        except FileNotFoundError:
            pass

    def save(self):
        """Save logs to JSON file"""
        data = [log.to_dict() for log in self.logs]
        with open(self.log_file, 'w') as f:
            json.dump(data, f, indent=2)

    def check_in(self, student_id: str) -> RestroomVisit:
        """Record a student checking in"""
        visit = RestroomVisit(str(student_id), datetime.now())
        self.active_visits[str(student_id)] = visit
        return visit

    def check_out(self, student_id: str) -> Optional[RestroomVisit]:
        """Record a student checking out"""
        student_id = str(student_id)
        if student_id not in self.active_visits:
            return None
        
        visit = self.active_visits.pop(student_id)
        visit.check_out_time = datetime.now()
        visit.duration_minutes = (visit.check_out_time - visit.check_in_time).total_seconds() / 60
        visit.violation_triggered = visit.duration_minutes > Config.VIOLATION_THRESHOLD_MINUTES
        
        self.logs.append(visit)
        self.save()
        return visit

    def get_active_visits(self) -> Dict[str, RestroomVisit]:
        """Get all currently active visits"""
        return self.active_visits.copy()

    def get_logs(self, student_id: Optional[str] = None) -> List[RestroomVisit]:
        """Get logs for a student or all logs"""
        if student_id:
            return [log for log in self.logs if log.student_id == str(student_id)]
        return self.logs.copy()


# ==================== RESTROOM SYSTEM ====================
class RestroomManagementSystem:
    """Main system for managing restroom passes"""
    
    def __init__(self, students_file: str = 'students.json', logs_file: str = 'restroom_logs.json'):
        self.students = StudentManager(students_file)
        self.logs = RestroomLogManager(logs_file)
        self.strike_list: List[Dict] = []
        self.deduction_list: List[str] = []
        self.extra_credit_list: List[str] = []

    def check_and_lift_probation(self) -> List[str]:
        """Check and lift expired probations"""
        lifted = []
        current_time = datetime.now()
        
        for student in self.students.get_all_students().values():
            if student.on_probation and student.probation_end_date and current_time > student.probation_end_date:
                student.on_probation = False
                student.probation_end_date = None
                student.violations = 0
                self.students.update_student(student)
                
                if student.student_id in self.deduction_list:
                    self.deduction_list.remove(student.student_id)
                
                lifted.append(student.student_id)
        
        return lifted

    def handle_scan(self, student_id: str) -> Dict:
        """Handle a barcode/NFC scan"""
        self.check_and_lift_probation()
        
        student = self.students.get_student(student_id)
        if not student:
            return {'success': False, 'message': f'Student {student_id} not found'}

        # Check if student is currently checked in
        if student_id in self.logs.active_visits:
            return self._handle_checkout(student)
        else:
            return self._handle_checkin(student)

    def _handle_checkin(self, student: Student) -> Dict:
        """Handle check-in logic"""
        # Check pass limit
        if self._should_reset_passes(student):
            student.passes_used_current_cycle = 0
            student.last_pass_reset_date = datetime.now()
            self.students.update_student(student)

        if student.passes_used_current_cycle >= Config.PASSES_PER_CYCLE and not student.on_probation:
            return {
                'success': False,
                'message': f'{student.name} has used all {Config.PASSES_PER_CYCLE} passes this cycle',
                'student_name': student.name
            }

        # Record check-in
        visit = self.logs.check_in(student.student_id)
        student.passes_used_current_cycle += 1
        self.students.update_student(student)

        return {
            'success': True,
            'message': f'Checked in {student.name}. Timer started!',
            'student_name': student.name,
            'passes_remaining': Config.PASSES_PER_CYCLE - student.passes_used_current_cycle
        }

    def _handle_checkout(self, student: Student) -> Dict:
        """Handle check-out logic"""
        visit = self.logs.check_out(student.student_id)
        
        if not visit:
            return {'success': False, 'message': 'Error checking out'}

        message = f'{student.name} checked out. Duration: {visit.duration_minutes:.1f} minutes'

        # Check for violation
        if visit.violation_triggered:
            student.violations += 1
            message += ' ⚠️ VIOLATION RECORDED'

            # Check if student should be placed on probation
            if student.violations >= Config.PROBATION_THRESHOLD_VIOLATIONS and not student.on_probation:
                student.on_probation = True
                student.probation_end_date = datetime.now() + timedelta(days=Config.PROBATION_PERIOD_DAYS)
                student.points_deducted += Config.PROBATION_AUTO_DEDUCTION
                self.deduction_list.append(student.student_id)
                message += f' → PROBATION ACTIVATED until {student.probation_end_date.strftime("%m/%d")}'
                
                # Add to strike list
                self.strike_list.append({
                    'student_id': student.student_id,
                    'student_name': student.name,
                    'parent_email': student.parent_email,
                    'timestamp': datetime.now(),
                    'violation_count': student.violations
                })

        self.students.update_student(student)

        return {
            'success': True,
            'message': message,
            'student_name': student.name,
            'duration_minutes': visit.duration_minutes,
            'violation': visit.violation_triggered
        }

    def _should_reset_passes(self, student: Student) -> bool:
        """Check if it's time to reset passes"""
        if not student.last_pass_reset_date:
            return False
        
        days_since_reset = (datetime.now() - student.last_pass_reset_date).days
        return days_since_reset >= Config.PASS_CYCLE_DAYS

    def update_pass_cycles(self) -> List[str]:
        """Reset passes for students and identify extra credit candidates"""
        reset_students = []
        for student in self.students.get_all_students().values():
            if self._should_reset_passes(student):
                if student.passes_used_current_cycle < Config.PASSES_PER_CYCLE:
                    if student.student_id not in self.extra_credit_list:
                        self.extra_credit_list.append(student.student_id)
                
                student.passes_used_current_cycle = 0
                student.last_pass_reset_date = datetime.now()
                self.students.update_student(student)
                reset_students.append(student.student_id)
        
        return reset_students

    def get_student_status(self, student_id: str) -> Optional[Dict]:
        """Get complete status of a student"""
        student = self.students.get_student(student_id)
        if not student:
            return None
        
        active_visit = self.logs.active_visits.get(str(student_id))
        elapsed_minutes = None
        if active_visit:
            elapsed_minutes = (datetime.now() - active_visit.check_in_time).total_seconds() / 60
        
        return {
            'student': student,
            'active_visit': active_visit,
            'elapsed_minutes': elapsed_minutes,
            'visit_history': self.logs.get_logs(student_id)
        }

    def get_dashboard_data(self) -> Dict:
        """Get data for dashboard display"""
        return {
            'active_users': self.logs.get_active_visits(),
            'all_logs': self.logs.get_logs(),
            'strike_list': self.strike_list,
            'deduction_list': self.deduction_list,
            'extra_credit_list': self.extra_credit_list,
            'all_students': self.students.get_all_students()
        }
