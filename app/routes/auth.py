from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User, Patient, LoginActivity

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            db.session.add(LoginActivity(user_id=user.id, action="Login", ip_address=request.remote_addr))
            db.session.commit()
            flash("Login successful.", "success")
            return redirect(url_for("main.dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        if not full_name or not email or not password:
            flash("Please fill all required fields.", "danger")
            return render_template("auth/register.html")
        if User.query.filter_by(email=email).first():
            flash("Email is already registered.", "danger")
            return render_template("auth/register.html")
        user = User(full_name=full_name, email=email, phone=phone, role="Patient")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        patient = Patient(user_id=user.id, full_name=full_name, contact_number=phone)
        db.session.add(patient)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")

@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        db.session.add(LoginActivity(user_id=current_user.id, action="Logout", ip_address=request.remote_addr))
        db.session.commit()
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
