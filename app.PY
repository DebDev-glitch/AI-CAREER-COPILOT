from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import Base, engine, SessionLocal
from ai import analyze_resume
from dotenv import load_dotenv
import models
import json
import os

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}

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

    try:
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not email or not password:
                return render_template(
                    "signup.html",
                    error="Email and password are required."
                )

            existing_user = db.query(models.User).filter_by(
                email=email
            ).first()

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

    finally:
        db.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    db = SessionLocal()

    try:
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not email or not password:
                return render_template(
                    "login.html",
                    error="Email and password are required."
                )

            user = db.query(models.User).filter_by(
                email=email
            ).first()

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
                    if not user.password.startswith(
                        ("scrypt:", "pbkdf2:")
                    ):
                        user.password = generate_password_hash(password)
                        db.commit()

                    session["user"] = user.email

                    return redirect("/dashboard")

            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        return render_template("login.html")

    finally:
        db.close()


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    db = SessionLocal()

    try:
        if request.method == "POST":

            email = request.form.get("email", "").strip().lower()
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not email or not new_password or not confirm_password:
                return render_template(
                    "forgot_password.html",
                    error="All fields are required."
                )

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

    finally:
        db.close()


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if "user" not in session:
        return redirect("/login")

    result = None

    if request.method == "POST":

        user_goal = request.form.get("role", "").strip()
        resume_text = request.form.get("resume", "").strip()

        file = request.files.get("file")

        # File handling
        if file and file.filename:

            filename = file.filename.lower()
            file_extension = os.path.splitext(filename)[1]

            # Check file type
            if file_extension not in ALLOWED_EXTENSIONS:

                result = {
                    "error": (
                        "Unsupported file type. "
                        "Please upload a PDF or DOCX file."
                    )
                }

            else:

                # Check file size
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)

                if file_size > MAX_FILE_SIZE:

                    result = {
                        "error": (
                            "File is too large. "
                            "Please upload a file smaller than 5 MB."
                        )
                    }

                elif file_size == 0:

                    result = {
                        "error": (
                            "The uploaded file is empty. "
                            "Please choose another file."
                        )
                    }

                # PDF
                elif file_extension == ".pdf":

                    try:
                        import PyPDF2

                        pdf_reader = PyPDF2.PdfReader(file)

                        text = ""

                        for page in pdf_reader.pages:
                            text += page.extract_text() or ""

                        if not text.strip():

                            result = {
                                "error": (
                                    "Could not extract text from this PDF. "
                                    "Please upload a text-based PDF."
                                )
                            }

                        else:
                            resume_text = text.strip()

                    except Exception:

                        result = {
                            "error": (
                                "Unable to read this PDF. "
                                "Please make sure the file is not corrupted."
                            )
                        }

                # DOCX
                elif file_extension == ".docx":

                    try:
                        import docx

                        doc = docx.Document(file)

                        text = ""

                        for para in doc.paragraphs:
                            text += para.text + "\n"

                        if not text.strip():

                            result = {
                                "error": (
                                    "Could not extract text from this DOCX file. "
                                    "Please upload a valid resume."
                                )
                            }

                        else:
                            resume_text = text.strip()

                    except Exception:

                        result = {
                            "error": (
                                "Unable to read this DOCX file. "
                                "Please make sure the file is not corrupted."
                            )
                        }

        # Validate resume
        if not result:

            if not resume_text:

                result = {
                    "error": (
                        "Please upload a resume "
                        "or paste your resume text."
                    )
                }

            elif not user_goal:

                result = {
                    "error": (
                        "Please select a career goal "
                        "before analyzing your resume."
                    )
                }

        # Analyze resume
        if resume_text and user_goal and not result:

            try:

                result = analyze_resume(
                    resume_text,
                    user_goal
                )

                # Save report
                db = SessionLocal()

                try:
                    user = db.query(models.User).filter_by(
                        email=session["user"]
                    ).first()

                    if not user:
                        session.pop("user", None)
                        return redirect("/login")

                    report = models.Report(
                        user_id=user.id,
                        resume_text=resume_text,
                        result=json.dumps(result)
                    )

                    db.add(report)
                    db.commit()

                finally:
                    db.close()

            except Exception as e:

                result = {
                    "error": f"AI error: {str(e)}"
                }

    return render_template(
        "dashboard.html",
        user=session["user"],
        result=result
    )


@app.route("/history")
def history():

    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()

    try:
        user = db.query(models.User).filter_by(
            email=session["user"]
        ).first()

        if not user:
            session.pop("user", None)
            return redirect("/login")

        reports = db.query(models.Report).filter_by(
            user_id=user.id
        ).all()

        parsed_reports = []

        for report in reports:

            try:
                parsed_result = json.loads(report.result)

            except (json.JSONDecodeError, TypeError):
                parsed_result = {}

            parsed_reports.append({
                "resume": report.resume_text,
                "result": parsed_result
            })

        return render_template(
            "history.html",
            reports=parsed_reports
        )

    finally:
        db.close()


@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect("/login")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )