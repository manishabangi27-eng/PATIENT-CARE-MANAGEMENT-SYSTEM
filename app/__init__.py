from flask import Flask, g, request
import time
from collections import defaultdict, deque
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    # Lightweight request-performance monitor used by the System Status module.
    # It keeps only a small in-memory rolling window, so it has negligible
    # storage overhead and does not add a database write to every request.
    app.extensions["performance_metrics"] = defaultdict(lambda: {"count": 0, "total_ms": 0.0, "recent_ms": deque(maxlen=20)})

    @app.before_request
    def _performance_timer():
        g._request_started_at = time.perf_counter()

    @app.after_request
    def _record_performance(response):
        started = getattr(g, "_request_started_at", None)
        if started is not None:
            elapsed_ms = (time.perf_counter() - started) * 1000
            key = request.endpoint or request.path
            metric = app.extensions["performance_metrics"][key]
            metric["count"] += 1
            metric["total_ms"] += elapsed_ms
            metric["recent_ms"].append(elapsed_ms)
        return response

    from app.models import User
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.doctor import doctor_bp
    from app.routes.nurse import nurse_bp
    from app.routes.patient import patient_bp
    from app.routes.clinical import clinical_bp
    from app.routes.milestone3 import milestone3_bp
    from app.routes.api import api_bp
    from app.routes.milestone4 import milestone4_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(doctor_bp, url_prefix="/doctor")
    app.register_blueprint(nurse_bp, url_prefix="/nurse")
    app.register_blueprint(patient_bp, url_prefix="/patient")
    app.register_blueprint(clinical_bp, url_prefix="/clinical")
    app.register_blueprint(milestone3_bp, url_prefix="/milestone3")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(milestone4_bp, url_prefix="/milestone4")

    with app.app_context():
        (Path(app.instance_path)).mkdir(parents=True, exist_ok=True)
        db.create_all()
        # Lightweight schema upgrade for existing installations.
        # This keeps the payment gateway fields available without requiring
        # users to delete their existing database.
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if "payment_transactions" in inspector.get_table_names():
            existing = {c["name"] for c in inspector.get_columns("payment_transactions")}
            additions = {
                "gateway": "VARCHAR(40)",
                "gateway_order_id": "VARCHAR(100)",
                "gateway_payment_id": "VARCHAR(100)",
                "gateway_signature": "VARCHAR(128)",
                "gateway_status": "VARCHAR(40)",
            }
            for name, sql_type in additions.items():
                if name not in existing:
                    with db.engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE payment_transactions ADD COLUMN {name} {sql_type}"))

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    return app
