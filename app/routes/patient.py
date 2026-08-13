from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Patient, Doctor, Appointment, MedicalRecord
from app import db

patient_bp = Blueprint("patient", __name__)

def patient_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role.lower() != "patient":
            flash("Patient access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)
    return wrapper

def get_current_patient():
    return Patient.query.filter_by(user_id=current_user.id).first()

@patient_bp.route("/dashboard")
@patient_required
def dashboard():
    patient = get_current_patient()
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.appointment_date.desc()).all() if patient else []
    records = MedicalRecord.query.filter_by(patient_id=patient.id).order_by(MedicalRecord.created_at.desc()).all() if patient else []
    return render_template("patient/dashboard.html", patient=patient, appointments=appointments, records=records)

@patient_bp.route("/profile", methods=["GET", "POST"])
@patient_required
def profile():
    patient = get_current_patient()
    if request.method == "POST":
        patient.full_name = request.form["full_name"]
        patient.age = request.form.get("age") or None
        patient.gender = request.form.get("gender")
        patient.contact_number = request.form.get("contact_number")
        patient.address = request.form.get("address")
        patient.blood_group = request.form.get("blood_group")
        current_user.full_name = patient.full_name
        current_user.phone = patient.contact_number
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("patient.profile"))
    return render_template("patient/profile.html", patient=patient)

@patient_bp.route("/book-appointment", methods=["GET", "POST"])
@patient_required
def book_appointment():
    patient = get_current_patient()
    doctors = Doctor.query.order_by(Doctor.doctor_name).all()
    if request.method == "POST":
        doctor_id = int(request.form["doctor_id"])
        date = datetime.strptime(request.form["appointment_date"], "%Y-%m-%d").date()
        time = datetime.strptime(request.form["appointment_time"], "%H:%M").time()
        appointment = Appointment(patient_id=patient.id, doctor_id=doctor_id, appointment_date=date, appointment_time=time)
        db.session.add(appointment)
        db.session.commit()
        flash("Appointment booked successfully.", "success")
        return redirect(url_for("patient.dashboard"))
    return render_template("patient/book_appointment.html", doctors=doctors)


@patient_bp.route("/medical-history")
@patient_required
def medical_history():
    patient = get_current_patient()
    from app.models import ElectronicHealthRecord, Consultation, Prescription, LaboratoryReport
    ehr = ElectronicHealthRecord.query.filter_by(patient_id=patient.id).first()
    consultations = Consultation.query.filter_by(patient_id=patient.id).order_by(Consultation.consultation_date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(Prescription.prescribed_at.desc()).all()
    labs = LaboratoryReport.query.filter_by(patient_id=patient.id).order_by(LaboratoryReport.test_date.desc()).all()
    return render_template("patient/medical_history.html", patient=patient, ehr=ehr,
                           consultations=consultations, prescriptions=prescriptions, labs=labs)
