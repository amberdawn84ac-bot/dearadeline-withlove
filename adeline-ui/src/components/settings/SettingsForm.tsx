'use client';

import { useState } from 'react';
import { Loader2, Check, AlertCircle } from 'lucide-react';
import { INTERESTS_OPTIONS, LEARNING_STYLES, US_STATES } from '@/components/onboarding/constants';

interface UserProfile {
  id: string;
  name: string;
  gradeLevel: string;
  mathLevel?: number;
  elaLevel?: number;
  scienceLevel?: number;
  historyLevel?: number;
  interests: string[];
  learningStyle?: string;
  pacingMultiplier: number;
  state?: string;
  targetGraduationYear?: number;
  onboardingComplete: boolean;
}

interface SettingsFormProps {
  initialProfile: UserProfile;
}

const GRADE_OPTIONS = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];
const SUBJECT_GRADES = Array.from({ length: 13 }, (_, i) => i);
const PACING_OPTIONS = [
  { value: 1.0, label: 'Standard (1.0x)' },
  { value: 1.25, label: 'Accelerated (1.25x)' },
  { value: 1.5, label: 'Fast Track (1.5x)' },
  { value: 2.0, label: 'Sprint (2.0x)' },
];
const CURRENT_YEAR = new Date().getFullYear();
const YEAR_RANGE = Array.from({ length: 21 }, (_, i) => CURRENT_YEAR + i);

export function SettingsForm({ initialProfile }: SettingsFormProps) {
  const [gradeLevel, setGradeLevel] = useState(initialProfile.gradeLevel);
  const [mathLevel, setMathLevel] = useState<number | null>(initialProfile.mathLevel || null);
  const [elaLevel, setElaLevel] = useState<number | null>(initialProfile.elaLevel || null);
  const [scienceLevel, setScienceLevel] = useState<number | null>(initialProfile.scienceLevel || null);
  const [historyLevel, setHistoryLevel] = useState<number | null>(initialProfile.historyLevel || null);
  const [interests, setInterests] = useState(initialProfile.interests);
  const [learningStyle, setLearningStyle] = useState(initialProfile.learningStyle || 'EXPEDITION');
  const [pacingMultiplier, setPacingMultiplier] = useState(initialProfile.pacingMultiplier);
  const [state, setState] = useState(initialProfile.state || '');
  const [targetGraduationYear, setTargetGraduationYear] = useState(initialProfile.targetGraduationYear || CURRENT_YEAR + 4);
  const [useMathOverride, setUseMathOverride] = useState(mathLevel !== null);
  const [useElaOverride, setUseElaOverride] = useState(elaLevel !== null);
  const [useScienceOverride, setUseScienceOverride] = useState(scienceLevel !== null);
  const [useHistoryOverride, setUseHistoryOverride] = useState(historyLevel !== null);

  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [saveError, setSaveError] = useState<string | null>(null);

  const toggleInterest = (interest: string) => {
    setInterests((prev) =>
      prev.includes(interest) ? prev.filter((i) => i !== interest) : [...prev, interest]
    );
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setSaveStatus('idle');
      setSaveError(null);

      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : '';

      const updateData: Record<string, unknown> = {
        gradeLevel,
        interests,
        learningStyle,
        pacingMultiplier,
        state,
        targetGraduationYear,
      };

      // Only include subject levels if the override is enabled
      if (useMathOverride) updateData.mathLevel = mathLevel;
      if (useElaOverride) updateData.elaLevel = elaLevel;
      if (useScienceOverride) updateData.scienceLevel = scienceLevel;
      if (useHistoryOverride) updateData.historyLevel = historyLevel;

      const response = await fetch('/brain/api/onboarding', {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save settings');
      }

      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save settings';
      setSaveError(message);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left column: Form fields */}
      <div className="lg:col-span-2 space-y-6">
        {/* Overall Grade Level */}
        <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
          <h3 className="text-lg font-bold text-[#2F4731] mb-4">Overall Grade Level</h3>
          <div className="grid grid-cols-7 gap-2">
            {GRADE_OPTIONS.map((g) => (
              <button
                key={g}
                onClick={() => setGradeLevel(g)}
                className={`py-2 px-1 rounded-lg font-semibold transition-colors text-sm ${
                  gradeLevel === g
                    ? 'bg-[#BD6809] text-white'
                    : 'border-2 border-[#E7DAC3] text-[#2F4731] hover:border-[#BD6809]'
                }`}
              >
                {g}
              </button>
            ))}
          </div>
        </div>

        {/* Subject-Specific Levels */}
        <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
          <h3 className="text-lg font-bold text-[#2F4731] mb-4">Subject-Specific Levels (Optional)</h3>
          <p className="text-sm text-[#2F4731]/60 mb-4">
            Override the overall grade for specific subjects. Leave unchecked to use overall grade.
          </p>

          <div className="space-y-4">
            {/* Math */}
            <div>
              <label className="flex items-center gap-3 mb-2">
                <input
                  type="checkbox"
                  checked={useMathOverride}
                  onChange={(e) => setUseMathOverride(e.target.checked)}
                  className="w-5 h-5 rounded text-[#BD6809]"
                />
                <span className="font-semibold text-[#2F4731]">Math</span>
              </label>
              {useMathOverride && (
                <select
                  value={mathLevel || ''}
                  onChange={(e) => setMathLevel(e.target.value ? Number(e.target.value) : null)}
                  className="w-full px-3 py-2 border-2 border-[#E7DAC3] rounded-lg text-[#2F4731] focus:outline-none focus:border-[#BD6809]"
                >
                  <option value="">Select level…</option>
                  {SUBJECT_GRADES.map((grade) => (
                    <option key={grade} value={grade}>
                      {grade === 0 ? 'K' : grade}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* ELA */}
            <div>
              <label className="flex items-center gap-3 mb-2">
                <input
                  type="checkbox"
                  checked={useElaOverride}
                  onChange={(e) => setUseElaOverride(e.target.checked)}
                  className="w-5 h-5 rounded text-[#BD6809]"
                />
                <span className="font-semibold text-[#2F4731]">English Language Arts</span>
              </label>
              {useElaOverride && (
                <select
                  value={elaLevel || ''}
                  onChange={(e) => setElaLevel(e.target.value ? Number(e.target.value) : null)}
                  className="w-full px-3 py-2 border-2 border-[#E7DAC3] rounded-lg text-[#2F4731] focus:outline-none focus:border-[#BD6809]"
                >
                  <option value="">Select level…</option>
                  {SUBJECT_GRADES.map((grade) => (
                    <option key={grade} value={grade}>
                      {grade === 0 ? 'K' : grade}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Science */}
            <div>
              <label className="flex items-center gap-3 mb-2">
                <input
                  type="checkbox"
                  checked={useScienceOverride}
                  onChange={(e) => setUseScienceOverride(e.target.checked)}
                  className="w-5 h-5 rounded text-[#BD6809]"
                />
                <span className="font-semibold text-[#2F4731]">Science</span>
              </label>
              {useScienceOverride && (
                <select
                  value={scienceLevel || ''}
                  onChange={(e) => setScienceLevel(e.target.value ? Number(e.target.value) : null)}
                  className="w-full px-3 py-2 border-2 border-[#E7DAC3] rounded-lg text-[#2F4731] focus:outline-none focus:border-[#BD6809]"
                >
                  <option value="">Select level…</option>
                  {SUBJECT_GRADES.map((grade) => (
                    <option key={grade} value={grade}>
                      {grade === 0 ? 'K' : grade}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* History */}
            <div>
              <label className="flex items-center gap-3 mb-2">
                <input
                  type="checkbox"
                  checked={useHistoryOverride}
                  onChange={(e) => setUseHistoryOverride(e.target.checked)}
                  className="w-5 h-5 rounded text-[#BD6809]"
                />
                <span className="font-semibold text-[#2F4731]">History</span>
              </label>
              {useHistoryOverride && (
                <select
                  value={historyLevel || ''}
                  onChange={(e) => setHistoryLevel(e.target.value ? Number(e.target.value) : null)}
                  className="w-full px-3 py-2 border-2 border-[#E7DAC3] rounded-lg text-[#2F4731] focus:outline-none focus:border-[#BD6809]"
                >
                  <option value="">Select level…</option>
                  {SUBJECT_GRADES.map((grade) => (
                    <option key={grade} value={grade}>
                      {grade === 0 ? 'K' : grade}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>
        </div>

        {/* Learning Pace */}
        <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
          <h3 className="text-lg font-bold text-[#2F4731] mb-4">Learning Pace</h3>
          <div className="space-y-2">
            {PACING_OPTIONS.map((option) => (
              <label key={option.value} className="flex items-center gap-3 p-3 border-2 border-transparent rounded-lg hover:border-[#E7DAC3] cursor-pointer transition-colors">
                <input
                  type="radio"
                  name="pacing"
                  value={option.value}
                  checked={pacingMultiplier === option.value}
                  onChange={() => setPacingMultiplier(option.value)}
                  className="w-5 h-5 text-[#BD6809]"
                />
                <span className="text-[#2F4731] font-medium">{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Learning Style */}
        <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
          <h3 className="text-lg font-bold text-[#2F4731] mb-4">Learning Mode</h3>
          <div className="space-y-3">
            {LEARNING_STYLES.map((style) => (
              <label key={style.value} className="block p-4 border-2 border-[#E7DAC3] rounded-lg cursor-pointer hover:border-[#BD6809] transition-colors">
                <div className="flex items-start gap-3">
                  <input
                    type="radio"
                    name="learningStyle"
                    value={style.value}
                    checked={learningStyle === style.value}
                    onChange={(e) => setLearningStyle(e.target.value)}
                    className="w-5 h-5 text-[#BD6809] mt-0.5"
                  />
                  <div>
                    <h4 className="font-semibold text-[#2F4731]">{style.label}</h4>
                    <p className="text-sm text-[#2F4731]/60 mt-1">{style.description}</p>
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Interests */}
        <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
          <h3 className="text-lg font-bold text-[#2F4731] mb-4">Interests</h3>
          <div className="grid grid-cols-2 gap-2">
            {INTERESTS_OPTIONS.map((interest) => (
              <button
                key={interest}
                onClick={() => toggleInterest(interest)}
                className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                  interests.includes(interest)
                    ? 'bg-[#2F4731] text-white'
                    : 'border-2 border-[#E7DAC3] text-[#2F4731] hover:border-[#BD6809]'
                }`}
              >
                {interest}
              </button>
            ))}
          </div>
        </div>

        {/* Curriculum Alignment */}
        <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
          <h3 className="text-lg font-bold text-[#2F4731] mb-4">Curriculum Alignment</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* State */}
            <div>
              <label className="block text-sm font-semibold text-[#2F4731] mb-2">State</label>
              <select
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="w-full px-3 py-2 border-2 border-[#E7DAC3] rounded-lg text-[#2F4731] focus:outline-none focus:border-[#BD6809]"
              >
                <option value="">Select a state…</option>
                {US_STATES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            {/* Target Graduation Year */}
            <div>
              <label className="block text-sm font-semibold text-[#2F4731] mb-2">Target Graduation Year</label>
              <select
                value={targetGraduationYear}
                onChange={(e) => setTargetGraduationYear(Number(e.target.value))}
                className="w-full px-3 py-2 border-2 border-[#E7DAC3] rounded-lg text-[#2F4731] focus:outline-none focus:border-[#BD6809]"
              >
                {YEAR_RANGE.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Right column: Summary and Save button */}
      <div className="lg:col-span-1">
        <div className="sticky top-24 bg-white rounded-2xl border-2 border-[#E7DAC3] p-6">
          <h3 className="text-lg font-bold text-[#2F4731] mb-6">Summary</h3>

          <div className="space-y-4 mb-6 text-sm">
            <div>
              <p className="text-[#2F4731]/60">Grade Level</p>
              <p className="font-semibold text-[#2F4731]">{gradeLevel}</p>
            </div>

            {(useMathOverride || useElaOverride || useScienceOverride || useHistoryOverride) && (
              <div>
                <p className="text-[#2F4731]/60">Subject Levels</p>
                <ul className="text-[#2F4731] space-y-1">
                  {useMathOverride && <li>• Math: {mathLevel === 0 ? 'K' : mathLevel}</li>}
                  {useElaOverride && <li>• ELA: {elaLevel === 0 ? 'K' : elaLevel}</li>}
                  {useScienceOverride && <li>• Science: {scienceLevel === 0 ? 'K' : scienceLevel}</li>}
                  {useHistoryOverride && <li>• History: {historyLevel === 0 ? 'K' : historyLevel}</li>}
                </ul>
              </div>
            )}

            <div>
              <p className="text-[#2F4731]/60">Pace</p>
              <p className="font-semibold text-[#2F4731]">{pacingMultiplier.toFixed(2)}x</p>
            </div>

            <div>
              <p className="text-[#2F4731]/60">Learning Mode</p>
              <p className="font-semibold text-[#2F4731]">{learningStyle === 'EXPEDITION' ? 'Expedition' : 'Classic'}</p>
            </div>

            <div>
              <p className="text-[#2F4731]/60">Interests</p>
              <p className="font-semibold text-[#2F4731]">{interests.length} selected</p>
            </div>

            {state && (
              <div>
                <p className="text-[#2F4731]/60">State</p>
                <p className="font-semibold text-[#2F4731]">{state}</p>
              </div>
            )}

            <div>
              <p className="text-[#2F4731]/60">Graduation Year</p>
              <p className="font-semibold text-[#2F4731]">{targetGraduationYear}</p>
            </div>
          </div>

          {/* Status messages */}
          {saveStatus === 'success' && (
            <div className="mb-4 p-3 bg-green-50 border-2 border-green-200 rounded-lg flex items-start gap-2">
              <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <p className="text-green-700 text-sm font-medium">Settings saved! Adeline will adapt to your changes in the next lesson.</p>
            </div>
          )}

          {saveStatus === 'error' && (
            <div className="mb-4 p-3 bg-red-50 border-2 border-red-200 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-700 text-sm font-medium">Failed to save settings</p>
                <p className="text-red-600 text-xs mt-1">{saveError}</p>
              </div>
            </div>
          )}

          {/* Save button */}
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="w-full px-4 py-3 bg-[#BD6809] text-white rounded-lg font-semibold hover:bg-[#A55708] disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Saving…
              </>
            ) : (
              'Save Changes'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
