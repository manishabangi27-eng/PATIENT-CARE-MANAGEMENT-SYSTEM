from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Doctor, Appointment, Patient
from app import db

doctor_bp = Blueprint("doctor", __name__)

def doctor_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role.lower() != "doctor":
            flash("Doctor access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)
    return wrapper

@doctor_bp.route("/dashboard")
@doctor_required
def dashboard():
    doctor = Doctor.query.filter_by(email=current_user.email).first()
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.appointment_date.desc()).all() if doctor else []
    return render_template("doctor/dashboard.html", doctor=doctor, appointments=appointments)
