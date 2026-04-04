# Brain Integration Verification

## Overview

This document describes how to verify that the onboarding system correctly integrates with adeline-brain, ensuring that student profile data is properly stored and used by Adeline agents for lesson generation.

## Integration Points

### 1. Database Storage (Postgres)

**Location:** `adeline-brain/prisma/schema.prisma`

**User Table Columns Added:**
```prisma
model User {
  // ... existing fields ...

  // Onboarding fields (new)
  gradeLevel            String?  // Required for students: "K", "1"-"12"
  mathLevel             Int?     // 0-12 mastery score (null = use gradeLevel)
  elaLevel              Int?     // 0-12 mastery score (null = use gradeLevel)
  scienceLevel          Int?     // 0-12 mastery score (null = use gradeLevel)
  historyLevel          Int?     // 0-12 mastery score (null = use gradeLevel)
  interests             String[] // Array of tags: ["Coding", "Gardening", etc]
  learningStyle         String?  // "EXPEDITION" (cross-curricular) or "CLASSIC" (siloed)
  pacingMultiplier      Float?   // 1.0, 1.25, 1.5, or 2.0
  state                 String?  // US state name for curriculum alignment
  targetGraduationYear  Int?     // Year (e.g., 2030)
  onboardingComplete    Boolean  // Gate for access to dashboard
}
```

**Verification:**
```bash
# Connect to adeline-brain Postgres
psql $POSTGRES_DSN

# Verify User table schema
\d "User"

# After user completes onboarding, verify data:
SELECT id, name, gradeLevel, interests, learningStyle, pacingMultiplier, state, targetGraduationYear, onboardingComplete
FROM "User"
WHERE id = '<user-uuid>';
```

### 2. API Endpoints

**Endpoints Created:**
- `GET /api/onboarding` - Fetch student profile
- `POST /api/onboarding` - Initial onboarding submission
- `PATCH /api/onboarding` - Update settings

**Location:** `adeline-brain/app/api/onboarding.py`

**Verification:**
```bash
# Test GET endpoint
curl -X GET http://localhost:8000/api/onboarding \
  -H "Authorization: Bearer <user-id>"

# Test POST endpoint (initial onboarding)
curl -X POST http://localhost:8000/api/onboarding \
  -H "Authorization: Bearer <user-id>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Emma Johnson",
    "gradeLevel": "5",
    "interests": ["Science", "Reading"],
    "learningStyle": "EXPEDITION",
    "state": "Oklahoma",
    "targetGraduationYear": 2030,
    "coppaConsent": true
  }'

# Test PATCH endpoint (settings update)
curl -X PATCH http://localhost:8000/api/onboarding \
  -H "Authorization: Bearer <user-id>" \
  -H "Content-Type: application/json" \
  -d '{
    "gradeLevel": "6",
    "mathLevel": 5
  }'
```

### 3. Agent Integration

**Location:** `adeline-brain/app/agents/orchestrator.py`

**Current State:** Agents should query the User table to fetch student profile before generating lessons.

**Required Verification:**
When agents generate lessons, they should:

1. **Query Student Profile:**
   ```python
   user = await conn.fetchrow(
       'SELECT * FROM "User" WHERE "id" = $1',
       student_id
   )
   ```

2. **Use Profile for Lesson Adaptation:**

   | Field | Usage |
   |-------|-------|
   | `gradeLevel` | Determine vocabulary complexity, concept difficulty |
   | `mathLevel`/`elaLevel`/`scienceLevel`/`historyLevel` | Override gradeLevel for subject-specific blocks |
   | `interests` | Choose relevant examples, tailor scenarios to student interests |
   | `learningStyle` | EXPEDITION = cross-curricular connections; CLASSIC = siloed subjects |
   | `pacingMultiplier` | Adjust lesson length: 1.0x standard, 1.5x accelerated, 2.0x sprint |
   | `state` | Align curriculum standards (OAS for Oklahoma, etc.) |
   | `targetGraduationYear` | Calculate credits remaining, adjust long-term planning |

3. **Example Agent Code (DiscipleshipAgent):**
   ```python
   async def generate_lesson(self, student_id: str, prompt: str):
       # Fetch student profile
       conn = await get_db_connection()
       student = await conn.fetchrow(
           'SELECT * FROM "User" WHERE "id" = $1',
           student_id
       )

       # Adapt lesson to student
       grade_band = determine_grade_band(
           student['gradeLevel'],
           student['mathLevel'] if prompt.contains('math') else None
       )

       vocabulary = VOCABULARY[grade_band]
       concepts = CONCEPTS[grade_band]

       # Add interest-based context
       context = f"Student interests: {', '.join(student['interests'])}"

       # Determine pacing
       lesson_blocks = BASE_BLOCKS * student['pacingMultiplier']

       # Return lesson adapted to student profile
       return generate_blocks(
           prompt=prompt,
           grade_band=grade_band,
           vocabulary=vocabulary,
           context=context,
           learning_style=student['learningStyle'],
           num_blocks=int(lesson_blocks)
       )
   ```

## Test Verification Checklist

### Setup
- [ ] Onboarding flow is complete and working
- [ ] User data stored in Postgres User table
- [ ] adeline-brain API endpoints responding
- [ ] Brain database connectivity verified

### API Level
- [ ] GET /api/onboarding returns correct user profile
- [ ] POST /api/onboarding saves all fields to database
- [ ] PATCH /api/onboarding updates fields and persists changes
- [ ] Authorization header validation working (401 on missing token)

### Database Level
- [ ] User table has all new onboarding columns
- [ ] Student profile queries return correct data types
- [ ] interests array handled properly in Postgres
- [ ] Timestamps (createdAt, updatedAt) updating correctly

### Agent Integration
- [ ] [ ] Agents query User table before generating lessons
- [ ] [ ] gradeLevel affects vocabulary complexity
- [ ] [ ] Subject-specific levels override gradeLevel when present
- [ ] [ ] interests appear in lesson examples and scenarios
- [ ] [ ] learningStyle determines cross-curricular vs. siloed structure
- [ ] [ ] pacingMultiplier affects lesson length
- [ ] [ ] state affects curriculum standards selected
- [ ] [ ] Agents handle NULL values gracefully (use defaults)

### End-to-End
- [ ] User completes onboarding
- [ ] Data persists in database
- [ ] Next lesson generated respects all profile settings
- [ ] Settings page allows edits
- [ ] Updated settings immediately affect next lesson
- [ ] Graduation tracking uses targetGraduationYear

## Manual Testing Procedure

### Step 1: Verify Database Storage
```bash
# After user completes onboarding:
psql $POSTGRES_DSN
SELECT * FROM "User" WHERE name = 'Emma Johnson';
```

**Expected Output:** Row with all onboarding fields populated

### Step 2: Verify API Responses
```bash
# Test each endpoint with user's token
curl -X GET http://localhost:8000/api/onboarding \
  -H "Authorization: Bearer $USER_TOKEN" | jq .
```

**Expected:** Response includes all student profile fields

### Step 3: Verify Lesson Generation Uses Profile
```bash
# Request a lesson with student profile set
curl -X POST http://localhost:8000/lesson/generate \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Teach me about photosynthesis"}' | jq .
```

**Verify in response:**
- Vocabulary matches student's gradeLevel
- Examples reference student's interests
- Lesson structure matches learningStyle (EXPEDITION = connections, CLASSIC = single subject)
- Lesson length matches pacingMultiplier

### Step 4: Update Settings and Test Again
```bash
# Change learning style
curl -X PATCH http://localhost:8000/api/onboarding \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"learningStyle": "CLASSIC"}'

# Request another lesson
curl -X POST http://localhost:8000/lesson/generate \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Teach me about photosynthesis"}' | jq .
```

**Verify in response:**
- Lesson structure is now siloed by subject (CLASSIC)
- Cross-curricular connections removed
- All other adaptations remain the same

## Troubleshooting

### Issue: Student profile not found (404)
**Cause:** GET /api/onboarding can't find User record
**Solution:**
1. Verify user completed onboarding (POST succeeded)
2. Check database: `SELECT * FROM "User"` — does row exist?
3. Check auth token — is it valid and matches user ID?

### Issue: Lessons don't respect grade level
**Cause:** Agents not querying User table, or using wrong fields
**Solution:**
1. Check agent code — does it fetch student profile?
2. Check field names match schema (gradeLevel not grade_level)
3. Verify database has data: `SELECT gradeLevel FROM "User"`
4. Check logs for agent errors

### Issue: Interests not showing in lessons
**Cause:** interests array not parsed correctly in agent
**Solution:**
1. Verify interests stored as array in Postgres (use `\d "User"`)
2. Check agent code — is it iterating interests correctly?
3. Verify no database type conversion issues

### Issue: Settings changes not taking effect
**Cause:** Agents caching student profile or not re-fetching
**Solution:**
1. Ensure agents fetch profile fresh on each lesson request
2. Don't cache student data across requests
3. Verify PATCH updates database: `SELECT * FROM "User"`

## Success Criteria

The brain integration is working correctly when:

- ✅ All student profile data persists in Postgres after onboarding
- ✅ API endpoints return correct data with proper authorization
- ✅ Agents query User table for each lesson generation
- ✅ Generated lessons adapt vocabulary to gradeLevel
- ✅ Lessons include references to student interests
- ✅ Lesson structure respects learningStyle (EXPEDITION vs. CLASSIC)
- ✅ Lesson length reflects pacingMultiplier
- ✅ Settings updates immediately affect next lesson (no caching)
- ✅ Subject-specific overrides work (mathLevel overrides gradeLevel for math)
- ✅ State-specific curriculum standards applied
- ✅ NULL fields handled gracefully (fallback to defaults)
