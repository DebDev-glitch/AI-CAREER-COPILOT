from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import Base, engine, SessionLocal
from ai import analyze_resume
from dotenv import load_dotenv
import models
import json
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

Base.metadata.create_all(bind=engine)

@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    db = SessionLocal()

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        existing_user = db.query(models.User).filter_by(email=email).first()

        if existing_user:
            return render_template(
                "signup.html",
                error="An account with this email already exists."
            )

        hashed_password = generate_password_hash(password)

        user = models.User(
            email=email,
            password=hashed_password
        )
        db.add(user)
        db.commit()

        return redirect("/login")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    db = SessionLocal()

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = db.query(models.User).filter_by(email=email).first()

        if user:
            try:
                password_valid = check_password_hash(
                    user.password,
                    password
                )
            except (ValueError, TypeError):
                password_valid = user.password == password

            if password_valid:
                # Upgrade old plain-text password to a hash
                if not user.password.startswith(("scrypt:", "pbkdf2:")):
                    user.password = generate_password_hash(password)
                    db.commit()

                session["user"] = user.email
                return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template("login.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    db = SessionLocal()

    if request.method == "POST":

        email = request.form.get("email")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            return render_template(
                "forgot_password.html",
                error="Passwords do not match."
            )

        user = db.query(models.User).filter_by(
            email=email
        ).first()

        if not user:
            return render_template(
                "forgot_password.html",
                error="This email is not registered."
            )

        hashed_password = generate_password_hash(new_password)

        user.password = hashed_password

        db.commit()

        return redirect("/login")

    return render_template("forgot_password.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")
    
    result = None

    if request.method == "POST":
        user_goal = request.form.get("role")
        resume_text = request.form.get("resume")

        file = request.files.get("file")

        # File handling
        if file and file.filename:
            if file.filename.endswith(".pdf"):
                try:
                    import PyPDF2

                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() or ""
                    resume_text = text
                except Exception as e:
                    result = {"error": f"PDF error: {str(e)}"}
            elif file.filename.endswith(".docx"):
                try:
                    import docx

                    doc = docx.Document(file)
                    text = ""
                    for para in doc.paragraphs:
                        text += para.text +"\n"
                    resume_text = text
                except Exception as e:
                    result = {"error": f"Docx error: {str(e)}"}

        if resume_text and user_goal and not result:
            try:
                result = analyze_resume(resume_text, user_goal)

                # Save to db
                db = SessionLocal()
                user = db.query(models.User).filter_by(email=session["user"]).first()

                report = models.Report(
                    user_id=user.id,
                    resume_text=resume_text,
                    result=json.dumps(result)
                    
                )

                db.add(report)
                db.commit()

            except Exception as e:
                result = {"error": f"AI error: {str(e)}"}
            
    return render_template(
        "dashboard.html",
        user=session["user"],
        result=result
    )
    
# History
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")
    
    db = SessionLocal()
    user = db.query(models.User).filter_by(email=session["user"]).first()

    reports = db.query(models.Report).filter_by(user_id=user.id).all()

    # Convert JSON string to dict
    parsed_reports = []
    for r in reports:
        try:
            parsed_result = json.loads(r.result)
        except json.JSONDecodeError:
            parsed_result = {}
        parsed_reports.append({
            "resume": r.resume_text,
            "result": parsed_result
        })
    return render_template("history.html", reports=parsed_reports)


# Logout route
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
