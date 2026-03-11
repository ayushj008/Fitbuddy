"""
FitBuddy – AI Fitness Plan Generator
FastAPI Backend with Google Gemini AI Integration
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import json
import os
import google.generativeai as genai
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-api-key-here")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

app = FastAPI(
    title="FitBuddy API",
    description="AI-powered fitness plan generator using Google Gemini",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================
# DATABASE SETUP (SQLite)
# ============================================================
DB_PATH = "fitbuddy.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            weight REAL,
            height REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS fitness_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            goal TEXT NOT NULL,
            intensity TEXT NOT NULL,
            days_per_week INTEGER DEFAULT 4,
            equipment TEXT,
            injuries TEXT,
            fitness_level TEXT,
            preferred_time TEXT,
            plan_json TEXT NOT NULL,
            nutrition_tip TEXT,
            feedback_history TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            feedback_text TEXT NOT NULL,
            chips TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (plan_id) REFERENCES fitness_plans(id)
        );
    """)
    conn.commit()
    conn.close()

init_db()

# ============================================================
# PYDANTIC MODELS
# ============================================================
class UserProfile(BaseModel):
    name: str
    age: int
    gender: str = "Male"
    weight: float
    height: Optional[float] = None
    goal: str
    intensity: str = "Medium"
    days_per_week: int = 4
    equipment: List[str] = []
    injuries: Optional[str] = None
    fitness_level: Optional[str] = None
    preferred_time: str = "Morning"

class FeedbackRequest(BaseModel):
    plan_id: int
    feedback_text: str
    chips: List[str] = []

class PlanResponse(BaseModel):
    plan_id: int
    user_name: str
    goal: str
    intensity: str
    plan_json: dict
    nutrition_tip: str
    generated_at: str

# ============================================================
# GEMINI AI PROMPTS
# ============================================================
def build_plan_prompt(user: UserProfile) -> str:
    equipment_str = ", ".join(user.equipment) if user.equipment else "no equipment"
    injuries_str = user.injuries if user.injuries else "none"
    return f"""You are FitBuddy, an expert AI fitness coach. Generate a detailed, personalized 7-day workout plan.

USER PROFILE:
- Name: {user.name}
- Age: {user.age} | Gender: {user.gender}
- Weight: {user.weight}kg | Height: {user.height or 'not specified'}cm
- Primary Goal: {user.goal}
- Workout Intensity: {user.intensity}
- Preferred Time: {user.preferred_time}
- Days Per Week: {user.days_per_week}
- Available Equipment: {equipment_str}
- Injuries/Limitations: {injuries_str}
- Current Fitness Level: {user.fitness_level or 'not specified'}

INSTRUCTIONS:
1. Create a structured 7-day plan with rest days distributed appropriately
2. Each workout day should include 4–6 exercises with sets, reps, and rest periods
3. Match difficulty to the {user.intensity} intensity level
4. Respect any injuries — avoid contraindicated exercises
5. Align exercises with available equipment
6. Include warm-up and cool-down reminders

Return ONLY a JSON object in this exact format:
{{
  "plan_title": "string",
  "days": [
    {{
      "day_number": 1,
      "day_name": "Monday",
      "focus": "string (e.g. Chest & Triceps)",
      "is_rest": false,
      "duration_min": "45-55 min",
      "calories_burned": "300-400",
      "exercises": [
        {{
          "name": "string",
          "sets": 3,
          "reps": "12",
          "rest_seconds": 60,
          "notes": "string",
          "category": "Compound|Isolation|Cardio|Core|Recovery"
        }}
      ]
    }}
  ]
}}"""

def build_feedback_prompt(original_plan: dict, feedback: str, chips: List[str]) -> str:
    chips_str = ", ".join(chips) if chips else "none"
    return f"""You are FitBuddy AI. A user wants to update their workout plan based on feedback.

ORIGINAL PLAN SUMMARY:
{json.dumps(original_plan, indent=2)[:2000]}

USER FEEDBACK:
- Written feedback: "{feedback}"
- Quick selections: {chips_str}

TASK: Regenerate a modified 7-day plan that addresses this feedback. Return the SAME JSON format as the original plan but with the requested modifications applied.

Keep what's working, change what the user requested. Maintain the original goal and overall structure."""

def build_nutrition_prompt(goal: str) -> str:
    return f"""You are a certified sports nutritionist. Provide a comprehensive, personalized nutrition tip for someone with the fitness goal: "{goal}".

Include:
1. Key macronutrient recommendations
2. Meal timing advice (pre/post workout)
3. 2–3 specific food recommendations
4. One optional supplement recommendation
5. One lifestyle tip (sleep, hydration, etc.)

Keep it practical, evidence-based, and under 150 words. No lists — write as flowing advice."""

# ============================================================
# ROUTES
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main FitBuddy HTML interface"""
    with open("static/index.html", "r") as f:
        return f.read()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "FitBuddy API", "model": "gemini-2.0-flash"}

# --- SCENARIO 1: Generate Plan ---
@app.post("/api/generate-plan", response_model=PlanResponse)
async def generate_plan(user: UserProfile, db: sqlite3.Connection = Depends(get_db)):
    """
    Scenario 1: Generate a personalized 7-day workout plan using Gemini AI
    based on user profile, fitness goal, and intensity level.
    """
    try:
        # Save user to DB
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (name, age, gender, weight, height) VALUES (?,?,?,?,?)",
            (user.name, user.age, user.gender, user.weight, user.height)
        )
        user_id = cursor.lastrowid

        # Generate plan with Gemini
        plan_prompt = build_plan_prompt(user)
        plan_response = model.generate_content(plan_prompt)
        plan_text = plan_response.text.strip()

        # Clean up JSON (remove markdown code blocks if present)
        if "```json" in plan_text:
            plan_text = plan_text.split("```json")[1].split("```")[0].strip()
        elif "```" in plan_text:
            plan_text = plan_text.split("```")[1].split("```")[0].strip()

        plan_json = json.loads(plan_text)

        # Generate nutrition tip
        nut_prompt = build_nutrition_prompt(user.goal)
        nut_response = model.generate_content(nut_prompt)
        nutrition_tip = nut_response.text.strip()

        # Save plan to DB
        cursor.execute(
            """INSERT INTO fitness_plans 
               (user_id, goal, intensity, days_per_week, equipment, injuries, 
                fitness_level, preferred_time, plan_json, nutrition_tip)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user_id, user.goal, user.intensity, user.days_per_week,
             json.dumps(user.equipment), user.injuries, user.fitness_level,
             user.preferred_time, json.dumps(plan_json), nutrition_tip)
        )
        plan_id = cursor.lastrowid
        db.commit()

        return PlanResponse(
            plan_id=plan_id,
            user_name=user.name,
            goal=user.goal,
            intensity=user.intensity,
            plan_json=plan_json,
            nutrition_tip=nutrition_tip,
            generated_at=datetime.now().isoformat()
        )

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse Gemini response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {str(e)}")

# --- SCENARIO 2: Update Plan with Feedback ---
@app.post("/api/update-plan")
async def update_plan(req: FeedbackRequest, db: sqlite3.Connection = Depends(get_db)):
    """
    Scenario 2: Update an existing workout plan based on user feedback.
    Uses Gemini AI to regenerate and refine the plan intelligently.
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM fitness_plans WHERE id = ?", (req.plan_id,))
    plan_row = cursor.fetchone()

    if not plan_row:
        raise HTTPException(status_code=404, detail="Plan not found")

    try:
        original_plan = json.loads(plan_row["plan_json"])

        # Generate updated plan with Gemini
        feedback_prompt = build_feedback_prompt(original_plan, req.feedback_text, req.chips)
        response = model.generate_content(feedback_prompt)
        updated_text = response.text.strip()

        if "```json" in updated_text:
            updated_text = updated_text.split("```json")[1].split("```")[0].strip()
        elif "```" in updated_text:
            updated_text = updated_text.split("```")[1].split("```")[0].strip()

        updated_plan = json.loads(updated_text)

        # Save feedback record
        cursor.execute(
            "INSERT INTO feedback (plan_id, feedback_text, chips) VALUES (?,?,?)",
            (req.plan_id, req.feedback_text, json.dumps(req.chips))
        )

        # Update feedback history on plan
        feedback_history = json.loads(plan_row["feedback_history"] or "[]")
        feedback_history.append({
            "text": req.feedback_text,
            "chips": req.chips,
            "timestamp": datetime.now().isoformat()
        })

        # Update plan in DB
        cursor.execute(
            """UPDATE fitness_plans 
               SET plan_json = ?, feedback_history = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (json.dumps(updated_plan), json.dumps(feedback_history), req.plan_id)
        )
        db.commit()

        return {
            "plan_id": req.plan_id,
            "updated_plan": updated_plan,
            "feedback_applied": req.feedback_text,
            "updated_at": datetime.now().isoformat(),
            "message": "Plan successfully updated by Gemini AI based on your feedback"
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse Gemini response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan update failed: {str(e)}")

# --- SCENARIO 3: Get Nutrition Tip ---
@app.get("/api/nutrition-tip/{goal}")
async def get_nutrition_tip(goal: str):
    """
    Scenario 3: Get a personalized nutrition or recovery tip based on fitness goal.
    Uses Gemini AI to generate relevant dietary and recovery advice.
    """
    valid_goals = ["Weight Loss", "Muscle Gain", "General Wellness", "Endurance", "Flexibility"]
    if goal not in valid_goals:
        raise HTTPException(status_code=400, detail=f"Invalid goal. Choose from: {valid_goals}")

    try:
        prompt = build_nutrition_prompt(goal)
        response = model.generate_content(prompt)
        tip = response.text.strip()

        return {
            "goal": goal,
            "tip": tip,
            "generated_at": datetime.now().isoformat(),
            "model": "gemini-2.0-flash"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Nutrition tip generation failed: {str(e)}")

# --- Get all saved plans ---
@app.get("/api/plans")
async def get_all_plans(db: sqlite3.Connection = Depends(get_db)):
    """Retrieve all saved fitness plans with user info"""
    cursor = db.cursor()
    cursor.execute("""
        SELECT fp.id, fp.goal, fp.intensity, fp.created_at, fp.updated_at,
               fp.days_per_week, fp.nutrition_tip,
               u.name, u.age, u.weight
        FROM fitness_plans fp
        JOIN users u ON fp.user_id = u.id
        ORDER BY fp.created_at DESC
    """)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

# --- Get single plan ---
@app.get("/api/plans/{plan_id}")
async def get_plan(plan_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Retrieve a specific fitness plan by ID"""
    cursor = db.cursor()
    cursor.execute("""
        SELECT fp.*, u.name, u.age, u.weight, u.gender
        FROM fitness_plans fp
        JOIN users u ON fp.user_id = u.id
        WHERE fp.id = ?
    """, (plan_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")
    result = dict(row)
    result["plan_json"] = json.loads(result["plan_json"])
    result["feedback_history"] = json.loads(result.get("feedback_history") or "[]")
    return result

# --- Delete plan ---
@app.delete("/api/plans/{plan_id}")
async def delete_plan(plan_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Delete a fitness plan"""
    cursor = db.cursor()
    cursor.execute("DELETE FROM fitness_plans WHERE id = ?", (plan_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Plan not found")
    db.commit()
    return {"message": f"Plan {plan_id} deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
