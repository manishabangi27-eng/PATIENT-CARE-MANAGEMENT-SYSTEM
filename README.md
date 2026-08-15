
# Integrated Patient Care Management System

A full-stack Flask + MySQL/SQLite hospital management application covering patient registration, appointments, clinical records, prescriptions, laboratory reports, billing, payments, analytics, reporting, system integration, settings, testing and optimization.

## Core Technology

- Python + Flask
- Flask-SQLAlchemy
- MySQL with PyMySQL or SQLite for quick local testing
- Flask-Login role-based authentication
- HTML, CSS, Bootstrap 5
- Font Awesome icons
- Chart.js dashboards
- ReportLab PDF invoices/prescriptions
- CSV/Excel/PDF administrative reports

## Clinical Modules

The interface uses clear healthcare icons:

| Module | Icon |
|---|---|
| Electronic Health Record (EHR) | `fa-file-medical` |
| Consultation | `fa-stethoscope` |
| Prescription | `fa-prescription-bottle-medical` |
| Laboratory | `fa-flask-vial` |
| Appointment | `fa-calendar-check` |
| Billing | `fa-file-invoice-dollar` |
| Payment | `fa-credit-card` |
| System Integration | `fa-diagram-project` |
| System Settings | `fa-gear` |
| Testing & Optimization | `fa-vial-circle-check` |

## Patient Payment Workflow

1. Admin/hospital staff generates a bill.
2. The patient opens **Bills & Payments**.
3. The patient selects **UPI**, **Online**, or **Cash**.
4. UPI/Online create a Razorpay Order and open secure Razorpay Standard Checkout. The server verifies the payment signature, amount and captured status before marking the bill as paid.
5. Cash creates a **Pending Cash Collection** transaction.
6. The administrator confirms cash collection from **System Integration**.
7. The bill changes to **Paid** and remains available with its invoice.

## Admin Control Center

The admin dashboard includes:

- Patient, doctor, appointment, consultation and billing KPIs
- Appointment trends
- Revenue charts
- Patient registrations
- Doctor-wise consultations
- Patient demographics
- Diagnosis distribution
- Laboratory statistics
- Patient satisfaction
- Recent appointments and activity logs
- System Integration
- System Settings
- Testing & Optimization

## System Integration

The integration screen provides a single view of:

- Database and ORM
- Authentication and role guards
- EHR and clinical workflows
- Appointment management
- Billing and payment transactions
- Notifications
- Reports and analytics
- UPI payment hook
- Online payment hook

## System Settings

Administrators can configure:

- Hospital name
- Currency symbol
- UPI ID
- Cash payment availability
- UPI availability
- Online payment availability
- Appointment slot length
- Maintenance mode flag

## Testing & Optimization

The admin testing screen performs live application checks for:

- Database connectivity
- Required tables
- Payment transaction table
- System settings table
- Route registration
- Role-based access
- Payment workflow
- Dashboard optimization baseline

## Run in VS Code / PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
python run.py
```

Open:

`http://127.0.0.1:5000`

## MySQL

Create a database:

```sql
CREATE DATABASE ipcms;
```

Copy `.env.example` to `.env` and set:

```env
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost/ipcms
```

If `DATABASE_URL` is not configured, the application can use SQLite according to `config.py`.

## Demo Accounts

| Role | Email | Password |
|---|---|---|
| Admin | admin@ipcms.com | admin123 |
| Doctor | doctor@ipcms.com | doctor123 |
| Nurse | nurse@ipcms.com | nurse123 |
| Patient | patient@ipcms.com | patient123 |

## Important Production Note

The UPI and Online payment routes in this academic/demo project intentionally simulate successful payment confirmation. They do **not** process real money. For deployment, integrate a verified payment provider, validate webhook signatures, use HTTPS, add CSRF protection, move secrets to environment variables, and perform database migrations instead of relying only on `db.create_all()`.

## Database Changes

New tables:

- `payment_transactions`
- `system_settings`

The application creates them automatically on startup for a fresh database. For an existing production database, apply a proper migration.

## Project Structure

```text
Integrated_Patient_Care_System/
├── app/
│   ├── models.py
│   ├── routes/
│   ├── templates/
│   └── static/
├── config.py
├── database.sql
├── seed.py
├── requirements.txt
├── run.py
└── README.md
```

## Real-Money Payments

The patient billing workflow supports **Razorpay Standard Checkout** for real UPI/online payments, with server-side order creation, payment-signature verification, amount verification, captured-status verification, and webhook verification. Cash remains a manual counter workflow.

See `REAL_MONEY_PAYMENTS.md` for setup, Test Mode, Live Mode, webhook configuration, and production checklist.
=======
# PATIENT-CARE-MANAGEMENT-SYSTEM
>>>>>>> d35da359fc4964199e6b06c30dd13baed817251a
