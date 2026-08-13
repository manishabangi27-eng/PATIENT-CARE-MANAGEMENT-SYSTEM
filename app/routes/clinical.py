from functools import wraps
from datetime import datetime
from io import BytesIO

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, make_response
from flask_login import login_required, current_user
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app import db
from app.models import (
    User, Patient, Doctor, ElectronicHealthRecord,
    Consultation, Prescription, LaboratoryReport, MedicalRecord, Notification
)

clinical_bp = Blueprint("clinical", __name__)


def clinical_required(roles=("doctor", "nurse", "admin")):
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role.lower() not in roles:
                flash("You do not have permission to access clinical management.", "danger")
                return redirect(url_for("main.dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def doctor_required(f):
    return clinical_required(("doctor",))(f)


def get_doctor():
    return Doctor.query.filter(
        (Doctor.user_id == current_user.id) | (Doctor.email == current_user.email)
    ).first()


def get_or_create_ehr(patient):
    ehr = ElectronicHealthRecord.query.filter_by(patient_id=patient.id).first()
    if not ehr:
        ehr = ElectronicHealthRecord(patient_id=patient.id)
        db.session.add(ehr)
        db.session.flush()
    return ehr


@clinical_bp.route("/ehr")
@clinical_required(("doctor", "nurse", "admin"))
def ehr_search():
    q = request.args.get("q", "").strip()
    patients = []
    if q:
        patients = Patient.query.filter(
            db.or_(
                Patient.full_name.ilike(f"%{q}%"),
                db.cast(Patient.id, db.String).ilike(f"%{q}%")
            )
        ).order_by(Patient.full_name).all()
    return render_template("clinical/ehr_search.html", patients=patients, q=q)


@clinical_bp.route("/ehr/<int:patient_id>", methods=["GET", "POST"])
@clinical_required(("doctor", "nurse", "admin"))
def ehr_detail(patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("clinical.ehr_search"))

    ehr = get_or_create_ehr(patient)
    if request.method == "POST":
        ehr.allergies = request.form.get("allergies", "").strip()
        ehr.medical_history = request.form.get("medical_history", "").strip()
        ehr.previous_diagnoses = request.form.get("previous_diagnoses", "").strip()
        ehr.current_medications = request.form.get("current_medications", "").strip()
        db.session.commit()
        flash("EHR updated successfully.", "success")
        return redirect(url_for("clinical.ehr_detail", patient_id=patient.id))

    return render_template(
        "clinical/ehr_detail.html",
        patient=patient, ehr=ehr,
        consultations=Consultation.query.filter_by(patient_id=patient.id).order_by(
            Consultation.consultation_date.desc()).all(),
        prescriptions=Prescription.query.filter_by(patient_id=patient.id).order_by(
            Prescription.prescribed_at.desc()).all(),
        lab_reports=LaboratoryReport.query.filter_by(patient_id=patient.id).order_by(
            LaboratoryReport.test_date.desc()).all()
    )


@clinical_bp.route("/consultations")
@doctor_required
def consultations():
    doctor = get_doctor()
    records = Consultation.query.filter_by(doctor_id=doctor.id).order_by(
        Consultation.consultation_date.desc()).all() if doctor else []
    return render_template("clinical/consultations.html", consultations=records)


@clinical_bp.route("/consultations/new", methods=["GET", "POST"])
@doctor_required
def new_consultation():
    doctor = get_doctor()
    patients = Patient.query.order_by(Patient.full_name).all()
    if not doctor:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for("doctor.dashboard"))

    if request.method == "POST":
        patient = db.session.get(Patient, int(request.form["patient_id"]))
        if not patient:
            flash("Patient not found.", "danger")
            return redirect(url_for("clinical.new_consultation"))

        consultation = Consultation(
            patient_id=patient.id,
            doctor_id=doctor.id,
            symptoms=request.form.get("symptoms", "").strip(),
            diagnosis=request.form.get("diagnosis", "").strip(),
            treatment=request.form.get("treatment", "").strip()
        )
        db.session.add(consultation)

        record = MedicalRecord(
            patient_id=patient.id,
            doctor_id=doctor.id,
            diagnosis=consultation.diagnosis,
            notes=f"Symptoms: {consultation.symptoms}\nTreatment: {consultation.treatment}"
        )
        db.session.add(record)

        ehr = get_or_create_ehr(patient)
        if consultation.diagnosis:
            old = ehr.previous_diagnoses or ""
            ehr.previous_diagnoses = (old + "\n" if old else "") + consultation.diagnosis

        db.session.commit()
        return render_template("clinical/consultation_summary.html",
                               consultation=consultation)

    return render_template("clinical/consultation_form.html", patients=patients)


@clinical_bp.route("/prescriptions")
@doctor_required
def prescriptions():
    doctor = get_doctor()
    records = Prescription.query.filter_by(doctor_id=doctor.id).order_by(
        Prescription.prescribed_at.desc()).all() if doctor else []
    return render_template("clinical/prescriptions.html", prescriptions=records)


@clinical_bp.route("/prescriptions/new", methods=["GET", "POST"])
@doctor_required
def new_prescription():
    doctor = get_doctor()
    patients = Patient.query.order_by(Patient.full_name).all()
    if request.method == "POST":
        patient = db.session.get(Patient, int(request.form["patient_id"]))
        if not patient:
            flash("Patient not found.", "danger")
            return redirect(url_for("clinical.new_prescription"))

        prescription = Prescription(
            patient_id=patient.id, doctor_id=doctor.id,
            medicine_name=request.form["medicine_name"].strip(),
            dosage=request.form.get("dosage", "").strip(),
            frequency=request.form.get("frequency", "").strip(),
            duration=request.form.get("duration", "").strip(),
            special_instructions=request.form.get("special_instructions", "").strip()
        )
        db.session.add(prescription)
        ehr = get_or_create_ehr(patient)
        medication_line = f"{prescription.medicine_name} - {prescription.dosage} - {prescription.frequency} - {prescription.duration}"
        old = ehr.current_medications or ""
        ehr.current_medications = (old + "\n" if old else "") + medication_line
        db.session.commit()
        return render_template("clinical/prescription_summary.html", prescription=prescription)

    return render_template("clinical/prescription_form.html", patients=patients)


@clinical_bp.route("/prescriptions/<int:prescription_id>/download")
@login_required
def download_prescription(prescription_id):
    prescription = db.session.get(Prescription, prescription_id)
    if not prescription:
        flash("Prescription not found.", "danger")
        return redirect(url_for("main.dashboard"))

    role = current_user.role.lower()
    if role == "patient":
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient or patient.id != prescription.patient_id:
            flash("Access denied.", "danger")
            return redirect(url_for("main.dashboard"))
    elif role == "doctor":
        doctor = get_doctor()
        if not doctor or doctor.id != prescription.doctor_id:
            flash("Access denied.", "danger")
            return redirect(url_for("main.dashboard"))
    elif role not in ("nurse", "admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("main.dashboard"))

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 70
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(60, y, "Integrated Patient Care - Digital Prescription")
    y -= 40
    pdf.setFont("Helvetica", 11)
    lines = [
        f"Patient: {prescription.patient.full_name}",
        f"Doctor: {prescription.doctor.doctor_name}",
        f"Date: {prescription.prescribed_at.strftime('%Y-%m-%d %H:%M')}",
        f"Medicine: {prescription.medicine_name}",
        f"Dosage: {prescription.dosage or '-'}",
        f"Frequency: {prescription.frequency or '-'}",
        f"Duration: {prescription.duration or '-'}",
        f"Special Instructions: {prescription.special_instructions or '-'}",
    ]
    for line in lines:
        pdf.drawString(60, y, line[:110])
        y -= 24
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f"prescription_{prescription.id}.pdf",
                     mimetype="application/pdf")


@clinical_bp.route("/laboratory")
@clinical_required(("doctor", "nurse", "admin"))
def laboratory():
    role = current_user.role.lower()
    if role == "doctor":
        doctor = get_doctor()
        reports = LaboratoryReport.query.filter_by(doctor_id=doctor.id).order_by(
            LaboratoryReport.test_date.desc()).all() if doctor else []
    else:
        reports = LaboratoryReport.query.order_by(LaboratoryReport.test_date.desc()).all()
    return render_template("clinical/laboratory.html", reports=reports)


@clinical_bp.route("/laboratory/new", methods=["GET", "POST"])
@doctor_required
def new_laboratory_report():
    doctor = get_doctor()
    patients = Patient.query.order_by(Patient.full_name).all()
    if request.method == "POST":
        patient = db.session.get(Patient, int(request.form["patient_id"]))
        test_date = datetime.strptime(request.form["test_date"], "%Y-%m-%d").date()
        report = LaboratoryReport(
            patient_id=patient.id, doctor_id=doctor.id,
            test_type=request.form["test_type"].strip(),
            test_date=test_date,
            result=request.form.get("result", "").strip(),
            remarks=request.form.get("remarks", "").strip()
        )
        db.session.add(report)
        db.session.flush()
        if patient.user_id:
            db.session.add(Notification(
                user_id=patient.user_id,
                title="Laboratory Report Updated",
                message=f"Your {report.test_type} laboratory report is now available in your patient portal.",
                notification_type="Laboratory Report",
                status="Unread",
                delivery_status="Delivered"
            ))
        db.session.commit()
        return render_template("clinical/lab_summary.html", report=report)
    return render_template("clinical/lab_form.html", patients=patients)


@clinical_bp.route("/history")
@clinical_required(("doctor", "nurse", "admin"))
def medical_history():
    q = request.args.get("q", "").strip()
    patients = []
    selected = None
    if q:
        patients = Patient.query.filter(
            db.or_(Patient.full_name.ilike(f"%{q}%"),
                   db.cast(Patient.id, db.String).ilike(f"%{q}%"))
        ).order_by(Patient.full_name).all()
    patient_id = request.args.get("patient_id", type=int)
    if patient_id:
        selected = db.session.get(Patient, patient_id)
    return render_template("clinical/history.html", patients=patients, selected=selected, q=q)


@clinical_bp.route("/history/<int:patient_id>")
@clinical_required(("doctor", "nurse", "admin"))
def history_detail(patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("clinical.medical_history"))
    ehr = get_or_create_ehr(patient)
    consultations = Consultation.query.filter_by(patient_id=patient.id).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).all()
    labs = LaboratoryReport.query.filter_by(patient_id=patient.id).all()
    events = []
    for x in consultations:
        events.append((x.consultation_date, "Consultation", x))
    for x in prescriptions:
        events.append((x.prescribed_at, "Prescription", x))
    for x in labs:
        events.append((x.created_at, "Laboratory Report", x))
    events.sort(key=lambda item: item[0], reverse=True)
    return render_template("clinical/history_detail.html", patient=patient, ehr=ehr,
                           consultations=consultations, prescriptions=prescriptions,
                           labs=labs, events=events)


@clinical_bp.route("/reports")
@clinical_required(("doctor", "nurse", "admin"))
def reports_search():
    q = request.args.get("q", "").strip()
    patients = []
    if q:
        patients = Patient.query.filter(
            db.or_(Patient.full_name.ilike(f"%{q}%"),
                   db.cast(Patient.id, db.String).ilike(f"%{q}%"))
        ).order_by(Patient.full_name).all()
    return render_template("clinical/reports_search.html", patients=patients, q=q)


@clinical_bp.route("/reports/<int:patient_id>")
@clinical_required(("doctor", "nurse", "admin"))
def patient_report(patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("clinical.reports_search"))
    ehr = get_or_create_ehr(patient)
    consultations = Consultation.query.filter_by(patient_id=patient.id).order_by(
        Consultation.consultation_date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(
        Prescription.prescribed_at.desc()).all()
    labs = LaboratoryReport.query.filter_by(patient_id=patient.id).order_by(
        LaboratoryReport.test_date.desc()).all()
    return render_template("clinical/patient_report.html", patient=patient, ehr=ehr,
                           consultations=consultations, prescriptions=prescriptions,
                           labs=labs)


@clinical_bp.route("/reports/<int:patient_id>/print")
@clinical_required(("doctor", "nurse", "admin"))
def print_patient_report(patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("clinical.reports_search"))
    ehr = get_or_create_ehr(patient)
    consultations = Consultation.query.filter_by(patient_id=patient.id).order_by(
        Consultation.consultation_date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(
        Prescription.prescribed_at.desc()).all()
    labs = LaboratoryReport.query.filter_by(patient_id=patient.id).order_by(
        LaboratoryReport.test_date.desc()).all()
    return render_template("clinical/patient_report.html", patient=patient, ehr=ehr,
                           consultations=consultations, prescriptions=prescriptions,
                           labs=labs, print_mode=True)
