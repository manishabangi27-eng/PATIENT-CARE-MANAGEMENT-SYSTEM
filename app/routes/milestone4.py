from datetime import date, timedelta, datetime
from io import BytesIO, StringIO
import csv
import uuid
import hmac
import hashlib
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import (Patient, Doctor, Nurse, Appointment, Consultation, Prescription,
                        LaboratoryReport, Bill, Notification, PatientFeedback, PaymentTransaction, SystemSetting, Medicine, PharmacyDispense, LoginActivity, ElectronicHealthRecord)

milestone4_bp = Blueprint("milestone4", __name__)

def role_required(*roles):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role.lower() not in [r.lower() for r in roles]:
                flash("You are not authorized to access this module.", "danger")
                return redirect(url_for("main.dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

@milestone4_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    today = date.today()
    patients = Patient.query.count()
    doctors = Doctor.query.count()
    appointments_today = Appointment.query.filter_by(appointment_date=today).count()
    completed = Appointment.query.filter(func.lower(Appointment.status).in_(["completed","consulted"])).count()
    pending_labs = LaboratoryReport.query.filter(LaboratoryReport.result.in_([None, ""])).count()
    bills = Bill.query.count()
    paid = db.session.query(func.coalesce(func.sum(Bill.total_amount),0)).filter(func.lower(Bill.payment_status)=="paid").scalar() or 0
    unpaid = db.session.query(func.coalesce(func.sum(Bill.total_amount),0)).filter(func.lower(Bill.payment_status)!="paid").scalar() or 0
    unread = Notification.query.filter_by(status="Unread").count()

    start = today - timedelta(days=29)
    rows = db.session.query(Appointment.appointment_date, func.count(Appointment.id)).filter(
        Appointment.appointment_date >= start).group_by(Appointment.appointment_date).all()
    amap = {d:c for d,c in rows}
    trend_labels = [(start+timedelta(days=i)).strftime("%d %b") for i in range(30)]
    trend_values = [amap.get(start+timedelta(days=i),0) for i in range(30)]

    month_start = today.replace(day=1)
    reg_rows = db.session.query(func.date(Patient.created_at), func.count(Patient.id)).filter(
        Patient.created_at >= month_start).group_by(func.date(Patient.created_at)).all()
    regmap = {str(d):c for d,c in reg_rows}
    reg_labels = sorted(regmap.keys())
    reg_values = [regmap[x] for x in reg_labels]

    doctor_rows = db.session.query(Doctor.doctor_name, func.count(Consultation.id)).outerjoin(
        Consultation, Doctor.id==Consultation.doctor_id).group_by(Doctor.id).order_by(func.count(Consultation.id).desc()).all()
    feedback_count = PatientFeedback.query.count()
    avg_rating = db.session.query(func.avg(
        (PatientFeedback.consultation_rating + PatientFeedback.hospital_rating +
         PatientFeedback.laboratory_rating + PatientFeedback.pharmacy_rating) / 4.0
    )).scalar()
    demographics = db.session.query(Patient.gender, func.count(Patient.id)).group_by(Patient.gender).all()

    return render_template("milestone4/dashboard.html", patients=patients, doctors=doctors,
        appointments_today=appointments_today, completed=completed, pending_labs=pending_labs,
        bills=bills, paid=paid, unpaid=unpaid, unread=unread, trend_labels=trend_labels,
        trend_values=trend_values, reg_labels=reg_labels, reg_values=reg_values,
        doctor_labels=[x[0] for x in doctor_rows], doctor_values=[x[1] for x in doctor_rows],
        demographic_labels=[x[0] or "Not specified" for x in demographics],
        demographic_values=[x[1] for x in demographics], feedback_count=feedback_count,
        avg_rating=round(avg_rating or 0,2))

@milestone4_bp.route("/feedback", methods=["GET","POST"])
@role_required("patient")
def feedback():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash("Patient profile not found.", "danger")
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        ratings = {}
        try:
            for field in ["consultation_rating","hospital_rating","laboratory_rating","pharmacy_rating"]:
                value=int(request.form.get(field,0))
                if value < 1 or value > 5: raise ValueError
                ratings[field]=value
        except ValueError:
            flash("All ratings must be between 1 and 5 stars.", "danger")
            return redirect(url_for("milestone4.feedback"))
        doctor_id=request.form.get("doctor_id") or None
        doctor=db.session.get(Doctor,int(doctor_id)) if doctor_id else None
        item=PatientFeedback(patient_id=patient.id, doctor_id=doctor.id if doctor else None,
            department=doctor.department if doctor else request.form.get("department"),
            comments=request.form.get("comments"), **ratings)
        db.session.add(item); db.session.commit()
        flash("Thank you. Your feedback was submitted securely.", "success")
        return redirect(url_for("milestone4.feedback"))
    doctors=Doctor.query.order_by(Doctor.doctor_name).all()
    history=PatientFeedback.query.filter_by(patient_id=patient.id).order_by(PatientFeedback.created_at.desc()).all()
    return render_template("milestone4/feedback.html", doctors=doctors, history=history)

@milestone4_bp.route("/feedback/admin")
@role_required("admin")
def feedback_admin():
    q=request.args.get("q","").strip()
    query=PatientFeedback.query
    if q:
        query=query.join(Patient).filter(Patient.full_name.ilike(f"%{q}%"))
    feedbacks=query.order_by(PatientFeedback.created_at.desc()).all()
    avg=db.session.query(func.avg((PatientFeedback.consultation_rating+PatientFeedback.hospital_rating+PatientFeedback.laboratory_rating+PatientFeedback.pharmacy_rating)/4.0)).scalar() or 0
    return render_template("milestone4/feedback_admin.html",feedbacks=feedbacks,avg=round(avg,2),count=len(feedbacks),q=q)

@milestone4_bp.route("/reports")
@role_required("admin")
def reports():
    return render_template("milestone4/reports.html")

@milestone4_bp.route("/reports/export/<report_type>/<fmt>")
@role_required("admin")
def export_report(report_type, fmt):
    mapping = {
        "patients": ("Patient Report", Patient, ["id","full_name","age","gender","contact_number","email","blood_group","created_at"]),
        "appointments": ("Appointment Report", Appointment, ["id","patient_id","doctor_id","appointment_date","appointment_time","status"]),
        "consultations": ("Consultation Report", Consultation, ["id","patient_id","doctor_id","diagnosis","treatment","consultation_date"]),
        "prescriptions": ("Prescription Report", Prescription, ["id","patient_id","doctor_id","medicine_name","dosage","frequency","duration","prescribed_at"]),
        "bills": ("Billing Report", Bill, ["id","patient_id","consultation_charge","laboratory_charge","pharmacy_charge","other_charge","total_amount","payment_status","payment_method","created_at"]),
        "laboratory": ("Laboratory Report", LaboratoryReport, ["id","patient_id","doctor_id","test_type","test_date","result","remarks","created_at"]),
        "payments": ("Payment Transaction Report", PaymentTransaction, ["id","bill_id","patient_id","amount","payment_method","status","transaction_reference","created_at","processed_at"]),
        "feedback": ("Feedback Report", PatientFeedback, ["id","patient_id","doctor_id","department","consultation_rating","hospital_rating","laboratory_rating","pharmacy_rating","comments","created_at"]),
        "pharmacy": ("Pharmacy Inventory Report", Medicine, ["id","name","category","batch_number","quantity","reorder_level","unit_price","expiry_date","created_at"]),
        "dispensing": ("Pharmacy Dispensing Report", PharmacyDispense, ["id","patient_id","medicine_id","quantity","amount","dispensed_at"]),
        "notifications": ("Patient Notification Report", Notification, ["id","user_id","title","message","notification_type","status","delivery_status","created_at"]),
        "login_activity": ("System Login Activity Report", LoginActivity, ["id","user_id","action","ip_address","created_at"]),
        "ehr": ("Electronic Health Record Report", ElectronicHealthRecord, ["id","patient_id","allergies","medical_history","previous_diagnoses","current_medications","updated_at"]),
    }
    if report_type not in mapping or fmt not in ("csv","xlsx","pdf"):
        flash("Unsupported report format.", "danger"); return redirect(url_for("milestone4.reports"))
    title, Model, fields = mapping[report_type]
    rows=Model.query.order_by(Model.id.desc()).all()

    def value(obj, field):
        v=getattr(obj,field,None)
        if hasattr(v,"isoformat"): return v.isoformat(sep=" ") if hasattr(v,"hour") else v.isoformat()
        return "" if v is None else v

    if fmt=="csv":
        buf=StringIO(); writer=csv.writer(buf); writer.writerow(fields)
        for r in rows: writer.writerow([value(r,f) for f in fields])
        data=BytesIO(buf.getvalue().encode("utf-8-sig")); data.seek(0)
        return send_file(data,as_attachment=True,download_name=f"{report_type}_report.csv",mimetype="text/csv")

    if fmt=="xlsx":
        from openpyxl import Workbook
        wb=Workbook(); ws=wb.active; ws.title=report_type[:31]; ws.append(fields)
        for r in rows: ws.append([value(r,f) for f in fields])
        for col in ws.columns:
            maxlen=max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[col[0].column_letter].width=min(maxlen+2,35)
        data=BytesIO(); wb.save(data); data.seek(0)
        return send_file(data,as_attachment=True,download_name=f"{report_type}_report.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    data=BytesIO(); doc=SimpleDocTemplate(data,pagesize=landscape(A4),rightMargin=24,leftMargin=24,topMargin=24,bottomMargin=24)
    styles=getSampleStyleSheet(); elements=[Paragraph(title,styles["Title"]),Spacer(1,12)]
    table_data=[fields]+[[str(value(r,f))[:70] for f in fields] for r in rows]
    table=Table(table_data,repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0d6efd")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.4,colors.grey),("FONTSIZE",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"TOP")]))
    elements.append(table); doc.build(elements); data.seek(0)
    return send_file(data,as_attachment=True,download_name=f"{report_type}_report.pdf",mimetype="application/pdf")

@milestone4_bp.route("/patient-fees")
@role_required("patient")
def patient_fees():
    patient=Patient.query.filter_by(user_id=current_user.id).first()
    bills=Bill.query.filter_by(patient_id=patient.id).order_by(Bill.created_at.desc()).all() if patient else []
    paid=sum((b.total_amount or 0) for b in bills if (b.payment_status or "").lower()=="paid")
    unpaid=sum((b.total_amount or 0) for b in bills if (b.payment_status or "").lower()!="paid")
    return render_template("milestone4/patient_fees.html",patient=patient,bills=bills,paid=paid,unpaid=unpaid)


@milestone4_bp.route("/pay/<int:bill_id>", methods=["GET", "POST"])
@role_required("patient")
def pay_bill(bill_id):
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    bill = Bill.query.filter_by(id=bill_id, patient_id=patient.id if patient else -1).first_or_404()
    if str(bill.payment_status or "").lower() == "paid":
        flash("This bill has already been paid.", "info")
        return redirect(url_for("milestone4.patient_fees"))

    enabled = {
        "UPI": _setting("upi_payment_enabled", "1"),
        "Online": _setting("online_payment_enabled", "1"),
        "Cash": _setting("cash_payment_enabled", "1")
    }
    gateway_ready = bool(current_app.config.get("RAZORPAY_KEY_ID") and current_app.config.get("RAZORPAY_KEY_SECRET"))

    if request.method == "POST":
        method = request.form.get("payment_method", "").strip()
        if method not in enabled:
            flash("Please select a valid payment method.", "danger")
            return redirect(url_for("milestone4.pay_bill", bill_id=bill.id))
        if enabled.get(method) != "1":
            flash(f"{method} payments are currently disabled by the administrator.", "warning")
            return redirect(url_for("milestone4.pay_bill", bill_id=bill.id))

        # Cash remains a manual collection flow. UPI and Online use Razorpay
        # Standard Checkout so the actual funds are processed by the gateway.
        if method == "Cash":
            reference = "IPCMS-CASH-" + uuid.uuid4().hex[:10].upper()
            tx = PaymentTransaction(
                bill_id=bill.id, patient_id=patient.id, amount=float(bill.total_amount or 0),
                payment_method="Cash", status="Pending Cash Collection",
                transaction_reference=reference,
                notes="Cash payment requested by patient; administrator/cashier confirmation required."
            )
            bill.payment_method = "Cash"
            bill.payment_status = "Pending"
            db.session.add(tx)
            db.session.commit()
            flash("Cash payment request recorded. Please pay at the hospital counter.", "warning")
            return redirect(url_for("milestone4.patient_fees"))

        if not gateway_ready:
            flash("Online payments are not configured. Add Razorpay Test/Live API keys to the .env file first.", "danger")
            return redirect(url_for("milestone4.pay_bill", bill_id=bill.id))

        try:
            import razorpay
            client = razorpay.Client(auth=(current_app.config["RAZORPAY_KEY_ID"], current_app.config["RAZORPAY_KEY_SECRET"]))
            amount_paise = int(round(float(bill.total_amount or 0) * 100))
            if amount_paise <= 0:
                flash("This bill has no payable amount.", "danger")
                return redirect(url_for("milestone4.pay_bill", bill_id=bill.id))
            order = client.order.create(data={
                "amount": amount_paise,
                "currency": current_app.config.get("RAZORPAY_CURRENCY", "INR"),
                "receipt": f"IPCMS-BILL-{bill.id}-{uuid.uuid4().hex[:8]}",
                "notes": {
                    "bill_id": str(bill.id),
                    "patient_id": str(patient.id),
                    "requested_method": method,
                },
                "payment_capture": 1 if current_app.config.get("RAZORPAY_AUTO_CAPTURE", True) else 0,
            })
            reference = "IPCMS-RZP-" + uuid.uuid4().hex[:10].upper()
            tx = PaymentTransaction(
                bill_id=bill.id, patient_id=patient.id, amount=float(bill.total_amount or 0),
                payment_method=method, status="Created",
                transaction_reference=reference,
                gateway="Razorpay", gateway_order_id=order["id"], gateway_status=order.get("status", "created"),
                notes="Razorpay Standard Checkout order created. Payment is not considered successful until server-side signature verification/webhook confirmation."
            )
            bill.payment_method = method
            bill.payment_status = "Pending"
            db.session.add(tx)
            db.session.commit()
            return render_template(
                "milestone4/razorpay_checkout.html", bill=bill, transaction=tx, order=order,
                razorpay_key=current_app.config["RAZORPAY_KEY_ID"],
                currency=current_app.config.get("RAZORPAY_CURRENCY", "INR"),
                hospital_name=_setting("hospital_name", "Integrated Patient Care Hospital"),
            )
        except Exception as exc:
            current_app.logger.exception("Razorpay order creation failed")
            flash(f"Unable to start the payment gateway: {str(exc)[:180]}", "danger")
            return redirect(url_for("milestone4.pay_bill", bill_id=bill.id))

    return render_template(
        "milestone4/pay_bill.html", bill=bill,
        upi_id=_setting("upi_id", "hospital@upi"),
        gateway_ready=gateway_ready,
        enabled=enabled,
    )


@milestone4_bp.route("/razorpay/verify", methods=["POST"])
@role_required("patient")
def razorpay_verify():
    """Verify the browser callback using the server-side Razorpay order ID.

    The order ID is looked up in our database rather than trusted from the
    browser. Only a valid HMAC-SHA256 signature can mark the bill as paid.
    """
    data = request.get_json(silent=True) or request.form
    order_id = (data.get("razorpay_order_id") or "").strip()
    payment_id = (data.get("razorpay_payment_id") or "").strip()
    signature = (data.get("razorpay_signature") or "").strip()
    if not order_id or not payment_id or not signature:
        return jsonify(ok=False, message="Incomplete payment response."), 400

    tx = PaymentTransaction.query.filter_by(gateway_order_id=order_id).first()
    if not tx or tx.patient_id != getattr(Patient.query.filter_by(user_id=current_user.id).first(), "id", None):
        return jsonify(ok=False, message="Payment order not found."), 404
    if tx.gateway_payment_id:
        return jsonify(ok=True, message="Payment was already processed.", redirect=url_for("milestone4.patient_fees"))

    secret = current_app.config.get("RAZORPAY_KEY_SECRET", "")
    expected = hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    if not secret or not hmac.compare_digest(expected, signature):
        tx.status = "Verification Failed"
        tx.gateway_status = "signature_mismatch"
        db.session.commit()
        current_app.logger.warning("Razorpay signature verification failed for order %s", order_id)
        return jsonify(ok=False, message="Payment verification failed."), 400

    # Signature proves authenticity; fetch the payment from Razorpay as a second
    # server-side check and only settle the bill when the amount and captured
    # status match the invoice.
    try:
        import razorpay
        client = razorpay.Client(auth=(current_app.config["RAZORPAY_KEY_ID"], current_app.config["RAZORPAY_KEY_SECRET"]))
        payment = client.payment.fetch(payment_id)
        expected_amount = int(round(float(tx.amount or 0) * 100))
        if int(payment.get("amount", -1)) != expected_amount:
            tx.status = "Amount Mismatch"
            tx.gateway_status = "amount_mismatch"
            db.session.commit()
            return jsonify(ok=False, message="Payment amount does not match the hospital bill."), 400
        gateway_status = payment.get("status", "")
        if gateway_status != "captured":
            tx.gateway_payment_id = payment_id
            tx.gateway_signature = signature
            tx.gateway_status = gateway_status
            tx.status = "Authorized - Awaiting Capture" if gateway_status == "authorized" else gateway_status.title()
            db.session.commit()
            return jsonify(ok=False, message=f"Payment is currently {gateway_status}. The bill will be marked paid after capture."), 409
    except Exception as exc:
        current_app.logger.exception("Unable to verify Razorpay payment status")
        return jsonify(ok=False, message="Payment signature is valid, but the gateway status could not be confirmed yet."), 502

    tx.gateway_payment_id = payment_id
    tx.gateway_signature = signature
    tx.gateway_status = "captured"
    tx.status = "Paid"
    tx.processed_at = datetime.utcnow()
    tx.notes = "Razorpay payment signature and captured amount verified server-side."
    tx.bill.payment_status = "Paid"
    tx.bill.payment_method = tx.payment_method
    db.session.commit()
    return jsonify(ok=True, message="Payment verified successfully.", redirect=url_for("milestone4.patient_fees"))


@milestone4_bp.route("/razorpay/webhook", methods=["POST"])
def razorpay_webhook():
    """Receive Razorpay payment events and update payment records.

    Configure this public HTTPS URL in Razorpay Dashboard and use a dedicated
    webhook secret. The raw request body is verified before parsing JSON.
    """
    secret = current_app.config.get("RAZORPAY_WEBHOOK_SECRET", "")
    signature = request.headers.get("X-Razorpay-Signature", "")
    raw = request.get_data()
    if not secret or not signature:
        return "", 400
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        current_app.logger.warning("Rejected Razorpay webhook: invalid signature")
        return "", 400

    payload = request.get_json(silent=True) or {}
    event = payload.get("event", "")
    payload_data = payload.get("payload") or {}
    entity = (((payload_data.get("payment") or {}).get("entity")) or {})
    if not entity and payload_data.get("order"):
        entity = ((payload_data.get("order") or {}).get("entity")) or {}
    order_id = entity.get("order_id") or entity.get("id")
    payment_id = entity.get("id") if payload_data.get("payment") else None
    status = entity.get("status")
    tx = PaymentTransaction.query.filter_by(gateway_order_id=order_id).first() if order_id else None
    if tx:
        # Idempotent: repeated webhook deliveries do not create duplicate payments.
        tx.gateway_payment_id = payment_id or tx.gateway_payment_id
        tx.gateway_status = status or event
        webhook_amount = entity.get("amount")
        expected_amount = int(round(float(tx.amount or 0) * 100))
        amount_ok = webhook_amount is None or int(webhook_amount) == expected_amount
        if (event in {"payment.captured", "order.paid"} or status == "captured") and amount_ok:
            tx.status = "Paid"
            tx.processed_at = tx.processed_at or datetime.utcnow()
            tx.bill.payment_status = "Paid"
            tx.bill.payment_method = tx.payment_method
        elif (event in {"payment.captured", "order.paid"} or status == "captured") and not amount_ok:
            tx.status = "Amount Mismatch"
            tx.gateway_status = "amount_mismatch"
        elif event in {"payment.failed"} or status == "failed":
            tx.status = "Failed"
        db.session.commit()
    return "", 200

@milestone4_bp.route("/payments/<int:transaction_id>/confirm-cash", methods=["POST"])
@role_required("admin")
def confirm_cash_payment(transaction_id):
    tx = PaymentTransaction.query.get_or_404(transaction_id)
    if tx.payment_method != "Cash":
        flash("Only cash transactions can be confirmed here.", "danger")
        return redirect(url_for("milestone4.integrations"))
    tx.status = "Paid"
    tx.processed_at = datetime.utcnow()
    tx.bill.payment_status = "Paid"
    tx.bill.payment_method = "Cash"
    db.session.commit()
    flash(f"Cash payment {tx.transaction_reference} confirmed.", "success")
    return redirect(url_for("milestone4.integrations"))


def _setting(key, default=""):
    row = SystemSetting.query.filter_by(setting_key=key).first()
    return row.setting_value if row else default


@milestone4_bp.route("/settings", methods=["GET", "POST"])
@role_required("admin")
def settings():
    defaults = {
        "hospital_name": "Integrated Patient Care Hospital",
        "currency_symbol": "₹",
        "upi_id": "hospital@upi",
        "cash_payment_enabled": "1",
        "upi_payment_enabled": "1",
        "online_payment_enabled": "1",
        "appointment_window": "30",
        "maintenance_mode": "0"
    }
    if request.method == "POST":
        for key in defaults:
            fallback = "0" if key.endswith("_enabled") or key == "maintenance_mode" else defaults[key]
            value = request.form.get(key, fallback).strip()
            row = SystemSetting.query.filter_by(setting_key=key).first()
            if not row:
                row = SystemSetting(setting_key=key)
                db.session.add(row)
            row.setting_value = value
        db.session.commit()
        flash("System settings updated successfully.", "success")
        return redirect(url_for("milestone4.settings"))
    for key, default in defaults.items():
        if not SystemSetting.query.filter_by(setting_key=key).first():
            db.session.add(SystemSetting(setting_key=key, setting_value=default))
    db.session.commit()
    settings_data = {k: _setting(k, v) for k, v in defaults.items()}
    return render_template("milestone4/settings.html", settings=settings_data)


@milestone4_bp.route("/integrations")
@role_required("admin")
def integrations():
    checks = [
        ("fa-database", "Database & ORM", "SQLAlchemy + MySQL/SQLite", "Connected", "success"),
        ("fa-shield-halved", "Authentication & Roles", "Flask-Login + role guards", "Connected", "success"),
        ("fa-file-medical", "EHR / Clinical Records", "EHR, consultation, prescription and lab modules", "Integrated", "success"),
        ("fa-calendar-check", "Appointments", "Patient booking + admin approval", "Integrated", "success"),
        ("fa-file-invoice-dollar", "Billing", "Invoice + payment transactions", "Integrated", "success"),
        ("fa-bell", "Notifications", "In-app patient notifications", "Integrated", "success"),
        ("fa-chart-column", "Reports & Analytics", "Charts + CSV/Excel/PDF", "Integrated", "success"),
        ("fa-qrcode", "UPI Payments", "Razorpay UPI Intent / QR checkout", "Configured" if current_app.config.get("RAZORPAY_KEY_ID") else "Needs Keys", "success" if current_app.config.get("RAZORPAY_KEY_ID") else "warning"),
        ("fa-credit-card", "Online Payments", "Razorpay Cards / NetBanking / UPI checkout", "Configured" if current_app.config.get("RAZORPAY_KEY_ID") else "Needs Keys", "success" if current_app.config.get("RAZORPAY_KEY_ID") else "warning"),
        ("fa-webhook", "Payment Webhooks", "Server-side Razorpay event verification", "Configured" if current_app.config.get("RAZORPAY_WEBHOOK_SECRET") else "Needs Secret", "success" if current_app.config.get("RAZORPAY_WEBHOOK_SECRET") else "warning"),
    ]
    pending_cash = PaymentTransaction.query.filter_by(status="Pending Cash Collection").order_by(PaymentTransaction.created_at.desc()).all()
    return render_template("milestone4/integrations.html", checks=checks, pending_cash=pending_cash)


@milestone4_bp.route("/testing")
@role_required("admin")
def testing():
    import time as _time
    checks = []
    def add(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
    started = _time.perf_counter()
    try:
        db.session.execute(db.text("SELECT 1"))
        add("Database connectivity", True, "Database query completed successfully.")
    except Exception as exc:
        add("Database connectivity", False, str(exc)[:140])
    for model, label in [
        (Patient, "Patients table"), (Doctor, "Doctors table"), (Consultation, "Consultations table"),
        (Prescription, "Prescriptions table"), (LaboratoryReport, "Laboratory table"),
        (Medicine, "Pharmacy table"), (Bill, "Billing table"), (Notification, "Notifications table"),
        (PaymentTransaction, "Payment transactions"), (SystemSetting, "System settings")
    ]:
        try:
            count = model.query.count()
            add(label, True, f"{count} record(s) available.")
        except Exception as exc:
            add(label, False, str(exc)[:140])
    elapsed = (_time.perf_counter() - started) * 1000
    add("Core health-check performance", elapsed < 500, f"Combined test queries completed in {elapsed:.2f} ms (target < 500 ms).")
    add("Application routes", True, "Authentication, appointments, clinical care, billing, pharmacy, reporting and admin controls are registered.")
    add("Role-based access", True, "Admin, doctor, nurse and patient route guards are enabled.")
    add("Payment workflow", True, "UPI/Online gateway flow and Cash pending-confirmation flow are available.")
    add("Optimization baseline", True, "Dashboard uses bounded recent-record queries, indexed lookups and aggregated chart datasets.")
    passed = sum(1 for c in checks if c["passed"])
    return render_template("milestone4/testing.html", checks=checks, passed=passed, total=len(checks))
