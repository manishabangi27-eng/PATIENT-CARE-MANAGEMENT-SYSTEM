from datetime import datetime, date
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from app import db
from app.models import Patient, Doctor, Nurse, Appointment, Consultation, Prescription, LaboratoryReport, Medicine, PharmacyDispense, Bill, Notification, LoginActivity, PaymentTransaction

milestone3_bp=Blueprint("milestone3",__name__)

def roles(*allowed):
    return login_required

def notify_patient(patient,title,message,kind="General"):
    if patient.user_id:
        db.session.add(Notification(user_id=patient.user_id,title=title,message=message,notification_type=kind,delivery_status="Delivered"))

@milestone3_bp.route("/search")
@login_required
def search():
    q=request.args.get("q","").strip(); patients=[]
    if q:
        patients=Patient.query.filter(or_(Patient.full_name.ilike(f"%{q}%"),Patient.contact_number.ilike(f"%{q}%"),Patient.email.ilike(f"%{q}%"),Patient.aadhaar_number.ilike(f"%{q}%"),db.cast(Patient.id,db.String).ilike(f"%{q}%"))).all()
    return render_template("milestone3/search.html",patients=patients,q=q)

@milestone3_bp.route("/patient/<int:patient_id>")
@login_required
def patient_detail(patient_id):
    p=Patient.query.get_or_404(patient_id)
    return render_template("milestone3/patient_detail.html",patient=p)

@milestone3_bp.route("/pharmacy",methods=["GET","POST"])
@login_required
def pharmacy():
    if request.method=="POST":
        m=Medicine(name=request.form["name"],category=request.form.get("category"),batch_number=request.form.get("batch_number"),quantity=int(request.form.get("quantity",0)),reorder_level=int(request.form.get("reorder_level",10)),unit_price=float(request.form.get("unit_price",0)),expiry_date=datetime.strptime(request.form["expiry_date"],"%Y-%m-%d").date() if request.form.get("expiry_date") else None)
        db.session.add(m); db.session.commit(); flash("Medicine added.","success"); return redirect(url_for("milestone3.pharmacy"))
    q=request.args.get("q",""); medicines=Medicine.query.filter(Medicine.name.ilike(f"%{q}%")).order_by(Medicine.name).all() if q else Medicine.query.order_by(Medicine.name).all()
    today=date.today(); return render_template("milestone3/pharmacy.html",medicines=medicines,total=Medicine.query.count(),stock=db.session.query(func.coalesce(func.sum(Medicine.quantity),0)).scalar(),low=Medicine.query.filter(Medicine.quantity<=Medicine.reorder_level).count(),expired=Medicine.query.filter(Medicine.expiry_date<today).count(),dispensed_today=PharmacyDispense.query.filter(func.date(PharmacyDispense.dispensed_at)==today).count(),patients=Patient.query.order_by(Patient.full_name).all())

@milestone3_bp.route("/pharmacy/dispense",methods=["POST"])
@login_required
def dispense():
    m=Medicine.query.get_or_404(int(request.form["medicine_id"])); qty=int(request.form["quantity"]); p=Patient.query.get_or_404(int(request.form["patient_id"]))
    if qty<=0 or m.quantity<qty: flash("Insufficient stock.","danger"); return redirect(url_for("milestone3.pharmacy"))
    m.quantity-=qty; d=PharmacyDispense(patient_id=p.id,medicine_id=m.id,quantity=qty,amount=qty*m.unit_price); db.session.add(d); notify_patient(p,"Prescription Dispensed",f"{qty} x {m.name} has been dispensed.","Pharmacy"); db.session.commit(); flash("Medicine dispensed successfully.","success"); return redirect(url_for("milestone3.pharmacy"))

@milestone3_bp.route("/billing",methods=["GET","POST"])
@login_required
def billing():
    if request.method=="POST":
        p=Patient.query.get_or_404(int(request.form["patient_id"])); c=float(request.form.get("consultation_charge",0)); l=float(request.form.get("laboratory_charge",0)); ph=float(request.form.get("pharmacy_charge",0)); o=float(request.form.get("other_charge",0)); b=Bill(patient_id=p.id,consultation_charge=c,laboratory_charge=l,pharmacy_charge=ph,other_charge=o,total_amount=c+l+ph+o,payment_method=request.form.get("payment_method"),payment_status=request.form.get("payment_status","Paid")); db.session.add(b); db.session.flush(); notify_patient(p,"Billing Update",f"Invoice #{b.id} total is INR {b.total_amount:.2f}. Payment status: {b.payment_status}.","Billing"); db.session.commit(); flash("Invoice generated and patient notified.","success"); return redirect(url_for("milestone3.billing"))
    return render_template("milestone3/billing.html",patients=Patient.query.order_by(Patient.full_name).all(),bills=Bill.query.order_by(Bill.created_at.desc()).all(),transactions=PaymentTransaction.query.order_by(PaymentTransaction.created_at.desc()).limit(20).all())

@milestone3_bp.route("/notifications")
@login_required
def notifications(): return render_template("milestone3/notifications.html",notifications=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all())
@milestone3_bp.route("/notifications/<int:id>/read",methods=["POST"])
@login_required
def read_notification(id):
    n=Notification.query.filter_by(id=id,user_id=current_user.id).first_or_404(); n.status="Read"; db.session.commit(); return redirect(url_for("milestone3.notifications"))

@milestone3_bp.route("/analytics")
@login_required
def analytics():
    stats={"patients":Patient.query.count(),"doctors":Doctor.query.count(),"nurses":Nurse.query.count(),"appointments":Appointment.query.count(),"prescriptions":Prescription.query.count(),"labs":LaboratoryReport.query.count(),"medicines":Medicine.query.count(),"bills":Bill.query.count(),"revenue":db.session.query(func.coalesce(func.sum(Bill.total_amount),0)).scalar() or 0}; return render_template("milestone3/analytics.html",stats=stats,activities=LoginActivity.query.order_by(LoginActivity.created_at.desc()).limit(20).all())

@milestone3_bp.route("/invoice/<int:id>")
@login_required
def invoice(id):
    b=Bill.query.get_or_404(id); from reportlab.pdfgen import canvas; from reportlab.lib.pagesizes import A4; buf=BytesIO(); pdf=canvas.Canvas(buf,pagesize=A4); y=780; pdf.setFont("Helvetica-Bold",18); pdf.drawString(60,y,"Integrated Patient Care - Invoice"); y-=40; pdf.setFont("Helvetica",11)
    for line in [f"Invoice: #{b.id}",f"Patient: {b.patient.full_name}",f"Consultation: INR {b.consultation_charge:.2f}",f"Laboratory: INR {b.laboratory_charge:.2f}",f"Pharmacy: INR {b.pharmacy_charge:.2f}",f"Other: INR {b.other_charge:.2f}",f"Total: INR {b.total_amount:.2f}",f"Payment: {b.payment_method or '-'} / {b.payment_status}"]:
        pdf.drawString(60,y,line); y-=24
    pdf.save(); buf.seek(0); return send_file(buf,as_attachment=True,download_name=f"invoice_{b.id}.pdf",mimetype="application/pdf")
