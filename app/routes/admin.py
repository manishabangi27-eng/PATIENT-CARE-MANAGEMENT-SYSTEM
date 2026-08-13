from functools import wraps
from collections import defaultdict
from datetime import date, timedelta, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from app import db
from app.models import User, Patient, Doctor, Nurse, Appointment, Consultation, LaboratoryReport, Bill, Notification, PatientFeedback, LoginActivity, Medicine, PharmacyDispense, Prescription

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role.lower() != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    """Complete administrator control dashboard."""
    today = date.today()

    # Core dashboard cards
    patients = Patient.query.count()
    doctors = Doctor.query.count()
    nurses = Nurse.query.count()
    admins = User.query.filter(db.func.lower(User.role) == "admin").count()
    appointments_today = Appointment.query.filter_by(appointment_date=today).count()
    completed_consultations = Consultation.query.count()
    pending_labs = LaboratoryReport.query.filter(
        db.or_(LaboratoryReport.result.is_(None), LaboratoryReport.result == "")
    ).count()
    bills_generated = Bill.query.count()
    paid_revenue = sum(float(b.total_amount or 0) for b in Bill.query.filter(db.func.lower(Bill.payment_status) == "paid").all())
    unpaid_revenue = sum(float(b.total_amount or 0) for b in Bill.query.filter(db.func.lower(Bill.payment_status) != "paid").all())
    unread_notifications = Notification.query.filter_by(status="Unread").count()

    # Last 30 days appointment trend.
    start_date = today - timedelta(days=29)
    appointments = Appointment.query.filter(Appointment.appointment_date >= start_date).all()
    daily_counts = {}
    for a in appointments:
        daily_counts[a.appointment_date] = daily_counts.get(a.appointment_date, 0) + 1
    trend_labels = [(start_date + timedelta(days=i)).strftime("%d %b") for i in range(30)]
    trend_values = [daily_counts.get(start_date + timedelta(days=i), 0) for i in range(30)]

    # Patient registrations for the last 6 calendar months.
    month_starts = []
    cursor = today.replace(day=1)
    for _ in range(5, -1, -1):
        y, m = cursor.year, cursor.month - _
        while m <= 0:
            y -= 1; m += 12
        month_starts.append(date(y, m, 1))
    month_labels = [d.strftime("%b %Y") for d in month_starts]
    month_values = [0] * 6
    for p in Patient.query.all():
        if not p.created_at:
            continue
        pd = p.created_at.date() if hasattr(p.created_at, "date") else p.created_at
        for i, ms in enumerate(month_starts):
            next_month = date(ms.year + (1 if ms.month == 12 else 0), 1 if ms.month == 12 else ms.month + 1, 1)
            if ms <= pd < next_month:
                month_values[i] += 1
                break

    # Doctor-wise consultation counts.
    doctor_counts = {d.doctor_name: 0 for d in Doctor.query.order_by(Doctor.doctor_name).all()}
    for c in Consultation.query.all():
        if c.doctor_id:
            d = db.session.get(Doctor, c.doctor_id)
            if d:
                doctor_counts[d.doctor_name] = doctor_counts.get(d.doctor_name, 0) + 1
    doctor_labels = list(doctor_counts.keys())
    doctor_values = list(doctor_counts.values())

    # Patient demographics.
    demographic_counts = {}
    for p in Patient.query.all():
        key = (p.gender or "Not specified").strip() or "Not specified"
        demographic_counts[key] = demographic_counts.get(key, 0) + 1

    # Disease/diagnosis distribution from consultations.
    disease_counts = {}
    for c in Consultation.query.all():
        diagnosis = (c.diagnosis or "Not specified").strip() or "Not specified"
        diagnosis = diagnosis[:40]
        disease_counts[diagnosis] = disease_counts.get(diagnosis, 0) + 1
    disease_items = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    # Laboratory test statistics.
    lab_counts = {}
    for lab in LaboratoryReport.query.all():
        key = (lab.test_type or "Other").strip() or "Other"
        lab_counts[key] = lab_counts.get(key, 0) + 1
    lab_items = sorted(lab_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    # Monthly revenue for the last 6 months.
    revenue_values = [0.0] * 6
    for b in Bill.query.all():
        if not b.created_at:
            continue
        bd = b.created_at.date() if hasattr(b.created_at, "date") else b.created_at
        for i, ms in enumerate(month_starts):
            next_month = date(ms.year + (1 if ms.month == 12 else 0), 1 if ms.month == 12 else ms.month + 1, 1)
            if ms <= bd < next_month and str(b.payment_status or "").lower() == "paid":
                revenue_values[i] += float(b.total_amount or 0)
                break

    # Recent operational records.
    recent_appointments = Appointment.query.order_by(
        Appointment.appointment_date.desc(), Appointment.appointment_time.desc()
    ).limit(8).all()
    recent_feedback = PatientFeedback.query.order_by(PatientFeedback.created_at.desc()).limit(5).all()
    recent_activity = LoginActivity.query.order_by(LoginActivity.created_at.desc()).limit(8).all()

    avg_rating = db.session.query(db.func.avg(
        (PatientFeedback.consultation_rating + PatientFeedback.hospital_rating +
         PatientFeedback.laboratory_rating + PatientFeedback.pharmacy_rating) / 4.0
    )).scalar() or 0

    # Department-level consultation graph.
    department_rows = db.session.query(
        Doctor.department, db.func.count(Consultation.id)
    ).outerjoin(Consultation, Doctor.id == Consultation.doctor_id).group_by(
        Doctor.department
    ).order_by(db.func.count(Consultation.id).desc()).all()
    department_labels = [x[0] or "Unassigned" for x in department_rows]
    department_values = [x[1] for x in department_rows]

    pharmacy_total = Medicine.query.count()
    pharmacy_low = Medicine.query.filter(Medicine.quantity <= Medicine.reorder_level).count()
    pharmacy_expired = Medicine.query.filter(Medicine.expiry_date < today).count()
    unread_patients = Notification.query.join(User).filter(
        db.func.lower(User.role) == "patient", Notification.status == "Unread"
    ).count()

    return render_template(
        "admin/dashboard.html",
        patients=patients, doctors=doctors, nurses=nurses, admins=admins,
        appointments=Appointment.query.count(), appointments_today=appointments_today,
        completed_consultations=completed_consultations, pending_labs=pending_labs,
        bills_generated=bills_generated, paid_revenue=paid_revenue,
        unpaid_revenue=unpaid_revenue, unread_notifications=unread_notifications,
        feedback_count=PatientFeedback.query.count(), avg_rating=round(float(avg_rating), 2),
        trend_labels=trend_labels, trend_values=trend_values,
        month_labels=month_labels, month_values=month_values,
        doctor_labels=doctor_labels, doctor_values=doctor_values,
        demographic_labels=list(demographic_counts.keys()), demographic_values=list(demographic_counts.values()),
        disease_labels=[x[0] for x in disease_items], disease_values=[x[1] for x in disease_items],
        lab_labels=[x[0] for x in lab_items], lab_values=[x[1] for x in lab_items],
        revenue_labels=month_labels, revenue_values=revenue_values,
        recent_appointments=recent_appointments, recent_feedback=recent_feedback,
        recent_activity=recent_activity,
        department_labels=department_labels, department_values=department_values,
        pharmacy_total=pharmacy_total, pharmacy_low=pharmacy_low,
        pharmacy_expired=pharmacy_expired, unread_patients=unread_patients
    )


@admin_bp.route("/appointments")
@admin_required
def appointments():
    return render_template(
        "admin/appointments.html",
        appointments=Appointment.query.order_by(
            Appointment.appointment_date.desc(),
            Appointment.appointment_time.desc()
        ).all()
    )


@admin_bp.route("/appointments/<int:appointment_id>/accept", methods=["POST"])
@admin_required
def accept_appointment(appointment_id):
    appointment = db.session.get(Appointment, appointment_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for("admin.appointments"))

    appointment.status = "Accepted"
    db.session.commit()
    flash("Appointment accepted successfully.", "success")
    return redirect(request.referrer or url_for("admin.appointments"))


@admin_bp.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
@admin_required
def cancel_appointment(appointment_id):
    appointment = db.session.get(Appointment, appointment_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for("admin.appointments"))

    appointment.status = "Cancelled"
    db.session.commit()
    flash("Appointment cancelled successfully.", "warning")
    return redirect(request.referrer or url_for("admin.appointments"))


@admin_bp.route("/doctors")
@admin_required
def doctors():
    return render_template("admin/doctors.html", doctors=Doctor.query.order_by(Doctor.id.desc()).all())


@admin_bp.route("/doctors/add", methods=["GET", "POST"])
@admin_required
def add_doctor():
    if request.method == "POST":
        doctor_name = request.form.get("doctor_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not doctor_name or not email or not password:
            flash("Doctor name, email, and password are required.", "danger")
            return render_template("admin/doctor_form.html")

        if User.query.filter_by(email=email).first():
            flash("A login account with this email already exists.", "danger")
            return render_template("admin/doctor_form.html")

        user = User(
            full_name=doctor_name,
            email=email,
            phone=request.form.get("contact_number"),
            role="Doctor"
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        doctor = Doctor(
            user_id=user.id,
            doctor_name=doctor_name,
            specialization=request.form.get("specialization"),
            qualification=request.form.get("qualification"),
            department=request.form.get("department"),
            contact_number=request.form.get("contact_number"),
            email=email,
            available_time=request.form.get("available_time")
        )
        db.session.add(doctor)
        db.session.commit()
        flash(f"Doctor account created successfully. Login email: {email}", "success")
        return redirect(url_for("admin.doctors"))
    return render_template("admin/doctor_form.html")


@admin_bp.route("/doctors/delete/<int:doctor_id>", methods=["POST"])
@admin_required
def delete_doctor(doctor_id):
    doctor = db.session.get(Doctor, doctor_id)
    if doctor:
        linked_user = db.session.get(User, doctor.user_id) if doctor.user_id else None
        db.session.delete(doctor)
        if linked_user:
            db.session.delete(linked_user)
        db.session.commit()
        flash("Doctor and linked login account deleted.", "success")
    return redirect(url_for("admin.doctors"))


@admin_bp.route("/nurses")
@admin_required
def nurses():
    return render_template("admin/nurses.html", nurses=Nurse.query.order_by(Nurse.id.desc()).all())


@admin_bp.route("/nurses/add", methods=["GET", "POST"])
@admin_required
def add_nurse():
    if request.method == "POST":
        nurse_name = request.form.get("nurse_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not nurse_name or not email or not password:
            flash("Nurse name, email, and password are required.", "danger")
            return render_template("admin/nurse_form.html")

        if User.query.filter_by(email=email).first():
            flash("A login account with this email already exists.", "danger")
            return render_template("admin/nurse_form.html")

        user = User(
            full_name=nurse_name,
            email=email,
            phone=request.form.get("contact_number"),
            role="Nurse"
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        nurse = Nurse(
            user_id=user.id,
            nurse_name=nurse_name,
            department=request.form.get("department"),
            contact_number=request.form.get("contact_number"),
            email=email
        )
        db.session.add(nurse)
        db.session.commit()
        flash(f"Nurse account created successfully. Login email: {email}", "success")
        return redirect(url_for("admin.nurses"))
    return render_template("admin/nurse_form.html")


@admin_bp.route("/nurses/delete/<int:nurse_id>", methods=["POST"])
@admin_required
def delete_nurse(nurse_id):
    nurse = db.session.get(Nurse, nurse_id)
    if nurse:
        linked_user = db.session.get(User, nurse.user_id) if nurse.user_id else None
        db.session.delete(nurse)
        if linked_user:
            db.session.delete(linked_user)
        db.session.commit()
        flash("Nurse and linked login account deleted.", "success")
    return redirect(url_for("admin.nurses"))


@admin_bp.route("/patients")
@admin_required
def patients():
    return render_template("admin/patients.html", patients=Patient.query.order_by(Patient.id.desc()).all())


@admin_bp.route("/notifications", methods=["GET", "POST"])
@admin_required
def notifications():
    """Admin notification center: send hospital updates to one or all patients."""
    if request.method == "POST":
        patient_id = request.form.get("patient_id", "all")
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        kind = request.form.get("notification_type", "General").strip() or "General"
        if not title or not message:
            flash("Notification title and message are required.", "danger")
            return redirect(url_for("admin.notifications"))
        patients = Patient.query.order_by(Patient.full_name).all() if patient_id == "all" else [
            Patient.query.get_or_404(int(patient_id))
        ]
        sent = 0
        for patient in patients:
            if patient.user_id:
                db.session.add(Notification(
                    user_id=patient.user_id, title=title, message=message,
                    notification_type=kind, status="Unread", delivery_status="Delivered"
                ))
                sent += 1
        db.session.commit()
        flash(f"Notification sent to {sent} patient account(s).", "success")
        return redirect(url_for("admin.notifications"))

    notifications = Notification.query.join(User).filter(
        db.func.lower(User.role) == "patient"
    ).order_by(Notification.created_at.desc()).limit(100).all()
    return render_template(
        "admin/notifications.html",
        patients=Patient.query.order_by(Patient.full_name).all(),
        notifications=notifications
    )


@admin_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@admin_required
def admin_read_notification(notification_id):
    n = Notification.query.get_or_404(notification_id)
    n.status = "Read"
    db.session.commit()
    return redirect(url_for("admin.notifications"))


@admin_bp.route("/system-status")
@admin_required
def system_status():
    """Hospital-wide operational and performance overview."""
    import time as _time

    def timed(label, fn):
        started = _time.perf_counter()
        try:
            value = fn()
            ms = (_time.perf_counter() - started) * 1000
            return {"name": label, "value": value, "ms": round(ms, 2), "ok": True}
        except Exception as exc:
            ms = (_time.perf_counter() - started) * 1000
            return {"name": label, "value": "Error", "ms": round(ms, 2), "ok": False, "detail": str(exc)[:120]}

    checks = [
        timed("Database health", lambda: db.session.execute(db.text("SELECT 1")).scalar()),
        timed("Patient module", lambda: Patient.query.count()),
        timed("Appointments", lambda: Appointment.query.count()),
        timed("Consultations", lambda: Consultation.query.count()),
        timed("Laboratory", lambda: LaboratoryReport.query.count()),
        timed("Prescriptions", lambda: Prescription.query.count()),
        timed("Pharmacy", lambda: Medicine.query.count()),
        timed("Billing", lambda: Bill.query.count()),
        timed("Notifications", lambda: Notification.query.count()),
    ]
    avg_ms = round(sum(x["ms"] for x in checks) / len(checks), 2)
    healthy = sum(1 for x in checks if x["ok"])
    uptime_score = round((healthy / len(checks)) * 100)
    if avg_ms < 100 and uptime_score >= 95:
        overall = "Excellent"
    elif avg_ms < 250 and uptime_score >= 80:
        overall = "Good"
    else:
        overall = "Needs Attention"

    metrics = current_app.extensions.get("performance_metrics", {})
    api_rows = []
    for endpoint, item in metrics.items():
        if item["count"]:
            api_rows.append({
                "endpoint": endpoint,
                "requests": item["count"],
                "avg_ms": round(item["total_ms"] / item["count"], 2),
                "last_ms": round(item["recent_ms"][-1], 2) if item["recent_ms"] else 0
            })
    api_rows.sort(key=lambda x: (x["avg_ms"], -x["requests"]))
    top_apis = api_rows[:8]

    dept_rows = db.session.query(
        Doctor.department, db.func.count(Consultation.id)
    ).outerjoin(Consultation, Doctor.id == Consultation.doctor_id).group_by(
        Doctor.department
    ).order_by(db.func.count(Consultation.id).desc()).all()

    module_counts = [
        ("Patients", Patient.query.count()),
        ("Doctors", Doctor.query.count()),
        ("Nurses", Nurse.query.count()),
        ("Appointments", Appointment.query.count()),
        ("Consultations", Consultation.query.count()),
        ("Laboratory Tests", LaboratoryReport.query.count()),
        ("Prescriptions", Prescription.query.count()),
        ("Pharmacy Medicines", Medicine.query.count()),
        ("Bills", Bill.query.count()),
        ("Notifications", Notification.query.count()),
    ]
    max_count = max([x[1] for x in module_counts] or [1])
    module_health = [
        {"name": name, "count": count, "score": round((count / max_count) * 100) if max_count else 0}
        for name, count in module_counts
    ]

    optimizations = [
        ("Database", "Indexes and bounded aggregate queries are used for dashboard and search workloads.", "fa-database"),
        ("API", "Recent request timings are tracked in a rolling in-memory window to identify slow endpoints.", "fa-gauge-high"),
        ("Frontend", "Charts use compact aggregated datasets instead of loading every record into the browser.", "fa-chart-line"),
        ("Security", "Role-based guards protect admin, clinical, billing and patient notification actions.", "fa-shield-halved"),
        ("Operations", "System health checks cover clinical, pharmacy, laboratory, billing and notification modules.", "fa-server"),
    ]

    return render_template(
        "admin/system_status.html",
        checks=checks, avg_ms=avg_ms, uptime_score=uptime_score, overall=overall,
        top_apis=top_apis, module_health=module_health,
        department_labels=[x[0] or "Unassigned" for x in dept_rows],
        department_values=[x[1] for x in dept_rows],
        optimizations=optimizations
    )


@admin_bp.route("/login-activity")
@admin_required
def login_activity():
    activities = LoginActivity.query.order_by(LoginActivity.created_at.desc()).limit(200).all()
    return render_template("admin/login_activity.html", activities=activities)

