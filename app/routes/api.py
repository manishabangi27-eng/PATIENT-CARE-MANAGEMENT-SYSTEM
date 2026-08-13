from flask import Blueprint,request,jsonify
from flask_login import login_required
from app import db
from app.models import Patient,Doctor,Consultation,Prescription,LaboratoryReport
api_bp=Blueprint("api",__name__)
def patient_json(p): return {"id":p.id,"full_name":p.full_name,"age":p.age,"gender":p.gender,"phone":p.contact_number,"email":p.email,"aadhaar":p.aadhaar_number,"address":p.address,"blood_group":p.blood_group}
@api_bp.route("/docs")
def docs(): return jsonify({"name":"IPCMS Milestone 3 API","endpoints":["GET/POST /patients","GET/PUT/DELETE /patients/<id>","GET/POST /doctors","GET/POST /consultations","GET/POST /prescriptions","GET/POST /laboratory" ]})
@api_bp.route("/patients",methods=["GET","POST"])
@login_required
def patients():
    if request.method=="POST":
        d=request.get_json() or {}; p=Patient(full_name=d.get("full_name",""),age=d.get("age"),gender=d.get("gender"),contact_number=d.get("phone"),email=d.get("email"),aadhaar_number=d.get("aadhaar"),address=d.get("address"),blood_group=d.get("blood_group")); db.session.add(p); db.session.commit(); return jsonify(patient_json(p)),201
    return jsonify([patient_json(p) for p in Patient.query.all()])
@api_bp.route("/patients/<int:id>",methods=["GET","PUT","DELETE"])
@login_required
def patient(id):
    p=Patient.query.get_or_404(id)
    if request.method=="GET": return jsonify(patient_json(p))
    if request.method=="DELETE": db.session.delete(p); db.session.commit(); return jsonify({"message":"deleted"})
    d=request.get_json() or {}; p.full_name=d.get("full_name",p.full_name); p.contact_number=d.get("phone",p.contact_number); p.email=d.get("email",p.email); p.aadhaar_number=d.get("aadhaar",p.aadhaar_number); db.session.commit(); return jsonify(patient_json(p))
@api_bp.route("/<resource>",methods=["GET"])
@login_required
def collection(resource):
    mp={"doctors":Doctor,"consultations":Consultation,"prescriptions":Prescription,"laboratory":LaboratoryReport}; M=mp.get(resource)
    if not M:return jsonify({"error":"unknown resource"}),404
    rows=M.query.all(); return jsonify([{c.name:getattr(x,c.name) for c in M.__table__.columns} for x in rows])
