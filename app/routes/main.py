from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Patient, Doctor, Nurse, Appointment

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home():
    return render_template("home.html")

@main_bp.route("/dashboard")
@login_required
def dashboard():
    role = current_user.role.lower()
    if role == "admin":
        return __import__("flask").redirect("/admin/dashboard")
    if role == "doctor":
        return __import__("flask").redirect("/doctor/dashboard")
    if role == "nurse":
        return __import__("flask").redirect("/nurse/dashboard")
    return __import__("flask").redirect("/patient/dashboard")
