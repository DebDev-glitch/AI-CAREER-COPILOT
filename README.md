# AI Career Copilot

AI Career Copilot is an AI-powered career analysis web application that analyzes a user's resume against a target career role and provides personalized career guidance.

## Features

- User registration with email OTP verification
- Secure login and logout
- Forgot password with email OTP verification
- Resume upload using PDF or DOCX
- Resume text input
- Target career role selection
- AI-powered resume analysis using Google Gemini
- Career summary
- Job readiness score
- Identified skills with proficiency levels and evidence
- Missing skills with priority and reasons
- Personalized career roadmap
- Recommended projects
- Role-specific interview questions
- Resume improvement suggestions
- Analysis history
- View previous full analyses
- User-specific report access protection
- Dark mode interface
- Resume file validation and error handling

## AI Analysis

The application analyzes the resume based on the selected target role and generates structured results including:

- Career Summary
- Job Readiness Score
- Job Readiness Reason
- Skills
- Missing Skills
- Career Roadmap
- Recommended Projects
- Interview Questions
- Resume Improvements

The AI is instructed to base recommendations on evidence from the resume and avoid inventing skills, experience, projects, certifications, or achievements.

## Tech Stack

### Backend
- Python
- Flask
- SQLAlchemy
- Flask-Mail

### AI
- Google Gemini API
- Google GenAI Python SDK

### Frontend
- HTML
- CSS
- JavaScript
- Jinja2 Templates

### Database
- SQLite
- SQLAlchemy ORM

### Other Libraries
- PyPDF2
- python-docx
- python-dotenv
- Werkzeug

## Project Structure

```text
AI_CARRER_COPILOT/
│
├── app.py
├── ai.py
├── db.py
├── models.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── signup.html
│   ├── verify_otp.html
│   ├── forgot_password.html
│   ├── verify_reset_otp.html
│   ├── reset_password.html
│   ├── dashboard.html
│   ├── analysis.html
│   └── history.html
│
└── static/
    └── style.css
```