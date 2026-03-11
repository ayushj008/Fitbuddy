# 🏋️ FitBuddy – AI Fitness Plan Generator

> **Powered by Google Gemini 2.0 Flash · Built with FastAPI · SQLite Database**

![FitBuddy Banner](https://img.shields.io/badge/AI-Gemini%202.0%20Flash-blue?style=for-the-badge&logo=google)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.11-yellow?style=for-the-badge&logo=python)
![SQLite](https://img.shields.io/badge/SQLite-Database-lightblue?style=for-the-badge&logo=sqlite)

---

## 📌 Project Overview

**FitBuddy** is a web-based AI fitness application that uses **Google Gemini 2.0 Flash** to generate personalized 7-day workout plans and nutrition tips. Users provide their fitness goals, body metrics, and preferences, and Gemini AI crafts a fully structured, goal-specific training schedule.

### 🎯 Three Core Scenarios

| Scenario | Description |
|----------|-------------|
| **1. Plan Generation** | AI generates a personalized 7-day workout plan based on user profile, goal, and intensity |
| **2. Feedback Refinement** | Users submit feedback to regenerate and improve their plan (e.g., "more cardio") |
| **3. Nutrition Tips** | AI provides goal-specific dietary and recovery recommendations |

---

## 🚀 Features

- 🤖 **Gemini 2.0 Flash** integration for AI plan generation
- 💪 **5 fitness goals**: Weight Loss, Muscle Gain, General Wellness, Endurance, Flexibility
- ⚡ **3 intensity levels**: Low (Beginner), Medium (Intermediate), High (Advanced)
- 🔄 **Adaptive feedback loop** — refine plans dynamically
- 🥗 **Nutrition tips** tailored to each fitness goal
- 💾 **SQLite persistence** — all plans and feedback stored in database
- 📱 **Responsive HTML interface** — works on desktop and mobile
- 🔗 **REST API** — clean FastAPI endpoints for all operations

---

## 🛠️ Tech Stack

```
Backend:    FastAPI (Python 3.11)
AI Model:   Google Gemini 2.0 Flash (google-generativeai SDK)
Database:   SQLite (via sqlite3 standard library)
Frontend:   HTML5 + CSS3 + Vanilla JavaScript (single-file SPA)
Server:     Uvicorn ASGI
```

---

## 📁 Project Structure

```
fitbuddy/
├── main.py              # FastAPI backend & Gemini AI integration
├── requirements.txt     # Python dependencies
├── fitbuddy.db          # SQLite database (auto-created on startup)
├── static/
│   └── index.html       # Single-page frontend (HTML/CSS/JS)
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/fitbuddy.git
cd fitbuddy
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set your Gemini API key
```bash
# Option 1: Environment variable (recommended)
export GEMINI_API_KEY="your-gemini-api-key-here"

# Option 2: Edit main.py directly (not recommended for production)
GEMINI_API_KEY = "your-gemini-api-key-here"
```

> Get your free Gemini API key at: https://aistudio.google.com/app/apikey

### 5. Set up static files
```bash
mkdir static
cp index.html static/index.html
```

### 6. Run the server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Open in browser
```
http://localhost:8000
```

---

## 📡 API Endpoints

### `POST /api/generate-plan`
Generate a personalized 7-day workout plan.

**Request Body:**
```json
{
  "name": "Alex Johnson",
  "age": 25,
  "gender": "Male",
  "weight": 75.5,
  "height": 178,
  "goal": "Weight Loss",
  "intensity": "Medium",
  "days_per_week": 4,
  "equipment": ["Dumbbells", "Gym Access"],
  "injuries": "mild lower back sensitivity",
  "fitness_level": "intermediate",
  "preferred_time": "Morning"
}
```

**Response:**
```json
{
  "plan_id": 1,
  "user_name": "Alex Johnson",
  "goal": "Weight Loss",
  "intensity": "Medium",
  "plan_json": { "plan_title": "...", "days": [...] },
  "nutrition_tip": "...",
  "generated_at": "2025-01-01T10:00:00"
}
```

---

### `POST /api/update-plan`
Refine an existing plan with user feedback.

**Request Body:**
```json
{
  "plan_id": 1,
  "feedback_text": "Please add more cardio and reduce upper body exercises",
  "chips": ["More Cardio", "Focus on Core"]
}
```

---

### `GET /api/nutrition-tip/{goal}`
Get an AI-generated nutrition tip for a specific goal.

**Example:** `GET /api/nutrition-tip/Muscle Gain`

**Response:**
```json
{
  "goal": "Muscle Gain",
  "tip": "Prioritize 1.6–2.2g protein per kg bodyweight...",
  "generated_at": "2025-01-01T10:00:00",
  "model": "gemini-2.0-flash"
}
```

---

### `GET /api/plans`
Retrieve all saved plans.

### `GET /api/plans/{plan_id}`
Retrieve a specific plan by ID.

### `DELETE /api/plans/{plan_id}`
Delete a fitness plan.

---

## 🗃️ Database Schema

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    weight REAL,
    height REAL,
    created_at TEXT
);

-- Plans table
CREATE TABLE fitness_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    goal TEXT NOT NULL,
    intensity TEXT NOT NULL,
    days_per_week INTEGER,
    equipment TEXT,        -- JSON array
    injuries TEXT,
    fitness_level TEXT,
    preferred_time TEXT,
    plan_json TEXT NOT NULL,     -- Full Gemini-generated plan
    nutrition_tip TEXT,
    feedback_history TEXT,       -- JSON array of feedback records
    created_at TEXT,
    updated_at TEXT
);

-- Feedback table
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER REFERENCES fitness_plans(id),
    feedback_text TEXT NOT NULL,
    chips TEXT,            -- JSON array of quick-select options
    created_at TEXT
);
```

---

## 🤖 Gemini AI Integration Details

FitBuddy uses `google-generativeai` Python SDK with **Gemini 2.0 Flash**:

```python
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Generate plan
response = model.generate_content(plan_prompt)
plan_json = json.loads(response.text)
```

### Prompt Engineering
- **Plan generation prompt**: Includes user profile, goals, equipment, injuries; requests structured JSON output
- **Feedback prompt**: Sends original plan + user feedback; requests targeted modifications
- **Nutrition prompt**: Goal-specific nutritional advice with macros, timing, and food recommendations

---

## 👥 Team

Built as a **Healthcare** track project for the Gemini AI Hackathon.

| Role | Contribution |
|------|-------------|
| Backend Developer | FastAPI, Gemini API integration, SQLite |
| Frontend Developer | HTML/CSS/JS single-page application |
| AI/ML Engineer | Prompt engineering, response parsing |

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 🙏 Acknowledgments

- [Google Gemini AI](https://deepmind.google/technologies/gemini/) for the powerful language model
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent Python web framework
- [Google AI Studio](https://aistudio.google.com/) for API key management

---

*Built with ❤️ and 💪 by the FitBuddy Team*
