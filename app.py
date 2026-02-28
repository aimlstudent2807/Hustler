from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from config import get_config
from extensions import db, migrate


def create_app():
    """Application factory for SwasthyaSync."""
    app = Flask(__name__)
    app.config.from_object(get_config())

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Proxy fix for production behind reverse proxies
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Register blueprints
    from blueprints.auth.routes import auth_bp
    from blueprints.profile.routes import profile_bp
    from blueprints.diet.routes import diet_bp
    from blueprints.nutrition.routes import nutrition_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(diet_bp, url_prefix="/diet")
    app.register_blueprint(nutrition_bp, url_prefix="/nutrition")

    # Landing + health routes
    @app.route("/")
    def index():
        """Public landing page; redirect logged-in users to their profile."""
        from flask import redirect, render_template, session, url_for

        if session.get("user_id"):
            return redirect(url_for("profile.profile"))
        return render_template("landing.html")

    @app.route("/health")
    def health():
        return {"status": "ok", "app": "SwasthyaSync"}

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5000)

