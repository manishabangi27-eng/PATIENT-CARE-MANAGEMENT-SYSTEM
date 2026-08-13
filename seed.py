from app import create_app, db
from app.models import User, Patient, Doctor, Nurse, Medicine, Bill, Appointment, Consultation, LaboratoryReport, PatientFeedback, PaymentTransaction, SystemSetting, Notification

app = create_app()

with app.app_context():
    db.create_all()

    demo = [
        ("System Admin", "admin@ipcms.com", "9999999999", "Admin", "admin123"),
        ("Dr. John", "doctor@ipcms.com", "9999999998", "Doctor", "doctor123"),
        ("Nurse Priya", "nurse@ipcms.com", "9999999997", "Nurse", "nurse123"),
        ("Rahul Patient", "patient@ipcms.com", "9999999996", "Patient", "patient123"),
        ("Pharmacy Manager", "pharmacist@ipcms.com", "9999999995", "Pharmacist", "pharma123"),
        ("Lab Staff", "lab@ipcms.com", "9999999994", "Laboratory Staff", "lab123"),
    ]

    for name, email, phone, role, password in demo:
        if not User.query.filter_by(email=email).first():
            user = User(full_name=name, email=email, phone=phone, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            if role == "Patient":
                db.session.add(Patient(user_id=user.id, full_name=name, contact_number=phone))
            elif role == "Doctor":
                db.session.add(Doctor(user_id=user.id, doctor_name=name, specialization="General Medicine", department="Medicine", contact_number=phone, email=email, available_time="10:00 AM - 4:00 PM"))
            elif role == "Nurse":
                db.session.add(Nurse(user_id=user.id, nurse_name=name, department="General Ward", contact_number=phone, email=email))

    if Doctor.query.count() < 2:
        db.session.add(Doctor(doctor_name="Dr. Priya", specialization="Cardiology", qualification="MBBS, MD", department="Cardiology", contact_number="9000000001", email="priya.doctor@ipcms.com", available_time="10:00 AM - 2:00 PM"))
        db.session.add(Doctor(doctor_name="Dr. Rahul", specialization="Pediatrics", qualification="MBBS, MD", department="Pediatrics", contact_number="9000000002", email="rahul.doctor@ipcms.com", available_time="2:00 PM - 6:00 PM"))

    if Medicine.query.count() == 0:
        db.session.add_all([Medicine(name="Paracetamol",category="Tablet",batch_number="PCM001",quantity=100,reorder_level=20,unit_price=2.5),Medicine(name="Amoxicillin",category="Capsule",batch_number="AMX001",quantity=50,reorder_level=10,unit_price=5.0)])
    # Milestone 4 demo records make analytics, billing and feedback visible immediately.
    patient = Patient.query.filter_by(email="patient@ipcms.com").first()
    doctor = Doctor.query.filter_by(email="doctor@ipcms.com").first()
    if patient and doctor:
        if Bill.query.filter_by(patient_id=patient.id).count() == 0:
            db.session.add(Bill(patient_id=patient.id, consultation_charge=500, laboratory_charge=750,
                                pharmacy_charge=250, other_charge=100, total_amount=1600,
                                payment_method="UPI", payment_status="Paid"))
            db.session.add(Bill(patient_id=patient.id, consultation_charge=400, laboratory_charge=600,
                                pharmacy_charge=0, other_charge=0, total_amount=1000,
                                payment_method="Cash", payment_status="Pending"))
        if Appointment.query.filter_by(patient_id=patient.id).count() == 0:
            from datetime import date, timedelta, time
            db.session.add(Appointment(patient_id=patient.id, doctor_id=doctor.id,
                appointment_date=date.today(), appointment_time=time(10,30), status="Accepted"))
            db.session.add(Appointment(patient_id=patient.id, doctor_id=doctor.id,
                appointment_date=date.today()-timedelta(days=2), appointment_time=time(11,0), status="Completed"))
        if PatientFeedback.query.filter_by(patient_id=patient.id).count() == 0:
            db.session.add(PatientFeedback(patient_id=patient.id, doctor_id=doctor.id,
                department=doctor.department, consultation_rating=5, hospital_rating=4,
                laboratory_rating=5, pharmacy_rating=4, comments="Good service and clear consultation."))
        if Notification.query.filter_by(user_id=patient.user_id).count() == 0:
            db.session.add(Notification(
                user_id=patient.user_id,
                title="Welcome to ICMP Hospital",
                message="Your patient portal is active. Billing, laboratory reports, pharmacy updates and hospital announcements will appear here.",
                notification_type="General",
                status="Unread",
                delivery_status="Delivered"
            ))

    # Payment and system configuration demo data.
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
    for key, value in defaults.items():
        if not SystemSetting.query.filter_by(setting_key=key).first():
            db.session.add(SystemSetting(setting_key=key, setting_value=value))

    db.session.commit()
    print("Database initialized and demo data created.")
