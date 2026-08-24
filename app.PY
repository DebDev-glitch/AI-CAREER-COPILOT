from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import Base, engine, SessionLocal
from ai import analyze_resume
from dotenv import load_dotenv
from datetime import datetime, timedelta
from flask_mail import Mail, Message
import secrets
import models
import json
import os


MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


load_dotenv()


app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")


# =========================
# MAIL CONFIGURATION
# =========================

app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.getenv(
    "MAIL_USE_TLS",
    "true"
).lower() == "true"

app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")


mail = Mail(app)


Base.metadata.create_all(bind=engine)



# HOME


@app.route("/")
def home():

    if "user" in session:
        return redirect("/dashboard")

    return redirect("/login")



# SIGN UP


@app.route("/signup", methods=["GET", "POST"])
def signup():

    db = SessionLocal()

    try:

        if request.method == "POST":

            username = request.form.get(
                "username",
                ""
            ).strip()

            email = request.form.get(
                "email",
                ""
            ).strip().lower()

            password = request.form.get(
                "password",
                ""
            )

    
            # Required fields
    

            if not username or not email or not password:

                return render_template(
                    "signup.html",
                    error="Please fill in all fields."
                )

    
            # Username validation
    

            if len(username) < 3:

                return render_template(
                    "signup.html",
                    error="Username must be at least 3 characters."
                )

    
            # Check existing user
    

            existing_user = db.query(
                models.User
            ).filter(
                (models.User.email == email) |
                (models.User.username == username)
            ).first()

            if existing_user:

                if existing_user.email == email:
                    error = "An account with this email already exists."

                else:
                    error = "This username is already taken."

                return render_template(
                    "signup.html",
                    error=error
                )

    
            # Remove old pending user
    

            pending_user = db.query(
                models.PendingUser
            ).filter(
                (models.PendingUser.email == email) |
                (models.PendingUser.username == username)
            ).first()

            if pending_user:

                db.delete(pending_user)
                db.commit()

    
            # Hash password
    

            hashed_password = generate_password_hash(
                password
            )

    
            # Generate OTP
    

            otp = str(
                secrets.randbelow(900000) + 100000
            )

    
            # Create pending user
    

            pending_user = models.PendingUser(
                username=username,
                email=email,
                password=hashed_password,
                otp=otp,
                otp_expires_at=datetime.utcnow()
                + timedelta(minutes=10)
            )

            db.add(pending_user)
            db.commit()

    
            # Send verification email
    

            try:

                message = Message(
                    subject="AI Career Copilot - Email Verification",
                    sender=app.config["MAIL_USERNAME"],
                    recipients=[email]
                )

                message.body = f"""
Hello {username},

Your AI Career Copilot verification code is:

{otp}

This code will expire in 10 minutes.

If you did not create this account, you can ignore this email.

AI Career Copilot
"""

                mail.send(message)

            except Exception:

                db.delete(pending_user)
                db.commit()

                return render_template(
                    "signup.html",
                    error="Unable to send verification email. Please try again."
                )

    
            # Save verification email
    

            session["verification_email"] = email

            return redirect("/verify-otp")

        return render_template("signup.html")

    finally:

        db.close()



# VERIFY SIGNUP OTP


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    email = session.get(
        "verification_email"
    )

    if not email:
        return redirect("/signup")

    db = SessionLocal()

    try:

        pending_user = db.query(
            models.PendingUser
        ).filter_by(
            email=email
        ).first()

        if not pending_user:

            session.pop(
                "verification_email",
                None
            )

            return redirect("/signup")

        if request.method == "POST":

            otp = request.form.get(
                "otp",
                ""
            ).strip()

    
            # Empty OTP
    

            if not otp:

                return render_template(
                    "verify_otp.html",
                    error="Please enter the verification code.",
                    email=email
                )

    
            # Invalid OTP
    

            if pending_user.otp != otp:

                return render_template(
                    "verify_otp.html",
                    error="Invalid verification code.",
                    email=email
                )

    
            # Expired OTP
    

            if datetime.utcnow() > pending_user.otp_expires_at:

                return render_template(
                    "verify_otp.html",
                    error="Verification code has expired. Please request a new one.",
                    email=email
                )

    
            # Create actual user
    

            user = models.User(
                username=pending_user.username,
                email=pending_user.email,
                password=pending_user.password,
                is_verified=1,
                otp=None,
                otp_expires_at=None
            )

            db.add(user)

            db.delete(pending_user)

            db.commit()

    
            # Clear signup session
    

            session.pop(
                "verification_email",
                None
            )

            return redirect("/login")

        return render_template(
            "verify_otp.html",
            email=email
        )

    finally:

        db.close()



# RESEND SIGNUP OTP


@app.route("/resend-otp", methods=["POST"])
def resend_otp():

    email = session.get(
        "verification_email"
    )

    if not email:
        return redirect("/signup")

    db = SessionLocal()

    try:

        pending_user = db.query(
            models.PendingUser
        ).filter_by(
            email=email
        ).first()

        if not pending_user:

            session.pop(
                "verification_email",
                None
            )

            return redirect("/signup")


        # Generate new OTP


        otp = str(
            secrets.randbelow(900000) + 100000
        )

        pending_user.otp = otp

        pending_user.otp_expires_at = (
            datetime.utcnow()
            + timedelta(minutes=10)
        )

        db.commit()


        # Send new OTP


        try:

            message = Message(
                subject="AI Career Copilot - New Verification Code",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email]
            )

            message.body = f"""
Hello {pending_user.username},

Your new AI Career Copilot verification code is:

{otp}

This code will expire in 10 minutes.

AI Career Copilot
"""

            mail.send(message)

        except Exception:

            return render_template(
                "verify_otp.html",
                error="Unable to send a new verification code.",
                email=email
            )

        return render_template(
            "verify_otp.html",
            email=email,
            message="A new verification code has been sent."
        )

    finally:

        db.close()



# LOGIN


@app.route("/login", methods=["GET", "POST"])
def login():

    db = SessionLocal()

    try:

        if request.method == "POST":

            email = request.form.get(
                "email",
                ""
            ).strip().lower()

            password = request.form.get(
                "password",
                ""
            )

    
            # Find user
    

            user = db.query(
                models.User
            ).filter_by(
                email=email
            ).first()

            if not user:

                return render_template(
                    "login.html",
                    error="Invalid email or password."
                )

    
            # Check verification
    

            if not user.is_verified:

                session["verification_email"] = user.email

                return render_template(
                    "login.html",
                    error="Please verify your email before logging in."
                )

    
            # Check password
    

            try:

                password_valid = check_password_hash(
                    user.password,
                    password
                )

            except (ValueError, TypeError):

                password_valid = False

            if password_valid:

                session["user"] = user.email

                return redirect("/dashboard")

            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        return render_template("login.html")

    finally:

        db.close()



# FORGOT PASSWORD


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    db = SessionLocal()

    try:

        if request.method == "POST":

            email = request.form.get(
                "email",
                ""
            ).strip().lower()

    
            # Email required
    

            if not email:

                return render_template(
                    "forgot_password.html",
                    error="Please enter your email address."
                )

    
            # Find user
    

            user = db.query(
                models.User
            ).filter_by(
                email=email
            ).first()

            if not user:

                return render_template(
                    "forgot_password.html",
                    error="No account found with this email."
                )

    
            # Check account verification
    

            if not user.is_verified:

                return render_template(
                    "forgot_password.html",
                    error="Please verify your account first."
                )

    
            # Generate reset OTP
    

            otp = str(
                secrets.randbelow(900000) + 100000
            )

            user.otp = otp

            user.otp_expires_at = (
                datetime.utcnow()
                + timedelta(minutes=10)
            )

            db.commit()

    
            # Send reset OTP
    

            try:

                message = Message(
                    subject="AI Career Copilot - Password Reset",
                    sender=app.config["MAIL_USERNAME"],
                    recipients=[email]
                )

                message.body = f"""
Hello {user.username},

Your password reset verification code is:

{otp}

This code will expire in 10 minutes.

If you did not request a password reset, please ignore this email.

AI Career Copilot
"""

                mail.send(message)

            except Exception:

                user.otp = None
                user.otp_expires_at = None

                db.commit()

                return render_template(
                    "forgot_password.html",
                    error="Unable to send verification email. Please try again."
                )

    
            # Save reset email
    

            session["reset_email"] = email

            # Remove previous reset verification
            session.pop(
                "reset_verified",
                None
            )

    
            # GO TO OTP PAGE
    

            return redirect("/verify-reset-otp")

        return render_template(
            "forgot_password.html"
        )

    finally:

        db.close()



# VERIFY PASSWORD RESET OTP


@app.route("/verify-reset-otp", methods=["GET", "POST"])
def verify_reset_otp():

    email = session.get(
        "reset_email"
    )

    # User did not request password reset
    if not email:

        return redirect("/forgot-password")

    db = SessionLocal()

    try:

        user = db.query(
            models.User
        ).filter_by(
            email=email
        ).first()

        if not user:

            session.pop(
                "reset_email",
                None
            )

            return redirect("/forgot-password")


        # Verify OTP


        if request.method == "POST":

            otp = request.form.get(
                "otp",
                ""
            ).strip()

            # Empty OTP
            if not otp:

                return render_template(
                    "verify_reset_otp.html",
                    error="Please enter the verification code.",
                    email=email
                )

            # Wrong OTP
            if user.otp != otp:

                return render_template(
                    "verify_reset_otp.html",
                    error="Invalid verification code.",
                    email=email
                )

            # No expiry time
            if not user.otp_expires_at:

                return render_template(
                    "verify_reset_otp.html",
                    error="Verification code has expired.",
                    email=email
                )

            # Expired OTP
            if datetime.utcnow() > user.otp_expires_at:

                return render_template(
                    "verify_reset_otp.html",
                    error="Verification code has expired. Please request a new one.",
                    email=email
                )

    
            # OTP SUCCESS
    

            session["reset_verified"] = True

            return redirect("/reset-password")

        return render_template(
            "verify_reset_otp.html",
            email=email
        )

    finally:

        db.close()



# RESET PASSWORD


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    email = session.get(
        "reset_email"
    )

    reset_verified = session.get(
        "reset_verified"
    )

    # Must request reset first

    if not email:

        return redirect("/forgot-password")

    # Must verify OTP first

    if not reset_verified:

        return redirect("/verify-reset-otp")

    db = SessionLocal()

    try:

        user = db.query(
            models.User
        ).filter_by(
            email=email
        ).first()

        if not user:

            session.pop(
                "reset_email",
                None
            )

            session.pop(
                "reset_verified",
                None
            )

            return redirect("/forgot-password")


        # Change password


        if request.method == "POST":

            new_password = request.form.get(
                "new_password",
                ""
            )

            confirm_password = request.form.get(
                "confirm_password",
                ""
            )

    
            # Minimum length
    

            if len(new_password) < 6:

                return render_template(
                    "reset_password.html",
                    error="Password must be at least 6 characters."
                )

    
            # Uppercase
    

            if not any(
                char.isupper()
                for char in new_password
            ):

                return render_template(
                    "reset_password.html",
                    error="Password must contain an uppercase letter."
                )

    
            # Special character
    

            if not any(
                not char.isalnum()
                for char in new_password
            ):

                return render_template(
                    "reset_password.html",
                    error="Password must contain a special character."
                )

    
            # Confirm password
    

            if new_password != confirm_password:

                return render_template(
                    "reset_password.html",
                    error="Passwords do not match."
                )

    
            # Update password
    

            user.password = generate_password_hash(
                new_password
            )

            # Clear OTP after successful reset

            user.otp = None

            user.otp_expires_at = None

            db.commit()

    
            # Clear reset session
    

            session.pop(
                "reset_email",
                None
            )

            session.pop(
                "reset_verified",
                None
            )

    
            # Back to login
    

            return redirect("/login")

        return render_template(
            "reset_password.html"
        )

    finally:

        db.close()


# DASHBOARD

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if "user" not in session:

        return redirect("/login")

    result = None

    if request.method == "POST":

        user_goal = request.form.get(
            "role",
            ""
        ).strip()

        resume_text = request.form.get(
            "resume",
            ""
        ).strip()

        file = request.files.get(
            "file"
        )


        # File upload


        if file and file.filename:

            filename = file.filename.lower()

            file_extension = os.path.splitext(
                filename
            )[1]

    
            # File type

            if file_extension not in ALLOWED_EXTENSIONS:

                result = {
                    "error": (
                        "Unsupported file type. "
                        "Please upload a PDF or DOCX file."
                    )
                }

            else:

        
                # File size
        

                file.seek(
                    0,
                    os.SEEK_END
                )

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

                        pdf_reader = PyPDF2.PdfReader(
                            file
                        )

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

                        doc = docx.Document(
                            file
                        )

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


        # AI Analysis


        if resume_text and user_goal and not result:

            try:

                result = analyze_resume(
                    resume_text,
                    user_goal
                )

                db = SessionLocal()

                try:

                    user = db.query(
                        models.User
                    ).filter_by(
                        email=session["user"]
                    ).first()

                    if not user:

                        session.pop(
                            "user",
                            None
                        )

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



# HISTORY


@app.route("/history")
def history():

    if "user" not in session:

        return redirect("/login")

    db = SessionLocal()

    try:

        user = db.query(
            models.User
        ).filter_by(
            email=session["user"]
        ).first()

        if not user:

            session.pop(
                "user",
                None
            )

            return redirect("/login")

        reports = db.query(
            models.Report
        ).filter_by(
            user_id=user.id
        ).all()

        parsed_reports = []

        for report in reports:

            try:

                parsed_result = json.loads(
                    report.result
                )

            except (
                json.JSONDecodeError,
                TypeError
            ):

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



# LOGOUT
@app.route("/logout")
def logout():

    session.pop(
        "user",
        None
    )

    return redirect("/login")



# RUN APPLICATION


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )