from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Patient")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    full_name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(30))
    contact_number = db.Column(db.String(30), index=True)
    email = db.Column(db.String(120), index=True)
    aadhaar_number = db.Column(db.String(20), index=True)
    address = db.Column(db.Text)
    blood_group = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Doctor(db.Model):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    doctor_name = db.Column(db.String(120), nullable=False)
    specialization = db.Column(db.String(120))
    qualification = db.Column(db.String(120))
    department = db.Column(db.String(120))
    contact_number = db.Column(db.String(30))
    email = db.Column(db.String(120))
    available_time = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Nurse(db.Model):
    __tablename__ = "nurses"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    nurse_name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120))
    contact_number = db.Column(db.String(30))
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(30), default="Booked")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="appointments")
    doctor = db.relationship("Doctor", backref="appointments")

class MedicalRecord(db.Model):
    __tablename__ = "medical_records"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=True)
    diagnosis = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="medical_records")
    doctor = db.relationship("Doctor", backref="medical_records")


class ElectronicHealthRecord(db.Model):
    __tablename__ = "electronic_health_records"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), unique=True, nullable=False)
    allergies = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    previous_diagnoses = db.Column(db.Text)
    current_medications = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship("Patient", backref=db.backref("ehr", uselist=False))


class Consultation(db.Model):
    __tablename__ = "consultations"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    symptoms = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    consultation_date = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="consultations")
    doctor = db.relationship("Doctor", backref="consultations")


class Prescription(db.Model):
    __tablename__ = "prescriptions"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    medicine_name = db.Column(db.String(200), nullable=False)
    dosage = db.Column(db.String(100))
    frequency = db.Column(db.String(100))
    duration = db.Column(db.String(100))
    special_instructions = db.Column(db.Text)
    prescribed_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="prescriptions")
    doctor = db.relationship("Doctor", backref="prescriptions")


class LaboratoryReport(db.Model):
    __tablename__ = "laboratory_reports"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    test_type = db.Column(db.String(120), nullable=False)
    test_date = db.Column(db.Date, nullable=False)
    result = db.Column(db.Text)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="laboratory_reports")
    doctor = db.relationship("Doctor", backref="laboratory_reports")


class Medicine(db.Model):
    __tablename__ = "medicines"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    category = db.Column(db.String(100))
    batch_number = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=10)
    unit_price = db.Column(db.Float, default=0)
    expiry_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PharmacyDispense(db.Model):
    __tablename__ = "pharmacy_dispenses"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicines.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, default=0)
    dispensed_at = db.Column(db.DateTime, default=datetime.utcnow)
    patient = db.relationship("Patient", backref="pharmacy_dispenses")
    medicine = db.relationship("Medicine")

class Bill(db.Model):
    __tablename__ = "bills"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    consultation_charge = db.Column(db.Float, default=0)
    laboratory_charge = db.Column(db.Float, default=0)
    pharmacy_charge = db.Column(db.Float, default=0)
    other_charge = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(30), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    patient = db.relationship("Patient", backref="bills")

class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default="General")
    status = db.Column(db.String(30), default="Unread")
    delivery_status = db.Column(db.String(30), default="Delivered")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="notifications")

class LoginActivity(db.Model):
    __tablename__ = "login_activities"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    action = db.Column(db.String(30), nullable=False)
    ip_address = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="login_activities")


class PatientFeedback(db.Model):
    __tablename__ = "patient_feedback"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=True, index=True)
    department = db.Column(db.String(120))
    consultation_rating = db.Column(db.Integer, nullable=False)
    hospital_rating = db.Column(db.Integer, nullable=False)
    laboratory_rating = db.Column(db.Integer, nullable=False)
    pharmacy_rating = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    patient = db.relationship("Patient", backref="feedback")
    doctor = db.relationship("Doctor", backref="feedback")


class PaymentTransaction(db.Model):
    __tablename__ = "payment_transactions"
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("bills.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False, default=0)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(40), default="Pending")
    transaction_reference = db.Column(db.String(120), unique=True, index=True)
    notes = db.Column(db.Text)
    gateway = db.Column(db.String(40), default="")
    gateway_order_id = db.Column(db.String(100), index=True)
    gateway_payment_id = db.Column(db.String(100), index=True)
    gateway_signature = db.Column(db.String(128))
    gateway_status = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    bill = db.relationship("Bill", backref=db.backref("payment_transactions", lazy=True))
    patient = db.relationship("Patient", backref="payment_transactions")


class SystemSetting(db.Model):
    __tablename__ = "system_settings"
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    setting_value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
