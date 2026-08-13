# Enhanced Admin, Notification & Performance Modules

This build adds the requested hospital-management enhancements:

- Admin dashboard Pharmacy module with a pills icon and direct inventory access.
- Admin Patient Notification Center with bell icon.
- Patient notifications for billing, laboratory reports and pharmacy dispensing.
- Read/unread notification state visible to patients and administrators.
- Expanded hospital management charts, including consultations by department.
- System Status module covering:
  - overall system performance overview
  - performance optimization
  - top API performance
  - system performance trend
  - all-system operational checks
  - consultations by department
  - module activity/performance overview
- Testing module now includes a combined health-check performance target.
- Reports expanded to EHR, pharmacy inventory, dispensing, notifications and system activity.
- Login page redesigned with an ICMP Hospital Care van background illustration.
- Lightweight in-memory request timing tracks API endpoint performance without a database write on every request.
- Pharmacy and billing use INR formatting and patient notifications.

## Run

1. Create/activate your Python virtual environment.
2. Install `requirements.txt`.
3. Configure `DATABASE_URL` and Razorpay settings in `.env` if required.
4. Run `python seed.py` once to create demo records.
5. Run `python app.py` / `python run.py` according to the project's existing setup.

The application uses `db.create_all()` and contains a lightweight schema upgrade for existing installations. Always keep a backup of a production database before applying application upgrades.
