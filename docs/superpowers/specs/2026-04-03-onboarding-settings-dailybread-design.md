# Onboarding + Settings + DailyBread Implementation Design

**Goal:** Build required onboarding flow, editable student settings, and daily scripture widget that allows Adeline to adapt all lessons to student profile stored in adeline-brain Postgres.

**Architecture:** Student profile (name, grade, interests, learning style, pacing, state, graduation year) is the source of truth in adeline-brain. On first login, onboarding blocks dashboard access. Settings allow edits; changes immediately sync to brain and Adeline adapts subsequent lessons. DailyBread fetches scripture and integrates with Adeline chat.

**Tech Stack:** Next.js 16 (adeline-ui) + FastAPI (adeline-brain) + Prisma ORM + PostgreSQL. No external APIs except existing Anthropic Claude and daily scripture service.

---

## Database Schema

### User Table Additions (adeline-brain/prisma/schema.prisma)

```prisma
model User {
  id                String   @id @default(uuid())
  name              String
  email             String   @unique
  role              UserRole
  gradeLevel        String?  // "K", "1", "2", ..., "12" — required when role = STUDENT

  // Subject-specific grade level overrides (null = use gradeLevel)
  mathLevel         Int?
  elaLevel          Int?
  scienceLevel      Int?
  historyLevel      Int?

  // Learning preferences
  interests         String[] // Array of tags: ["Coding", "Gardening", "Chickens", etc.]
  learningStyle     String?  // "EXPEDITION" (cross-curricular) or "CLASSIC" (siloed subjects)
  pacingMultiplier  Float?   // 1.0 (standard), 1.25 (accelerated), 1.5 (fast track), 2.0 (sprint)

  // State & graduation tracking (for curriculum alignment)
  state             String?  // US state name (e.g., "Oklahoma", "Texas")
  targetGraduationYear Int?  // Year (e.g., 2028)

  // Onboarding gate
  onboardingComplete Boolean @default(false)

  // Relations
  lessons           StudentLesson[]
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt

  @@index([role])
  @@index([email])
  @@index([onboardingComplete])
}
```

### Migration

Create migration file: `adeline-brain/prisma/migrations/2026040X_add_onboarding_fields/migration.sql`

The migration will:
- Add all new columns to User table with appropriate defaults
- Add indexes on `onboardingComplete` and `role` for fast queries

---

## API Endpoints

### POST /api/onboarding (adeline-brain/app/api/onboarding.py)

**Purpose:** Initial onboarding submission (first-time setup after signup)

**Request:**
```json
{
  "name": "Emma Johnson",
  "gradeLevel": "5",
  "interests": ["Gardening", "Science", "Reading"],
  "learningStyle": "EXPEDITION",
  "state": "Oklahoma",
  "targetGraduationYear": 2030,
  "coppaConsent": true
}
```

**Response:**
```json
{
  "ok": true,
  "user": {
    "id": "user-123",
    "name": "Emma Johnson",
    "gradeLevel": "5",
    "interests": ["Gardening", "Science", "Reading"],
    "learningStyle": "EXPEDITION",
    "state": "Oklahoma",
    "targetGraduationYear": 2030,
    "onboardingComplete": true
  }
}
```

**Logic:**
- Validate: all required fields present and non-empty
- Validate: COPPA consent is true
- Validate: gradeLevel is in valid range (K, 1-12)
- Validate: state is valid US state name
- Validate: targetGraduationYear is 4 digits and reasonable (current year to current year + 20)
- Validate: learningStyle is "EXPEDITION" or "CLASSIC"
- Update User record with all fields + set `onboardingComplete = true`
- Return user object
- Log: "[Onboarding] User {user_id} completed onboarding: {name}, grade {gradeLevel}, interests {interests}"

### PATCH /api/onboarding (adeline-brain/app/api/onboarding.py)

**Purpose:** Update student profile from Settings page (authenticated student only)

**Request:**
```json
{
  "gradeLevel": "6",
  "interests": ["Gardening", "Coding", "History"],
  "learningStyle": "CLASSIC",
  "mathLevel": 5,
  "elaLevel": 6,
  "scienceLevel": 5,
  "historyLevel": 6,
  "pacingMultiplier": 1.25,
  "state": "Oklahoma",
  "targetGraduationYear": 2029
}
```

**Response:**
```json
{
  "ok": true,
  "user": {
    "id": "user-123",
    "name": "Emma Johnson",
    "gradeLevel": "6",
    "mathLevel": 5,
    "elaLevel": 6,
    "scienceLevel": 5,
    "historyLevel": 6,
    "interests": ["Gardening", "Coding", "History"],
    "learningStyle": "CLASSIC",
    "pacingMultiplier": 1.25,
    "state": "Oklahoma",
    "targetGraduationYear": 2029,
    "onboardingComplete": true
  }
}
```

**Logic:**
- Require authentication (student user only)
- Validate each field if provided:
  - gradeLevel: K or 1-12
  - mathLevel/elaLevel/scienceLevel/historyLevel: null or 0-12 (where 0 = K)
  - interests: array of strings
  - learningStyle: "EXPEDITION" or "CLASSIC"
  - pacingMultiplier: 1.0, 1.25, 1.5, or 2.0
  - state: valid US state
  - targetGraduationYear: 4 digits, reasonable range
- Update User record with non-null fields
- Clear any cached journey plan or learning state (Adeline must recompute with new profile)
- Return updated user object
- Log: "[Onboarding PATCH] User {user_id} updated profile"

### GET /api/onboarding (adeline-brain/app/api/onboarding.py)

**Purpose:** Fetch current student profile (used by Settings page on load)

**Request:** GET /api/onboarding

**Response:**
```json
{
  "ok": true,
  "user": {
    "id": "user-123",
    "name": "Emma Johnson",
    "gradeLevel": "5",
    "mathLevel": null,
    "elaLevel": null,
    "scienceLevel": null,
    "historyLevel": null,
    "interests": ["Gardening", "Science", "Reading"],
    "learningStyle": "EXPEDITION",
    "pacingMultiplier": 1.0,
    "state": "Oklahoma",
    "targetGraduationYear": 2030,
    "onboardingComplete": true
  }
}
```

**Logic:**
- Require authentication
- Fetch User record
- Return all profile fields

---

## UI Components

### 1. Onboarding Flow (adeline-ui/src/app/onboarding/page.tsx)

**Parent component** for the multi-step onboarding wizard.

**Responsibilities:**
- Check onboarding status on mount (GET /api/onboarding, if 401 → user not logged in, redirect to /login)
- Render WelcomeFlow component
- On WelcomeFlow complete → POST /api/onboarding with data
- On success → redirect to /dashboard
- On error → show error message, allow retry

**Props to WelcomeFlow:**
- `onComplete(data)` — callback when all steps finished

### 2. Welcome Flow Component (adeline-ui/src/components/onboarding/WelcomeFlow.tsx)

**Multi-step modal component** (adapted from cascade-adeline).

**Steps:**
1. **Welcome** — Illustration + intro text about Adeline
2. **Parent Consent** — Checkbox: "I am the parent/guardian. I consent to my child using this platform and understand..."
3. **Tell Us About Your Learner** — Fields: child name, grade level (grade selector K-12), interests (multi-select tag input)
4. **Learning Style** — Radio: "Expedition Mode" (cross-curricular) vs "Classic Mode" (siloed subjects)
5. **Create Your Learning Plan** — Fields: state (dropdown), target graduation year (text input)

**State Management:**
- Track current step (0-4)
- Store form data in local state
- Validate required fields before allowing next
- Show progress bar (step N/5)

**Styling:**
- Use Dear Adeline color palette (#2F4731, #BD6809, #FFFEF7, #E7DAC3)
- Full-screen modal overlay (z-index 9999, dark semi-transparent background)
- Smooth slide/fade transitions between steps
- Mobile-responsive (single column on small screens)

**Validation:**
- Step 2: coppaConsent must be true
- Step 3: childName non-empty, gradeLevel selected, at least 1 interest
- Step 5: state selected, targetGraduationYear is 4-digit number in reasonable range

### 3. Settings Page (adeline-ui/src/app/settings/page.tsx)

**Server component** that wraps the Settings UI.

**Responsibilities:**
- On load: fetch user profile via GET /api/onboarding
- If onboarding not complete → redirect to /onboarding
- Render SettingsForm with current user data
- Pass onSave callback

### 4. Settings Form Component (adeline-ui/src/components/settings/SettingsForm.tsx)

**Two-column form component** for editing student preferences.

**Left Column:**
- Overall Grade Level selector (K, 1-12 buttons)
- Subject-Specific Levels section (Math, ELA, Science, History — each with "Use Overall" + grade buttons)
- Learning Pace dropdown (Standard 1.0x, Accelerated 1.25x, Fast Track 1.5x, Sprint 2.0x)
- Learning Mode radio (Expedition vs Classic)
- Interests multi-select (tag pills)

**Right Column:**
- Summary display showing selected values
- Save button
- Status message (success/error) after save

**State Management:**
- All editable fields in component state
- On save → PATCH /api/onboarding with changed fields only
- Show loading spinner during save
- On success → show "Settings saved!" message, update display
- On error → show "Failed to save" message

**Styling:**
- Same palette as onboarding
- Card-based layout (white rounded containers on #FFFEF7 background)
- Icons for subjects (Calculator for Math, BookOpen for ELA, FlaskConical for Science, Globe for History)
- Smooth transitions on button/input focus

### 5. DailyBreadWidget (adeline-ui/src/components/daily-bread/DailyBreadWidget.tsx)

**Sidebar widget component** that fetches and displays daily scripture.

**Responsibilities:**
- On mount: fetch `/api/daily-bread` (existing endpoint)
- Display verse, reference, original language note, meaning
- Show loading state while fetching
- Show error state with retry button
- On "Start Deep Dive Study" click → call parent callback with study prompt

**Props:**
- `onStudy(prompt: string)` — callback when user clicks study button

**Data Structure (from /api/daily-bread):**
```json
{
  "verse": "In the beginning, God created the heavens and the earth.",
  "reference": "Genesis 1:1",
  "original": "בְרֵאשִׁית",
  "originalMeaning": "In the beginning; when things began; at first",
  "translationNote": "The Hebrew word 'bereishit' literally means 'at the head of' or 'at the beginning of.'",
  "context": "The opening verse of the Bible sets the foundation for all of Scripture..."
}
```

**Study Prompt Format:**
```
I want my Daily Bread deep-dive study on Genesis 1:1 today. Translate it directly from the original Hebrew text, keeping the original meaning and context. Note any differences with the translation we are used to hearing — especially around the word "בְרֵאשִׁית" which means "In the beginning; when things began; at first". Also share the historical and cultural context that makes this verse richer.
```

**Styling:**
- Compact card format (fits in sidebar)
- Color: #FFFDF5 background, #2F4731 text, #BD6809 accents
- Icon (BookOpen) + "Daily Bread" label header
- Verse displayed in italics
- Original language section with meaning
- CTA button: "Start Deep Dive Study" with arrow

---

## Integration Points

### With AdelineChatPanel
- DailyBreadWidget calls `onStudy(prompt)` when user clicks button
- Parent component (Dashboard) passes callback that sends prompt to AdelineChatPanel
- AdelineChatPanel generates lesson response using Claude with student profile context

### With Dashboard
- Dashboard imports DailyBreadWidget and renders in sidebar
- Dashboard passes `onStudy` callback to DailyBreadWidget
- Dashboard shows onboarding check: if user lands on /dashboard and `onboardingComplete === false`, redirect to /onboarding

### With adeline-brain Agents
- When generating lessons, all agents (Historian, Science, Discipleship, Registrar) query User table to fetch:
  - gradeLevel (or subject-specific override)
  - interests
  - learningStyle
  - pacingMultiplier
  - state (for curriculum standards)
- Agents use these fields to customize content difficulty, vocabulary, pacing, and learning modality

---

## Onboarding Flow Details

### First-Time Login Sequence
1. User signs up / authenticates
2. Middleware/layout checks: GET /api/onboarding
3. If 401 (not logged in) → redirect to /login
4. If response `onboardingComplete === false` → redirect to /onboarding
5. Onboarding page loads, renders WelcomeFlow modal
6. User steps through 5 steps (≈5 minutes total)
7. On step 5 complete → POST /api/onboarding
8. On success → redirect to /dashboard
9. Dashboard now loads with user profile available

### Settings Edit Sequence
1. User navigates to /settings
2. Page loads, GET /api/onboarding fetches current profile
3. SettingsForm renders with all fields populated
4. User edits one or more fields
5. User clicks "Save Changes"
6. Form sends PATCH /api/onboarding with edited fields
7. API validates and updates User record
8. API clears any cached lesson plans (forces recompute with new profile)
9. Response includes updated user object
10. UI shows success message + updates display
11. Next lesson generation uses updated profile

---

## Error Handling

**Onboarding Errors:**
- Invalid COPPA consent → "Please provide parent consent to continue"
- Missing required fields → "Please fill in all required fields: {list}"
- Invalid state → "Please select a valid US state"
- Invalid grade → "Please select a grade between K and 12"
- Network error during POST → "Failed to save. Please check your connection and try again."

**Settings Errors:**
- Network error during PATCH → "Failed to save. Please try again."
- Validation error (invalid grade, invalid state, etc.) → Show specific validation message
- 401 (not authenticated) → Redirect to /login

**DailyBread Errors:**
- API call fails → Show "Could not load today's verse." with retry button
- Empty response → Show "No verse available today."

---

## Testing Considerations

**Onboarding:**
- Test all 5 steps progress and validation
- Test form data persists across steps
- Test POST /api/onboarding success and failure cases
- Test redirect to dashboard on success
- Test COPPA consent validation

**Settings:**
- Test GET /api/onboarding loads current profile
- Test all form fields update correctly
- Test PATCH /api/onboarding success and failure
- Test subject-level override logic (null = use overall)
- Test validation for each field type

**DailyBread:**
- Test fetch and display of scripture
- Test "Start Deep Dive Study" callback
- Test error/retry flow
- Test study prompt formatting

**Integration:**
- Test onboarding blocks unauthenticated access
- Test onboarding blocks non-completed access
- Test updated profile affects next lesson generation
- Test DailyBread integrates with chat panel

---

## Dependencies

**New:**
- None (no new external libraries)

**Existing (to verify installed):**
- `next` 16.2.2
- `react` 19
- `lucide-react` (icons)
- Anthropic SDK (Claude)

**adeline-brain:**
- Prisma ORM
- FastAPI
- PostgreSQL

---

## Assumptions & Constraints

1. **Authentication:** User is already authenticated before accessing onboarding/settings (handled by existing auth middleware)
2. **Database:** adeline-brain Postgres is already running and accessible
3. **API Baseurl:** adeline-ui points to `/api/*` (rewritten to BRAIN_INTERNAL_URL via next.config.js)
4. **Daily Bread:** `/api/daily-bread` endpoint already exists and returns expected format
5. **COPPA Compliance:** Onboarding captures parental consent; no audio/video recording in this feature (deferred to voice reading coach)

---

## Success Criteria

✓ Onboarding is required on first login; blocks dashboard access until complete
✓ All onboarding data persists in adeline-brain User table
✓ Settings page loads and edits current user profile
✓ Changes to settings immediately available for next lesson generation
✓ DailyBread displays scripture and triggers Adeline chat study
✓ All three features use consistent Dear Adeline styling
✓ Error handling provides clear user feedback
✓ COPPA compliance: parent consent captured and logged
