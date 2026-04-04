'use client';

import { useState } from 'react';
import { ChevronRight, ChevronLeft } from 'lucide-react';
import { INTERESTS_OPTIONS, LEARNING_STYLES, US_STATES } from './constants';

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

const GRADE_OPTIONS = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];
const CURRENT_YEAR = new Date().getFullYear();
const YEAR_RANGE = Array.from({ length: 21 }, (_, i) => CURRENT_YEAR + i);

export function WelcomeFlow({ onComplete }: WelcomeFlowProps) {
  const [step, setStep] = useState(0);
  const [coppaConsent, setCoppaConsent] = useState(false);
  const [name, setName] = useState('');
  const [gradeLevel, setGradeLevel] = useState('');
  const [interests, setInterests] = useState<string[]>([]);
  const [learningStyle, setLearningStyle] = useState('EXPEDITION');
  const [state, setState] = useState('');
  const [targetGraduationYear, setTargetGraduationYear] = useState(CURRENT_YEAR + 4);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateStep = (stepNum: number): boolean => {
    const newErrors: Record<string, string> = {};

    if (stepNum === 1) {
      if (!coppaConsent) {
        newErrors.coppaConsent = 'Please provide parent/guardian consent to continue';
      }
    } else if (stepNum === 2) {
      if (!name.trim()) newErrors.name = 'Child name is required';
      if (!gradeLevel) newErrors.gradeLevel = 'Grade level is required';
      if (interests.length === 0) newErrors.interests = 'Please select at least one interest';
    } else if (stepNum === 4) {
      if (!state) newErrors.state = 'Please select a state';
      if (!targetGraduationYear) newErrors.year = 'Please select a graduation year';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(step)) {
      if (step === 4) {
        // Final step — submit
        onComplete({
          name,
          gradeLevel,
          interests,
          learningStyle,
          state,
          targetGraduationYear,
          coppaConsent,
        });
      } else {
        setStep(step + 1);
      }
    }
  };

  const handlePrevious = () => {
    setErrors({});
    setStep(step - 1);
  };

  const toggleInterest = (interest: string) => {
    setInterests((prev) =>
      prev.includes(interest) ? prev.filter((i) => i !== interest) : [...prev, interest]
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-2xl bg-white rounded-3xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#2F4731] to-[#3D5A3F] px-8 py-6 text-white">
          <h1
            className="text-3xl font-bold mb-2"
            style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}
          >
            Welcome to Adeline
          </h1>
          <p className="text-white/80 text-sm">
            Step {step + 1} of 5 — Let's set up your learning plan
          </p>
          {/* Progress bar */}
          <div className="mt-4 h-1 bg-white/20 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#BD6809] transition-all duration-300"
              style={{ width: `${((step + 1) / 5) * 100}%` }}
            />
          </div>
        </div>

        {/* Content */}
        <div className="px-8 py-6 min-h-80">
          {/* Step 0: Welcome */}
          {step === 0 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-[#2F4731]">Welcome, Parents & Learners!</h2>
              <p className="text-[#2F4731]/70 leading-relaxed">
                Adeline is an AI learning companion that adapts to your child's unique interests, learning
                style, and pace. By learning a bit about your student, Adeline can create personalized lessons
                in science, history, literature, and more — tailored to their strengths and what excites them.
              </p>
              <p className="text-[#2F4731]/70 leading-relaxed">
                Let's get started by gathering some information about your learner. This should take about
                5 minutes.
              </p>
            </div>
          )}

          {/* Step 1: Parent Consent */}
          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-[#2F4731]">Parent/Guardian Consent</h2>
              <div className="bg-[#FFFEF7] border-2 border-[#E7DAC3] rounded-xl p-4">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={coppaConsent}
                    onChange={(e) => {
                      setCoppaConsent(e.target.checked);
                      setErrors((prev) => ({ ...prev, coppaConsent: '' }));
                    }}
                    className="w-5 h-5 rounded border-[#BD6809] text-[#BD6809] focus:ring-[#BD6809] mt-0.5"
                  />
                  <span className="text-[#2F4731] text-sm leading-relaxed">
                    I am the parent/guardian. I consent to my child using Adeline and understand that Adeline
                    is an AI educational tool that helps personalize learning. I have read and agree to the
                    privacy policy and terms of service.
                  </span>
                </label>
              </div>
              {errors.coppaConsent && (
                <p className="text-red-600 text-sm">{errors.coppaConsent}</p>
              )}
            </div>
          )}

          {/* Step 2: Child Info */}
          {step === 2 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-[#2F4731]">Tell Us About Your Learner</h2>

              {/* Name */}
              <div>
                <label className="block text-sm font-semibold text-[#2F4731] mb-2">
                  Child's Full Name *
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    setErrors((prev) => ({ ...prev, name: '' }));
                  }}
                  placeholder="e.g., Emma Johnson"
                  className="w-full px-4 py-2 border-2 border-[#E7DAC3] rounded-lg focus:outline-none focus:border-[#BD6809] text-[#2F4731]"
                />
                {errors.name && <p className="text-red-600 text-sm mt-1">{errors.name}</p>}
              </div>

              {/* Grade Level */}
              <div>
                <label className="block text-sm font-semibold text-[#2F4731] mb-2">
                  Current Grade Level *
                </label>
                <div className="grid grid-cols-7 gap-2">
                  {GRADE_OPTIONS.map((g) => (
                    <button
                      key={g}
                      onClick={() => {
                        setGradeLevel(g);
                        setErrors((prev) => ({ ...prev, gradeLevel: '' }));
                      }}
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
                {errors.gradeLevel && <p className="text-red-600 text-sm mt-1">{errors.gradeLevel}</p>}
              </div>

              {/* Interests */}
              <div>
                <label className="block text-sm font-semibold text-[#2F4731] mb-2">
                  Interests (select at least 1) *
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {INTERESTS_OPTIONS.map((interest) => (
                    <button
                      key={interest}
                      onClick={() => {
                        toggleInterest(interest);
                        setErrors((prev) => ({ ...prev, interests: '' }));
                      }}
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
                {errors.interests && <p className="text-red-600 text-sm mt-1">{errors.interests}</p>}
              </div>
            </div>
          )}

          {/* Step 3: Learning Style */}
          {step === 3 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-[#2F4731]">Learning Style</h2>
              <p className="text-[#2F4731]/70">How does your learner prefer to explore topics?</p>

              <div className="space-y-3">
                {LEARNING_STYLES.map((style) => (
                  <label
                    key={style.value}
                    className="block p-4 border-2 border-[#E7DAC3] rounded-lg cursor-pointer hover:border-[#BD6809] transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="radio"
                        name="learningStyle"
                        value={style.value}
                        checked={learningStyle === style.value}
                        onChange={(e) => setLearningStyle(e.target.value)}
                        className="w-5 h-5 text-[#BD6809] border-[#BD6809] focus:ring-[#BD6809] mt-0.5"
                      />
                      <div>
                        <h3 className="font-semibold text-[#2F4731]">{style.label}</h3>
                        <p className="text-sm text-[#2F4731]/60 mt-1">{style.description}</p>
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Step 4: Graduation Plan */}
          {step === 4 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-[#2F4731]">Create Your Learning Plan</h2>

              {/* State */}
              <div>
                <label className="block text-sm font-semibold text-[#2F4731] mb-2">
                  State *
                </label>
                <select
                  value={state}
                  onChange={(e) => {
                    setState(e.target.value);
                    setErrors((prev) => ({ ...prev, state: '' }));
                  }}
                  className="w-full px-4 py-2 border-2 border-[#E7DAC3] rounded-lg focus:outline-none focus:border-[#BD6809] text-[#2F4731]"
                >
                  <option value="">Select a state…</option>
                  {US_STATES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                {errors.state && <p className="text-red-600 text-sm mt-1">{errors.state}</p>}
              </div>

              {/* Target Graduation Year */}
              <div>
                <label className="block text-sm font-semibold text-[#2F4731] mb-2">
                  Target Graduation Year *
                </label>
                <select
                  value={targetGraduationYear}
                  onChange={(e) => {
                    setTargetGraduationYear(Number(e.target.value));
                    setErrors((prev) => ({ ...prev, year: '' }));
                  }}
                  className="w-full px-4 py-2 border-2 border-[#E7DAC3] rounded-lg focus:outline-none focus:border-[#BD6809] text-[#2F4731]"
                >
                  {YEAR_RANGE.map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
                </select>
                {errors.year && <p className="text-red-600 text-sm mt-1">{errors.year}</p>}
              </div>
            </div>
          )}
        </div>

        {/* Footer / Navigation */}
        <div className="flex items-center justify-between gap-4 px-8 py-4 bg-[#FFFEF7] border-t-2 border-[#E7DAC3]">
          <button
            onClick={handlePrevious}
            disabled={step === 0}
            className="flex items-center gap-2 px-4 py-2 text-[#BD6809] disabled:opacity-30 disabled:cursor-not-allowed hover:text-[#2F4731] font-semibold transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
            Back
          </button>

          <button
            onClick={handleNext}
            className="flex items-center gap-2 px-6 py-2 bg-[#BD6809] text-white rounded-lg font-semibold hover:bg-[#A55708] transition-colors"
          >
            {step === 4 ? 'Complete Setup' : 'Next'}
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
