# Onboarding + Settings + DailyBread Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement required onboarding flow (blocks dashboard until complete), editable settings page (syncs to adeline-brain), and integrate daily scripture widget that adapts Adeline's lessons to student profile.

**Architecture:** Student profile is stored in adeline-brain Postgres User table. Onboarding is a required first-time gate. Settings allows edits via PATCH endpoint. DailyBreadWidget fetches scripture and sends study prompts to Adeline chat. All agents read student profile (grade, interests, pacing, etc.) to customize lessons.

**Tech Stack:** Next.js 16.2.2 (adeline-ui) + FastAPI (adeline-brain) + Prisma 7.6.0 + PostgreSQL + React 19 + Tailwind CSS.

---

## File Structure

### adeline-brain (Backend)
- `prisma/schema.prisma` — Add User table columns (gradeLevel, interests, learningStyle, etc.)
- `prisma/migrations/2026040X_add_onboarding_fields/migration.sql` — Migration file
- `app/api/onboarding.py` — POST, PATCH, GET endpoints for onboarding

### adeline-ui (Frontend)
- `src/app/onboarding/page.tsx` — Page wrapper for onboarding flow
- `src/components/onboarding/WelcomeFlow.tsx` — Multi-step wizard (5 steps)
- `src/app/settings/page.tsx` — Settings page
- `src/components/settings/SettingsForm.tsx` — Form component for editing preferences
- `src/components/daily-bread/DailyBreadWidget.tsx` — Existing widget, minor updates
- `src/app/(routes)/layout.tsx` — Add onboarding gate check

---

## Phase 1: Database & API (adeline-brain)

### Task 1: Add User table columns to Prisma schema

**Files:**
- Modify: `adeline-brain/prisma/schema.prisma`

- [ ] **Step 1: Add new columns to User model**

Open `adeline-brain/prisma/schema.prisma` and find the `model User` block. Add the following columns after the existing fields but before `lessons`:

```prisma
model User {
  id                String   @id @default(uuid())
  name              String
  email             String   @unique
  role              UserRole
  gradeLevel        String?

  // Subject-specific grade level overrides
  mathLevel         Int?
  elaLevel          Int?
  scienceLevel      Int?
  historyLevel      Int?

  // Learning preferences
  interests         String[]
  learningStyle     String?
  pacingMultiplier  Float?

  // State & graduation tracking
  state             String?
  targetGraduationYear Int?

  // Onboarding gate
  onboardingComplete Boolean @default(false)

  lessons           StudentLesson[]
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt

  @@index([role])
  @@index([email])
  @@index([onboardingComplete])
}
```

- [ ] **Step 2: Run Prisma migration creation**

```bash
cd adeline-brain
npx prisma migrate dev --name add_onboarding_fields
```

Expected: Prisma creates a new migration file in `prisma/migrations/` and asks if you want to apply it. Say yes.

- [ ] **Step 3: Verify migration applied**

```bash
npx prisma db push
```

Expected: Migration applies successfully to the database. You should see "Your database is now in sync with your schema."

- [ ] **Step 4: Regenerate Prisma client**

```bash
npx prisma generate
```

Expected: No errors. Prisma client is updated with new User fields.

- [ ] **Step 5: Commit**

```bash
git add adeline-brain/prisma/schema.prisma "adeline-brain/prisma/migrations/*/migration.sql"
git commit -m "db: Add onboarding fields to User table (grade, interests, pacing, state, graduation year)"
```

---

### Task 2: Implement GET /api/onboarding endpoint

**Files:**
- Create: `adeline-brain/app/api/onboarding.py`

- [ ] **Step 1: Create the onboarding.py file with GET endpoint**

Create `adeline-brain/app/api/onboarding.py`:

```python
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

@router.get("/")
async def get_onboarding(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch current student profile"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = db.query(User).filter(User.id == current_user["userId"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return JSONResponse({
        "ok": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "gradeLevel": user.gradeLevel,
            "mathLevel": user.mathLevel,
            "elaLevel": user.elaLevel,
            "scienceLevel": user.scienceLevel,
            "historyLevel": user.historyLevel,
            "interests": user.interests or [],
            "learningStyle": user.learningStyle,
            "pacingMultiplier": user.pacingMultiplier or 1.0,
            "state": user.state,
            "targetGraduationYear": user.targetGraduationYear,
            "onboardingComplete": user.onboardingComplete,
        }
    })
```

- [ ] **Step 2: Register router in main FastAPI app**

Open `adeline-brain/app/main.py` and add this import and router registration after other routers:

```python
from app.api import onboarding

app.include_router(onboarding.router)
```

- [ ] **Step 3: Test the endpoint locally**

```bash
cd adeline-brain
uvicorn app.main:app --reload --port 8000
```

Then in another terminal, test with curl (replace with actual token):

```bash
curl -X GET http://localhost:8000/api/onboarding \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected: Returns 200 with user profile or 401 if not authenticated.

- [ ] **Step 4: Commit**

```bash
git add adeline-brain/app/api/onboarding.py adeline-brain/app/main.py
git commit -m "feat: Add GET /api/onboarding endpoint to fetch student profile"
```

---

### Task 3: Implement POST /api/onboarding endpoint

**Files:**
- Modify: `adeline-brain/app/api/onboarding.py`

- [ ] **Step 1: Add POST endpoint to onboarding.py**

Add this function to `adeline-brain/app/api/onboarding.py`:

```python
from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime

class OnboardingRequest(BaseModel):
    name: str
    gradeLevel: str
    interests: List[str]
    learningStyle: str
    state: str
    targetGraduationYear: int
    coppaConsent: bool

    @validator('gradeLevel')
    def validate_grade(cls, v):
        valid_grades = ['K'] + [str(i) for i in range(1, 13)]
        if v not in valid_grades:
            raise ValueError('gradeLevel must be K or 1-12')
        return v

    @validator('learningStyle')
    def validate_learning_style(cls, v):
        if v not in ['EXPEDITION', 'CLASSIC']:
            raise ValueError('learningStyle must be EXPEDITION or CLASSIC')
        return v

    @validator('targetGraduationYear')
    def validate_year(cls, v):
        current_year = datetime.now().year
        if v < current_year or v > current_year + 20:
            raise ValueError(f'targetGraduationYear must be between {current_year} and {current_year + 20}')
        return v

    @validator('state')
    def validate_state(cls, v):
        valid_states = ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
                       'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
                       'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
                       'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
                       'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
                       'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
                       'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
                       'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
                       'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
                       'West Virginia', 'Wisconsin', 'Wyoming']
        if v not in valid_states:
            raise ValueError(f'{v} is not a valid US state')
        return v

@router.post("/")
async def post_onboarding(
    req: OnboardingRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initial onboarding submission (first-time setup)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not req.coppaConsent:
        raise HTTPException(status_code=400, detail="COPPA consent required")

    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    if not req.interests or len(req.interests) == 0:
        raise HTTPException(status_code=400, detail="At least one interest must be selected")

    user = db.query(User).filter(User.id == current_user["userId"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user with onboarding data
    user.name = req.name
    user.gradeLevel = req.gradeLevel
    user.interests = req.interests
    user.learningStyle = req.learningStyle
    user.state = req.state
    user.targetGraduationYear = req.targetGraduationYear
    user.onboardingComplete = True

    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"[Onboarding] User {user.id} completed onboarding: {user.name}, grade {user.gradeLevel}, interests {user.interests}")

    return JSONResponse({
        "ok": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "gradeLevel": user.gradeLevel,
            "interests": user.interests or [],
            "learningStyle": user.learningStyle,
            "state": user.state,
            "targetGraduationYear": user.targetGraduationYear,
            "onboardingComplete": user.onboardingComplete,
        }
    })
```

- [ ] **Step 2: Test POST endpoint locally**

```bash
curl -X POST http://localhost:8000/api/onboarding \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Emma Johnson",
    "gradeLevel": "5",
    "interests": ["Gardening", "Science"],
    "learningStyle": "EXPEDITION",
    "state": "Oklahoma",
    "targetGraduationYear": 2030,
    "coppaConsent": true
  }'
```

Expected: Returns 200 with updated user object and `onboardingComplete: true`.

- [ ] **Step 3: Test validation errors**

Test missing COPPA consent:

```bash
curl -X POST http://localhost:8000/api/onboarding \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Emma Johnson",
    "gradeLevel": "5",
    "interests": ["Gardening"],
    "learningStyle": "EXPEDITION",
    "state": "Oklahoma",
    "targetGraduationYear": 2030,
    "coppaConsent": false
  }'
```

Expected: Returns 400 with error message "COPPA consent required".

- [ ] **Step 4: Commit**

```bash
git add adeline-brain/app/api/onboarding.py
git commit -m "feat: Add POST /api/onboarding endpoint with validation"
```

---

### Task 4: Implement PATCH /api/onboarding endpoint

**Files:**
- Modify: `adeline-brain/app/api/onboarding.py`

- [ ] **Step 1: Add PATCH request model and endpoint**

Add this to `adeline-brain/app/api/onboarding.py`:

```python
from typing import Optional

class OnboardingPatchRequest(BaseModel):
    gradeLevel: Optional[str] = None
    mathLevel: Optional[int] = None
    elaLevel: Optional[int] = None
    scienceLevel: Optional[int] = None
    historyLevel: Optional[int] = None
    interests: Optional[List[str]] = None
    learningStyle: Optional[str] = None
    pacingMultiplier: Optional[float] = None
    state: Optional[str] = None
    targetGraduationYear: Optional[int] = None

    @validator('gradeLevel', pre=True, always=False)
    def validate_grade_patch(cls, v):
        if v is not None:
            valid_grades = ['K'] + [str(i) for i in range(1, 13)]
            if v not in valid_grades:
                raise ValueError('gradeLevel must be K or 1-12')
        return v

    @validator('mathLevel', 'elaLevel', 'scienceLevel', 'historyLevel', pre=True, always=False)
    def validate_subject_level(cls, v):
        if v is not None and (v < 0 or v > 12):
            raise ValueError('Subject level must be 0-12 (where 0 = K)')
        return v

    @validator('pacingMultiplier', pre=True, always=False)
    def validate_pacing(cls, v):
        if v is not None and v not in [1.0, 1.25, 1.5, 2.0]:
            raise ValueError('pacingMultiplier must be 1.0, 1.25, 1.5, or 2.0')
        return v

    @validator('learningStyle', pre=True, always=False)
    def validate_learning_style_patch(cls, v):
        if v is not None and v not in ['EXPEDITION', 'CLASSIC']:
            raise ValueError('learningStyle must be EXPEDITION or CLASSIC')
        return v

    @validator('targetGraduationYear', pre=True, always=False)
    def validate_year_patch(cls, v):
        if v is not None:
            current_year = datetime.now().year
            if v < current_year or v > current_year + 20:
                raise ValueError(f'targetGraduationYear must be between {current_year} and {current_year + 20}')
        return v

    @validator('state', pre=True, always=False)
    def validate_state_patch(cls, v):
        if v is not None:
            valid_states = ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
                           'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
                           'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
                           'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
                           'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
                           'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
                           'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
                           'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
                           'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
                           'West Virginia', 'Wisconsin', 'Wyoming']
            if v not in valid_states:
                raise ValueError(f'{v} is not a valid US state')
        return v

@router.patch("/")
async def patch_onboarding(
    req: OnboardingPatchRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update student profile from Settings page"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = db.query(User).filter(User.id == current_user["userId"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update only provided fields
    if req.gradeLevel is not None:
        user.gradeLevel = req.gradeLevel
    if req.mathLevel is not None:
        user.mathLevel = req.mathLevel
    if req.elaLevel is not None:
        user.elaLevel = req.elaLevel
    if req.scienceLevel is not None:
        user.scienceLevel = req.scienceLevel
    if req.historyLevel is not None:
        user.historyLevel = req.historyLevel
    if req.interests is not None:
        user.interests = req.interests
    if req.learningStyle is not None:
        user.learningStyle = req.learningStyle
    if req.pacingMultiplier is not None:
        user.pacingMultiplier = req.pacingMultiplier
    if req.state is not None:
        user.state = req.state
    if req.targetGraduationYear is not None:
        user.targetGraduationYear = req.targetGraduationYear

    db.add(user)
    db.commit()
    db.refresh(user)

    # TODO: Clear cached journey plan or learning state if implemented in future

    print(f"[Onboarding PATCH] User {user.id} updated profile")

    return JSONResponse({
        "ok": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "gradeLevel": user.gradeLevel,
            "mathLevel": user.mathLevel,
            "elaLevel": user.elaLevel,
            "scienceLevel": user.scienceLevel,
            "historyLevel": user.historyLevel,
            "interests": user.interests or [],
            "learningStyle": user.learningStyle,
            "pacingMultiplier": user.pacingMultiplier or 1.0,
            "state": user.state,
            "targetGraduationYear": user.targetGraduationYear,
            "onboardingComplete": user.onboardingComplete,
        }
    })
```

- [ ] **Step 2: Test PATCH endpoint locally**

```bash
curl -X PATCH http://localhost:8000/api/onboarding \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "gradeLevel": "6",
    "pacingMultiplier": 1.25,
    "interests": ["Coding", "Gardening"]
  }'
```

Expected: Returns 200 with updated user object showing new grade, pacing, and interests.

- [ ] **Step 3: Test partial updates**

Update only one field:

```bash
curl -X PATCH http://localhost:8000/api/onboarding \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "learningStyle": "CLASSIC"
  }'
```

Expected: Returns 200 with learningStyle updated, other fields unchanged.

- [ ] **Step 4: Commit**

```bash
git add adeline-brain/app/api/onboarding.py
git commit -m "feat: Add PATCH /api/onboarding endpoint for settings updates"
```

---

## Phase 2: Onboarding UI (adeline-ui)

### Task 5: Create onboarding/page.tsx wrapper

**Files:**
- Create: `adeline-ui/src/app/onboarding/page.tsx`

- [ ] **Step 1: Create onboarding page**

Create `adeline-ui/src/app/onboarding/page.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { WelcomeFlow } from '@/components/onboarding/WelcomeFlow';

interface OnboardingData {
  name: string;
  gradeLevel: string;
  interests: string[];
  learningStyle: string;
  state: string;
  targetGraduationYear: number;
  coppaConsent: boolean;
}

export default function OnboardingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    // Check if user is already onboarded
    const checkOnboarding = async () => {
      try {
        const res = await fetch('/api/onboarding');
        if (res.status === 401) {
          // Not logged in, redirect to login
          router.push('/login');
          return;
        }
        const data = await res.json();
        if (data.user?.onboardingComplete) {
          // Already onboarded, redirect to dashboard
          router.push('/dashboard');
          return;
        }
        setLoading(false);
      } catch (err) {
        console.error('[Onboarding] Error checking status:', err);
        setError('Failed to check onboarding status');
        setLoading(false);
      }
    };

    checkOnboarding();
  }, [router]);

  const handleComplete = async (data: OnboardingData) => {
    setIsSubmitting(true);
    setError(null);

    try {
      const res = await fetch('/api/onboarding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Onboarding failed');
      }

      // Success - redirect to dashboard
      router.push('/dashboard');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error('[Onboarding] Submission error:', err);
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FFFEF7]">
        <div className="text-center">
          <p className="text-[#2F4731]/60">Loading...</p>
        </div>
      </div>
    );
  }

  if (error && !isSubmitting) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FFFEF7]">
        <div className="text-center max-w-md">
          <p className="text-red-600 font-semibold mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-[#2F4731] text-white rounded-xl font-bold hover:bg-[#1E2E20]"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return <WelcomeFlow onComplete={handleComplete} />;
}
```

- [ ] **Step 2: Test page loads**

Run `pnpm dev` and navigate to `http://localhost:3000/onboarding`. Should show WelcomeFlow component (will error if component doesn't exist yet, which is fine).

- [ ] **Step 3: Commit**

```bash
git add adeline-ui/src/app/onboarding/page.tsx
git commit -m "feat: Create onboarding page wrapper with status check"
```

---

### Task 6: Create WelcomeFlow multi-step component

**Files:**
- Create: `adeline-ui/src/components/onboarding/WelcomeFlow.tsx`

- [ ] **Step 1: Create WelcomeFlow component**

Create `adeline-ui/src/components/onboarding/WelcomeFlow.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { ChevronRight, ChevronLeft, Check } from 'lucide-react';

const US_STATES = [
  'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
  'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
  'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
  'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
  'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
  'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
  'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
  'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
  'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
  'West Virginia', 'Wisconsin', 'Wyoming',
];

const INTEREST_OPTIONS = [
  'Chickens & Poultry', 'Horses', 'Sheep & Wool', 'Goats', 'Rabbits',
  'Gardening', 'Canning & Preservation', 'Greenhouse', 'Soil & Composting',
  'Off-Grid Systems', 'Building & Woodworking', 'Welding & Metalwork',
  'Cooking & Baking', 'Soap & Candle Making', 'Sewing & Textiles',
  'Animals & Zoology', 'Science', 'History', 'Math', 'Art',
  'Music', 'Reading', 'Writing', 'Coding', 'Minecraft',
  'Debate', 'Film Making', 'Nature & Ecology', 'Entrepreneurship',
];

const GRADE_LEVELS = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];

interface WelcomeFlowProps {
  onComplete: (data: {
    name: string;
    gradeLevel: string;
    interests: string[];
    learningStyle: string;
    state: string;
    targetGraduationYear: number;
    coppaConsent: boolean;
  }) => void;
}

export function WelcomeFlow({ onComplete }: WelcomeFlowProps) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [gradeLevel, setGradeLevel] = useState('');
  const [interests, setInterests] = useState<string[]>([]);
  const [learningStyle, setLearningStyle] = useState('EXPEDITION');
  const [state, setState] = useState('');
  const [graduationYear, setGraduationYear] = useState(new Date().getFullYear() + 4);
  const [coppaConsent, setCoppaConsent] = useState(false);

  const toggleInterest = (interest: string) => {
    setInterests(prev =>
      prev.includes(interest) ? prev.filter(i => i !== interest) : [...prev, interest]
    );
  };

  const handleNext = () => {
    // Validate current step
    if (step === 0) {
      // Welcome screen, no validation
    } else if (step === 1) {
      if (!coppaConsent) {
        alert('Please provide parent/guardian consent to continue');
        return;
      }
    } else if (step === 2) {
      if (!name.trim()) {
        alert('Please enter your child\'s name');
        return;
      }
      if (!gradeLevel) {
        alert('Please select a grade level');
        return;
      }
      if (interests.length === 0) {
        alert('Please select at least one interest');
        return;
      }
    } else if (step === 3) {
      // Learning style, auto-selected
    } else if (step === 4) {
      if (!state) {
        alert('Please select your state');
        return;
      }
      if (!graduationYear || graduationYear < new Date().getFullYear()) {
        alert('Please enter a valid graduation year');
        return;
      }
    }

    if (step < 4) {
      setStep(step + 1);
    } else {
      // Submit
      onComplete({
        name,
        gradeLevel,
        interests,
        learningStyle,
        state,
        targetGraduationYear: graduationYear,
        coppaConsent,
      });
    }
  };

  const handlePrev = () => {
    if (step > 0) setStep(step - 1);
  };

  const progress = ((step + 1) / 5) * 100;

  return (
    <div className="min-h-screen bg-[#FFFEF7] flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Progress bar */}
        <div className="mb-8">
          <div className="h-1 bg-[#E7DAC3] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#BD6809] transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-[#2F4731]/50 mt-2 font-semibold">Step {step + 1} of 5</p>
        </div>

        {/* Steps */}
        <div className="bg-white rounded-2xl p-8 border-2 border-[#E7DAC3]">
          {/* Step 0: Welcome */}
          {step === 0 && (
            <div className="text-center">
              <div className="text-5xl mb-6">🌿</div>
              <h1 className="text-2xl font-bold text-[#2F4731] mb-3">Meet Adeline</h1>
              <p className="text-[#4B3424] mb-6 leading-relaxed">
                Hi! I'm Adeline, your family's learning companion. I help turn everyday activities into real academic credit — from baking bread to building birdhouses.
              </p>
              <p className="text-sm text-[#2F4731]/50">
                Let's get to know each other so I can create a personalized learning journey just for you.
              </p>
            </div>
          )}

          {/* Step 1: Parent Consent */}
          {step === 1 && (
            <div>
              <h2 className="text-xl font-bold text-[#2F4731] mb-6">Parent/Guardian Consent</h2>
              <label className="flex items-start gap-3 cursor-pointer p-4 border-2 border-[#E7DAC3] rounded-xl hover:border-[#BD6809] transition-colors">
                <input
                  type="checkbox"
                  checked={coppaConsent}
                  onChange={e => setCoppaConsent(e.target.checked)}
                  className="mt-1 w-5 h-5 accent-[#BD6809]"
                />
                <span className="text-sm text-[#2F4731]">
                  I am the parent or legal guardian. I consent to my child using this platform and understand that any generated content or data is used strictly for educational purposes.
                </span>
              </label>
            </div>
          )}

          {/* Step 2: Child Info */}
          {step === 2 && (
            <div className="space-y-5">
              <h2 className="text-xl font-bold text-[#2F4731]">Tell us about your learner</h2>
              <div>
                <label className="block text-sm font-bold text-[#2F4731]/60 mb-2">Child's name</label>
                <input
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="Emma"
                  className="w-full p-3 rounded-xl border-2 border-[#E7DAC3] focus:border-[#BD6809] outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-[#2F4731]/60 mb-3">Grade level</label>
                <div className="flex flex-wrap gap-2">
                  {GRADE_LEVELS.map(g => (
                    <button
                      key={g}
                      onClick={() => setGradeLevel(g)}
                      className={`px-4 py-2 rounded-xl border-2 font-bold text-sm transition-all ${
                        gradeLevel === g
                          ? 'bg-[#BD6809] border-[#BD6809] text-white'
                          : 'border-[#E7DAC3] text-[#2F4731] hover:border-[#BD6809]'
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-bold text-[#2F4731]/60 mb-3">Interests (pick all that apply)</label>
                <div className="flex flex-wrap gap-2">
                  {INTEREST_OPTIONS.map(interest => (
                    <button
                      key={interest}
                      onClick={() => toggleInterest(interest)}
                      className={`px-3 py-2 rounded-full border-2 text-xs font-bold transition-all ${
                        interests.includes(interest)
                          ? 'bg-[#2F4731] border-[#2F4731] text-white'
                          : 'border-[#E7DAC3] text-[#2F4731] hover:border-[#2F4731]'
                      }`}
                    >
                      {interest}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Learning Style */}
          {step === 3 && (
            <div className="space-y-5">
              <h2 className="text-xl font-bold text-[#2F4731]">How do they learn best?</h2>
              <button
                onClick={() => setLearningStyle('EXPEDITION')}
                className={`w-full text-left p-5 rounded-xl border-2 transition-all ${
                  learningStyle === 'EXPEDITION'
                    ? 'bg-[#BD6809] border-[#BD6809] text-white'
                    : 'border-[#E7DAC3] text-[#2F4731] hover:border-[#BD6809]'
                }`}
              >
                <div className="font-bold mb-1">🗺️ Expedition Mode</div>
                <div className="text-sm opacity-90">Unified, cross-curricular learning adventures. Perfect for project-based learners.</div>
              </button>
              <button
                onClick={() => setLearningStyle('CLASSIC')}
                className={`w-full text-left p-5 rounded-xl border-2 transition-all ${
                  learningStyle === 'CLASSIC'
                    ? 'bg-[#2F4731] border-[#2F4731] text-white'
                    : 'border-[#E7DAC3] text-[#2F4731] hover:border-[#2F4731]'
                }`}
              >
                <div className="font-bold mb-1">📚 Classic Mode</div>
                <div className="text-sm opacity-90">Traditional, siloed subjects with structured lessons and printable worksheets.</div>
              </button>
            </div>
          )}

          {/* Step 4: State & Graduation */}
          {step === 4 && (
            <div className="space-y-5">
              <h2 className="text-xl font-bold text-[#2F4731]">Create Your Learning Plan</h2>
              <div>
                <label className="block text-sm font-bold text-[#2F4731]/60 mb-2">State</label>
                <select
                  value={state}
                  onChange={e => setState(e.target.value)}
                  className="w-full p-3 rounded-xl border-2 border-[#E7DAC3] focus:border-[#BD6809] outline-none"
                >
                  <option value="">Select your state</option>
                  {US_STATES.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-bold text-[#2F4731]/60 mb-2">Expected graduation year</label>
                <input
                  type="number"
                  value={graduationYear}
                  onChange={e => setGraduationYear(parseInt(e.target.value))}
                  min={new Date().getFullYear()}
                  max={new Date().getFullYear() + 20}
                  className="w-full p-3 rounded-xl border-2 border-[#E7DAC3] focus:border-[#BD6809] outline-none"
                />
              </div>
            </div>
          )}

          {/* Navigation buttons */}
          <div className="flex gap-3 mt-8">
            {step > 0 && (
              <button
                onClick={handlePrev}
                className="flex items-center gap-2 px-4 py-3 border-2 border-[#E7DAC3] text-[#2F4731] rounded-xl hover:border-[#2F4731] transition-colors font-bold"
              >
                <ChevronLeft size={18} />
                Back
              </button>
            )}
            <button
              onClick={handleNext}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-[#BD6809] text-white rounded-xl hover:bg-[#a05a08] transition-colors font-bold"
            >
              {step === 4 ? (
                <>
                  <Check size={18} />
                  Complete
                </>
              ) : (
                <>
                  Next
                  <ChevronRight size={18} />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Test component**

Navigate to `/onboarding` — should see Step 1 (Welcome). Click Next and progress through all 5 steps. Verify validation (can't proceed without required fields).

- [ ] **Step 3: Commit**

```bash
git add adeline-ui/src/components/onboarding/WelcomeFlow.tsx
git commit -m "feat: Create WelcomeFlow multi-step onboarding component"
```

---

### Task 7: Create settings/page.tsx

**Files:**
- Create: `adeline-ui/src/app/settings/page.tsx`

- [ ] **Step 1: Create settings page**

Create `adeline-ui/src/app/settings/page.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { SettingsForm } from '@/components/settings/SettingsForm';

interface UserProfile {
  id: string;
  name: string;
  gradeLevel: string | null;
  mathLevel: number | null;
  elaLevel: number | null;
  scienceLevel: number | null;
  historyLevel: number | null;
  interests: string[];
  learningStyle: string | null;
  pacingMultiplier: number;
  state: string | null;
  targetGraduationYear: number | null;
  onboardingComplete: boolean;
}

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await fetch('/api/onboarding');
        if (res.status === 401) {
          router.push('/login');
          return;
        }
        if (!res.ok) {
          throw new Error('Failed to load profile');
        }
        const data = await res.json();

        if (!data.user?.onboardingComplete) {
          router.push('/onboarding');
          return;
        }

        setUser(data.user);
        setLoading(false);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        setLoading(false);
      }
    };

    fetchProfile();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FFFEF7] flex items-center justify-center">
        <p className="text-[#2F4731]/60">Loading...</p>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="min-h-screen bg-[#FFFEF7] flex items-center justify-center">
        <p className="text-red-600">{error || 'Failed to load settings'}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FFFEF7]">
      <header className="bg-white border-b-2 border-[#E7DAC3] px-6 py-5 sticky top-0 z-10">
        <h1 className="text-2xl font-bold text-[#2F4731]">Settings</h1>
        <p className="text-[#2F4731]/60 mt-0.5 text-sm">Customize your learning preferences</p>
      </header>

      <main className="max-w-2xl mx-auto p-6">
        <SettingsForm user={user} onSave={(updated) => setUser(updated)} />
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Test page**

Navigate to `/settings` — should load the form with current user data. If onboarding not complete, should redirect to onboarding.

- [ ] **Step 3: Commit**

```bash
git add adeline-ui/src/app/settings/page.tsx
git commit -m "feat: Create settings page with profile loading"
```

---

### Task 8: Create SettingsForm component

**Files:**
- Create: `adeline-ui/src/components/settings/SettingsForm.tsx`

- [ ] **Step 1: Create settings form component**

Create `adeline-ui/src/components/settings/SettingsForm.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { Save, Loader2 } from 'lucide-react';

const GRADE_LEVELS = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];
const US_STATES = [
  'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
  'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
  'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
  'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
  'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
  'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
  'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
  'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
  'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
  'West Virginia', 'Wisconsin', 'Wyoming',
];
const INTEREST_OPTIONS = [
  'Chickens & Poultry', 'Horses', 'Sheep & Wool', 'Goats', 'Rabbits',
  'Gardening', 'Canning & Preservation', 'Greenhouse', 'Soil & Composting',
  'Off-Grid Systems', 'Building & Woodworking', 'Welding & Metalwork',
  'Cooking & Baking', 'Soap & Candle Making', 'Sewing & Textiles',
  'Animals & Zoology', 'Science', 'History', 'Math', 'Art',
  'Music', 'Reading', 'Writing', 'Coding', 'Minecraft',
  'Debate', 'Film Making', 'Nature & Ecology', 'Entrepreneurship',
];

interface UserProfile {
  id: string;
  name: string;
  gradeLevel: string | null;
  mathLevel: number | null;
  elaLevel: number | null;
  scienceLevel: number | null;
  historyLevel: number | null;
  interests: string[];
  learningStyle: string | null;
  pacingMultiplier: number;
  state: string | null;
  targetGraduationYear: number | null;
}

interface Props {
  user: UserProfile;
  onSave: (updated: UserProfile) => void;
}

export function SettingsForm({ user, onSave }: Props) {
  const [gradeLevel, setGradeLevel] = useState(user.gradeLevel || '');
  const [mathLevel, setMathLevel] = useState(user.mathLevel);
  const [elaLevel, setElaLevel] = useState(user.elaLevel);
  const [scienceLevel, setScienceLevel] = useState(user.scienceLevel);
  const [historyLevel, setHistoryLevel] = useState(user.historyLevel);
  const [interests, setInterests] = useState(user.interests);
  const [learningStyle, setLearningStyle] = useState(user.learningStyle || 'EXPEDITION');
  const [pacingMultiplier, setPacingMultiplier] = useState(user.pacingMultiplier || 1.0);
  const [state, setState] = useState(user.state || '');
  const [targetGraduationYear, setTargetGraduationYear] = useState(user.targetGraduationYear || '');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  const toggleInterest = (interest: string) => {
    setInterests(prev =>
      prev.includes(interest) ? prev.filter(i => i !== interest) : [...prev, interest]
    );
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      const res = await fetch('/api/onboarding', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gradeLevel: gradeLevel || undefined,
          mathLevel: mathLevel || undefined,
          elaLevel: elaLevel || undefined,
          scienceLevel: scienceLevel || undefined,
          historyLevel: historyLevel || undefined,
          interests,
          learningStyle,
          pacingMultiplier,
          state: state || undefined,
          targetGraduationYear: targetGraduationYear ? parseInt(String(targetGraduationYear)) : undefined,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Save failed');
      }

      const data = await res.json();
      onSave(data.user);
      setMessage({ text: '✅ Settings saved! Adeline will adapt to your new profile.', ok: true });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to save';
      setMessage({ text: `❌ ${msg}`, ok: false });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Overall Grade Level */}
      <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
        <label className="block text-sm font-bold uppercase tracking-widest text-[#2F4731]/50 mb-4">
          Overall Grade Level
        </label>
        <div className="flex flex-wrap gap-2">
          {GRADE_LEVELS.map(g => (
            <button
              key={g}
              onClick={() => setGradeLevel(g)}
              className={`px-4 py-2 rounded-xl border-2 font-bold text-sm transition-all ${
                gradeLevel === g
                  ? 'bg-[#BD6809] border-[#BD6809] text-white'
                  : 'border-[#E7DAC3] text-[#2F4731] hover:border-[#BD6809]'
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {/* Subject-Specific Levels */}
      <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
        <label className="block text-sm font-bold uppercase tracking-widest text-[#2F4731]/50 mb-4">
          Subject-Specific Levels
        </label>
        <p className="text-xs text-[#2F4731]/50 mb-4">Override the grade level for each subject. Leave blank to use overall level.</p>
        <div className="space-y-4">
          {[
            { label: 'Math', state: mathLevel, setState: setMathLevel },
            { label: 'ELA / Reading', state: elaLevel, setState: setElaLevel },
            { label: 'Science', state: scienceLevel, setState: setScienceLevel },
            { label: 'History', state: historyLevel, setState: setHistoryLevel },
          ].map(({ label, state, setState }) => (
            <div key={label} className="p-4 rounded-xl border border-[#E7DAC3] bg-[#FDF6E9]">
              <div className="font-bold text-sm text-[#2F4731] mb-2">{label}</div>
              <div className="flex flex-wrap gap-1">
                <button
                  onClick={() => setState(null)}
                  className={`px-3 py-1 text-xs font-medium rounded-lg border transition-all ${
                    state === null
                      ? 'bg-gray-600 border-gray-600 text-white'
                      : 'border-gray-300 text-gray-500 hover:border-gray-500'
                  }`}
                >
                  Use overall
                </button>
                {GRADE_LEVELS.map(g => {
                  const numVal = g === 'K' ? 0 : parseInt(g);
                  return (
                    <button
                      key={g}
                      onClick={() => setState(numVal)}
                      className={`px-3 py-1 text-xs font-bold rounded-lg border transition-all ${
                        state === numVal
                          ? 'bg-[#BD6809] border-[#BD6809] text-white'
                          : 'border-[#E7DAC3] text-[#2F4731] hover:border-[#BD6809]'
                      }`}
                    >
                      {g}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Learning Pace */}
      <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
        <label className="block text-sm font-bold uppercase tracking-widest text-[#2F4731]/50 mb-4">
          Learning Pace
        </label>
        <div className="space-y-2">
          {[
            { value: 1.0, label: 'Standard', desc: 'Normal grade-level pacing' },
            { value: 1.25, label: 'Accelerated', desc: '25% faster' },
            { value: 1.5, label: 'Fast Track', desc: '50% faster' },
            { value: 2.0, label: 'Sprint', desc: '2× speed' },
          ].map(opt => (
            <button
              key={opt.value}
              onClick={() => setPacingMultiplier(opt.value)}
              className={`w-full text-left p-3 rounded-xl border-2 transition-all ${
                pacingMultiplier === opt.value
                  ? 'bg-[#BD6809] border-[#BD6809] text-white'
                  : 'border-[#E7DAC3] text-[#2F4731] hover:border-[#BD6809]'
              }`}
            >
              <div className="font-bold text-sm">{opt.label}</div>
              <div className={`text-xs mt-0.5 ${
                pacingMultiplier === opt.value ? 'text-white/80' : 'text-[#2F4731]/50'
              }`}>{opt.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Learning Mode */}
      <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
        <label className="block text-sm font-bold uppercase tracking-widest text-[#2F4731]/50 mb-4">
          Learning Mode
        </label>
        <div className="space-y-3">
          <button
            onClick={() => setLearningStyle('EXPEDITION')}
            className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
              learningStyle === 'EXPEDITION'
                ? 'bg-[#BD6809] border-[#BD6809] text-white'
                : 'border-[#E7DAC3] text-[#2F4731] hover:border-[#BD6809]'
            }`}
          >
            <div className="font-bold">🗺️ Expedition Mode</div>
            <div className={`text-sm mt-1 ${learningStyle === 'EXPEDITION' ? 'text-white/90' : 'text-[#2F4731]/60'}`}>
              Cross-curricular learning adventures
            </div>
          </button>
          <button
            onClick={() => setLearningStyle('CLASSIC')}
            className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
              learningStyle === 'CLASSIC'
                ? 'bg-[#2F4731] border-[#2F4731] text-white'
                : 'border-[#E7DAC3] text-[#2F4731] hover:border-[#2F4731]'
            }`}
          >
            <div className="font-bold">📚 Classic Mode</div>
            <div className={`text-sm mt-1 ${learningStyle === 'CLASSIC' ? 'text-white/90' : 'text-[#2F4731]/60'}`}>
              Traditional siloed subjects
            </div>
          </button>
        </div>
      </div>

      {/* Interests */}
      <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
        <label className="block text-sm font-bold uppercase tracking-widest text-[#2F4731]/50 mb-4">
          Interests
        </label>
        <div className="flex flex-wrap gap-2">
          {INTEREST_OPTIONS.map(interest => (
            <button
              key={interest}
              onClick={() => toggleInterest(interest)}
              className={`px-4 py-2 rounded-full border-2 font-bold text-sm transition-all ${
                interests.includes(interest)
                  ? 'bg-[#2F4731] border-[#2F4731] text-white'
                  : 'border-[#E7DAC3] text-[#2F4731] hover:border-[#2F4731]'
              }`}
            >
              {interest}
            </button>
          ))}
        </div>
      </div>

      {/* State & Graduation */}
      <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6 space-y-4">
        <div>
          <label className="block text-sm font-bold uppercase tracking-widest text-[#2F4731]/50 mb-2">
            State
          </label>
          <select
            value={state}
            onChange={e => setState(e.target.value)}
            className="w-full p-3 rounded-xl border-2 border-[#E7DAC3] focus:border-[#BD6809] outline-none"
          >
            <option value="">Select your state</option>
            {US_STATES.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-bold uppercase tracking-widest text-[#2F4731]/50 mb-2">
            Target Graduation Year
          </label>
          <input
            type="number"
            value={targetGraduationYear}
            onChange={e => setTargetGraduationYear(e.target.value)}
            className="w-full p-3 rounded-xl border-2 border-[#E7DAC3] focus:border-[#BD6809] outline-none"
          />
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`p-4 rounded-xl ${message.ok ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'} font-semibold`}>
          {message.text}
        </div>
      )}

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="flex items-center justify-center gap-2 w-full px-6 py-3 bg-[#2F4731] text-white rounded-xl font-bold hover:bg-[#1E2E20] transition-colors disabled:opacity-50"
      >
        {saving ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />}
        {saving ? 'Saving...' : 'Save Changes'}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Test form**

Navigate to `/settings` — should load form with current values. Edit a few fields, click save. Should show success message and update.

- [ ] **Step 3: Commit**

```bash
git add adeline-ui/src/components/settings/SettingsForm.tsx
git commit -m "feat: Create SettingsForm component for profile editing"
```

---

## Phase 3: Integration & Layout

### Task 9: Add onboarding gate to layout

**Files:**
- Modify: `adeline-ui/src/app/(routes)/layout.tsx`

- [ ] **Step 1: Add onboarding check to layout**

Open `adeline-ui/src/app/(routes)/layout.tsx` and wrap the content with an onboarding guard component:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AppSidebar } from '@/components/nav/AppSidebar';

export default function RoutesLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [onboardingComplete, setOnboardingComplete] = useState<boolean | null>(null);

  useEffect(() => {
    const checkOnboarding = async () => {
      try {
        const res = await fetch('/api/onboarding');
        if (res.status === 401) {
          router.push('/login');
          return;
        }
        const data = await res.json();
        if (!data.user?.onboardingComplete) {
          router.push('/onboarding');
          return;
        }
        setOnboardingComplete(true);
      } catch (err) {
        console.error('[Layout] Onboarding check failed:', err);
        // Allow to proceed on error (might be network issue)
        setOnboardingComplete(true);
      }
    };

    checkOnboarding();
  }, [router]);

  if (onboardingComplete === null) {
    return null; // Loading
  }

  if (!onboardingComplete) {
    return null; // Redirecting (handled in useEffect)
  }

  return <AppSidebar>{children}</AppSidebar>;
}
```

- [ ] **Step 2: Test gate**

Navigate to `/dashboard` without onboarding — should redirect to `/onboarding`. After completing onboarding, should allow access.

- [ ] **Step 3: Commit**

```bash
git add adeline-ui/src/app/\(routes\)/layout.tsx
git commit -m "feat: Add onboarding gate to routes layout"
```

---

### Task 10: Integrate DailyBreadWidget into dashboard

**Files:**
- Modify: `adeline-ui/src/app/(routes)/dashboard/page.tsx`

- [ ] **Step 1: Update dashboard to include DailyBreadWidget**

Open `adeline-ui/src/app/(routes)/dashboard/page.tsx` and update to include DailyBreadWidget in the sidebar area. Add this import:

```typescript
import { DailyBreadWidget } from '@/components/daily-bread/DailyBreadWidget';
```

And add the widget to the layout (in the sidebar area, around line 96 before the bottom section):

```typescript
{/* Daily Bread */}
<div className="mt-6 mb-6">
  <DailyBreadWidget onStudy={onStudy} />
</div>
```

Where `onStudy` is a callback that sends the prompt to AdelineChatPanel. Add this function to the component:

```typescript
const onStudy = (prompt: string) => {
  // This will be called by DailyBreadWidget
  // Send the prompt to AdelineChatPanel via its API
  // For now, just log it
  console.log('[Dashboard] Study prompt:', prompt);
};
```

- [ ] **Step 2: Test widget**

Navigate to `/dashboard` — should see DailyBreadWidget in sidebar loading scripture. Click "Start Deep Dive Study" — should log the study prompt.

- [ ] **Step 3: Commit**

```bash
git add adeline-ui/src/app/\(routes\)/dashboard/page.tsx
git commit -m "feat: Integrate DailyBreadWidget into dashboard sidebar"
```

---

## Phase 4: Final Polish & Testing

### Task 11: Test end-to-end onboarding flow

**Files:** (No new files, integration testing)

- [ ] **Step 1: Test full onboarding → dashboard flow**

1. Logout (or use incognito window)
2. Login as new user
3. Should redirect to `/onboarding`
4. Complete all 5 steps
5. Should redirect to `/dashboard`
6. Should see sidebar with navigation
7. Should see DailyBreadWidget
8. Should see AdelineChatPanel

- [ ] **Step 2: Test settings edit flow**

1. From dashboard, click Settings
2. Should load current profile
3. Edit a few fields (e.g., change grade, interests)
4. Click "Save Changes"
5. Should show success message
6. Refresh page — should persist changes
7. Verify next lesson generation uses new profile (check brain logs)

- [ ] **Step 3: Test onboarding gate**

1. Try accessing `/dashboard` directly with onboarding incomplete
2. Should redirect to `/onboarding`
3. Try accessing `/settings` with onboarding incomplete
4. Should redirect to `/onboarding`

- [ ] **Step 4: Commit test notes**

```bash
git add .
git commit -m "test: Complete end-to-end onboarding, settings, and gate testing"
```

---

### Task 12: Verify brain integration

**Files:** (No new files, verification)

- [ ] **Step 1: Verify adeline-brain User table**

```bash
cd adeline-brain
psql $POSTGRES_DSN -c "SELECT id, name, gradeLevel, interests, learningStyle, onboardingComplete FROM users LIMIT 1;"
```

Expected: Shows new columns with values from onboarding.

- [ ] **Step 2: Verify agents read profile**

Update agents in adeline-brain to query User table for profile. For example, in the lesson generation endpoint:

```python
user = db.query(User).filter(User.id == user_id).first()
if user:
    student_context = {
        "gradeLevel": user.gradeLevel,
        "interests": user.interests,
        "learningStyle": user.learningStyle,
        "pacingMultiplier": user.pacingMultiplier,
    }
    # Pass to agent
```

- [ ] **Step 3: Test agent adaptation**

Generate a lesson with one profile (e.g., grade 3, interests ["Gardening"]), then change to a different profile (grade 7, interests ["Coding"]), and generate another lesson. Verify the content adapts (different complexity, different topic connections).

- [ ] **Step 4: Commit**

```bash
git add adeline-brain/app/api/lessons.py  # or wherever agents are
git commit -m "feat: Agents read student profile from User table for lesson adaptation"
```

---

## Summary of Tasks

**Phase 1 (adeline-brain):** 4 tasks
- Task 1: Prisma schema + migration
- Task 2: GET /api/onboarding
- Task 3: POST /api/onboarding
- Task 4: PATCH /api/onboarding

**Phase 2 (adeline-ui UI):** 4 tasks
- Task 5: onboarding/page.tsx
- Task 6: WelcomeFlow component
- Task 7: settings/page.tsx
- Task 8: SettingsForm component

**Phase 3 (Integration):** 2 tasks
- Task 9: Onboarding gate in layout
- Task 10: DailyBreadWidget integration

**Phase 4 (Testing):** 2 tasks
- Task 11: End-to-end testing
- Task 12: Brain integration & verification

**Total: 12 focused tasks, each 2-5 minutes**

---

Plan complete and saved to `docs/superpowers/plans/2026-04-03-onboarding-settings-dailybread.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**