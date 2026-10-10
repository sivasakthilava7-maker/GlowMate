# GlowMate — Personal Self-Care AI Agent 🧴✨

GlowMate is a lightweight, reliable, and secure personal self-care AI agent designed for **skincare, haircare, body care, ingredient education, Indian product recommendations, and routine tracking**.

Built purely in **Python (compatible with Python 3.14)** using standard-library modules only (`urllib.request`, `json`, `datetime`, `re`, `hashlib`, `unittest`). GlowMate requires **no third-party frameworks** (no LangChain, CrewAI, AutoGen, or heavy SDKs) and consumes **zero API tokens for local deterministic tasks**.

---

## 🌟 Key Highlights

- **📱 Cross-Device Web App (Laptop & Phone)**: Run `python server.py` and access GlowMate from your laptop (`http://localhost:8000`) or phone (`http://<ip>:8000`) over home Wi-Fi. PWA-enabled with 1-tap "Add to Home Screen".
- **⏰ Daily Reminders & Audio Alarms**: Automated scheduled reminders for morning (AM) and evening (PM) routines using the Web Notifications API and soothing Web Audio chimes.
- **✨ 'What & When to Use Right Now' Engine**: Dynamically evaluates the current time of day and skin-cycling schedule (e.g. Exfoliant night vs Retinoid night vs Barrier recovery night) and presents immediate step-by-step guidance.
- **💾 Persistent User Data & 1-Click Check-in**: Saves user profile, active routine, reminders, and streak tracking in local JSON files (`data/`).
- **100% Local-First & Zero-Cost by Default**: Routine formulation, product searching, ingredient lookup, routine tracking, and safety triage execute offline without consuming Gemini API quota.
- **Google AI Studio Gemini REST Integration**: Leverages Gemini (`gemini-3.8-flash`) via direct REST requests using the `x-goog-api-key` header with bounded exponential backoff, rate limit handling, and structured JSON output.
- **Indian Market Catalog (INR)**: Curated database of verified pharmacy and dermatologist-tested brands (Cipla Saslic, Minimalist, Cetaphil, Sebamed, Re'equil, Scalpe Plus, Fixderma, Bioderma) across budget (< ₹400), mid-range (₹400–₹999), and premium (≥ ₹1000) tiers.
- **Deterministic Multi-Tier Safety Guardrails**: Independent Python safety engine checks for emergency anaphylaxis/throat swelling symptoms, acute adverse reactions, harmful DIY hacks (e.g. raw lemon on skin), and prescription-only medications.

---

## 📂 Project Architecture & File Tree

```
GlowMate/
│
├── agent.py                 # Core CLI loop, intent classification, envelope generator
├── config.py                # Environment configuration, timeouts, paths, sanitization
├── gemini_client.py         # Stdlib REST client (urllib), backoff, cache, usage tracking
│
├── tools/                   # Modular self-care capabilities
│   ├── __init__.py          # Tool registry exports
│   ├── profile_tool.py      # Tool A: Interactive setup wizard, storage & deletion
│   ├── skincare_tool.py     # Tool B: Personalized AM/PM routines (Cleanser, Moisturizer, SPF)
│   ├── haircare_tool.py     # Tool C: Scalp care, hair shaft protocols, alopecia flags
│   ├── bodycare_tool.py     # Tool D: Body cleansers, barrier lotions, keratosis pilaris care
│   ├── product_tool.py      # Tool E: Indian catalog search, budget filter, allergy exclusion
│   ├── ingredient_tool.py   # Tool F: Cosmetic ingredient dictionary & interaction checker
│   ├── nutrition_tool.py    # Tool G: Evidence-based nutrition education & supplement cautions
│   ├── routine_tracker.py   # Tool H: Datetime-based streak tracker & 28-day review milestone
│   └── safety_tool.py       # Tool I: Emergency, adverse reaction & prescription filter
│
├── data/
│   ├── products.json        # Curated Indian skincare & haircare catalog (INR)
│   └── profile.json         # User profile (generated locally on setup)
│
├── tests/
│   ├── __init__.py
│   ├── test_profile.py      # Profile lifecycle & hashing tests
│   ├── test_products.py     # Catalog filtering & exclusion tests
│   ├── test_safety.py       # Deterministic safety triage tests
│   ├── test_gemini_client.py# Mocked REST, retry, error sanitization tests
│   ├── test_cache.py        # Cache TTL & profile-invalidation tests
│   └── test_json_output.py  # Envelope structure verification tests
│
├── .gitignore
├── .env.example
└── README.md
```

---

## 🚀 Setup & Execution Guide (Windows PowerShell & VS Code)

### 1. Open Terminal in VS Code
In VS Code, open an integrated terminal (`Ctrl + ` `~` or **Terminal > New Terminal**). Ensure PowerShell is active.

### 2. Navigate to Project Directory
```powershell
cd C:\Users\ACER\.gemini\antigravity\scratch\GlowMate
```

### 3. Create and Activate Virtual Environment (Optional / Standard Python)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(Note: Because GlowMate uses Python's standard library, it runs directly with your system Python 3.14 without installing any pip packages!)*

### 4. Configure Gemini API Key
Obtain a free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

Set the environment variable in your active PowerShell session:
```powershell
$env:GEMINI_API_KEY = "your_actual_api_key_here"
$env:GEMINI_MODEL   = "gemini-3.8-flash"
```
To set it permanently for your Windows user account:
```powershell
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your_actual_api_key_here", "User")
```

### 5. Launch GlowMate Web App (Recommended for Laptop & Phone)
```powershell
python server.py
```
This starts the multi-threaded HTTP server:
- Open on **Laptop**: `http://localhost:8000`
- Open on **Mobile Phone**: `http://<your-laptop-ip>:8000` (e.g. `http://10.239.169.130:8000`)
*(Tip: On your phone, tap **"Add to Home Screen"** in Safari or Chrome to install GlowMate as a full-screen mobile app!)*

### 6. Alternatively, Launch GlowMate in Terminal CLI
```powershell
python agent.py
```

### 7. Run Automated Tests
Execute the comprehensive test suite (all 46 tests mock network calls, consuming zero API quota):
```powershell
python -m unittest discover -s tests -v
```

---

## 🖥️ Terminal Interactive Menu Options

```text
==================================================
                 MAIN MENU
==================================================
1.  Create or update my self-care profile
2.  View my profile
3.  Get a skincare routine
4.  Get a hair-care routine
5.  Get a body-care routine
6.  Find products by category and budget
7.  Ask about an ingredient
8.  Get nutrition and supplement information
9.  Track my daily routine
10. Ask GlowMate a general question (natural language)
11. View API usage statistics
12. Clear cached responses
13. Delete my profile
14. Exit
--------------------------------------------------
```

Users can either enter a number (`1`–`14`) or type any freeform natural language query (e.g., *"Can I use retinol and salicylic acid on the same night?"*).

---

## 📋 Standardized Structured JSON Envelope

All agent interactions generate a consistent JSON envelope:

```json
{
  "agent": "GlowMate",
  "status": "success",
  "intent": "skincare_routine",
  "summary": "Personalized Skincare Routine for Oily Skin",
  "data": {
    "morning_routine": [
      {
        "step": "1. Gentle Cleanser",
        "action": "Wash face with a gentle foaming or mild 1-2% salicylic acid cleanser.",
        "rationale": "Removes overnight sebum buildup and prevents follicular plugging."
      },
      {
        "step": "3. Oil-Free Gel Moisturizer",
        "action": "Lightweight water-based or gel moisturizer.",
        "rationale": "Hydrates without occlusive pore congestion."
      },
      {
        "step": "4. Broad-Spectrum Sunscreen (SPF 30+ / PA+++)",
        "action": "Apply two finger-lengths of photostable sunscreen.",
        "rationale": "Crucial daily barrier against UVA and UVB."
      }
    ],
    "evening_routine": [
      {
        "step": "1. Thorough Cleansing",
        "action": "Wash face thoroughly to break down daytime sunscreen.",
        "rationale": "Ensures clean pore canvas for night cellular regeneration."
      },
      {
        "step": "2. Targeted Blemish Treatment",
        "action": "Use Salicylic Acid (2%) or Azelaic Acid (10%) 2-3 nights per week.",
        "rationale": "Exfoliates pore linings and reduces bacterial colonization."
      },
      {
        "step": "3. Nourishing Night Moisturizer",
        "action": "Apply a restorative ceramide cream across face and neck.",
        "rationale": "Locks in hydration and prevents nocturnal transepidermal water loss."
      }
    ],
    "haircare": [],
    "bodycare": [],
    "product_suggestions": [],
    "nutrition_guidance": []
  },
  "safety_notes": [
    "Rule of One: Introduce only ONE new product every 2-3 weeks to isolate triggers.",
    "Always perform a 24-hour patch test on your inner forearm before applying to face."
  ],
  "follow_up_questions": [
    "Would you like recommendations for cleansers or sunscreens fitting your budget tier?"
  ],
  "timestamp": "2026-10-09T11:30:00.000000+00:00"
}
```

---

## 🛡️ Safety & Dermatological Policies

1. **Emergency Symptoms**: Any mentions of anaphylaxis, throat swelling, difficulty breathing, or severe chemical burns immediately trigger an **`emergency_blocked`** status instructing the user to contact emergency services immediately.
2. **Acute Reactions**: Users reporting severe stinging, burning, or facial swelling are advised to stop all recent products and apply cool compresses, with dermatologist referral guidance.
3. **No Medical Prescription**: GlowMate explicitly refuses requests to prescribe oral isotretinoin, oral antibiotics, systemic steroids, or prescription retinoids.
4. **Allergen Cross-Referencing**: Recommended products are checked against user-specified allergies and excluded.

---

## 🧪 Troubleshooting & Common Inquiries

- **HTTP 400 Invalid API Key**: Verify your key at [Google AI Studio](https://aistudio.google.com/app/apikey). Set it with `$env:GEMINI_API_KEY="AIzaSy..."` without extra spaces or quotes.
- **HTTP 429 Rate Limit**: The client automatically pauses and retries with exponential backoff and jitter. You can also rely on the deterministic menu options which operate 100% offline.
- **Model Availability**: The agent verifies `GEMINI_MODEL` (default: `gemini-3.8-flash`) against `/v1beta/models/{model}` upon launch.
