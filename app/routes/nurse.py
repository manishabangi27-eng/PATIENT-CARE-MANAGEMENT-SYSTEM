from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Nurse, Patient
from app import db

nurse_bp = Blueprint("nurse", __name__)

def nurse_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role.lower() != "nurse":
            flash("Nurse access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)
    return wrapper

@nurse_bp.route("/dashboard")
@nurse_required
def dashboard():
    nurse = Nurse.query.filter_by(email=current_user.email).first()
    patients = Patient.query.order_by(Patient.id.desc()).all()
    return render_template("nurse/dashboard.html", nurse=nurse, patients=patients)
