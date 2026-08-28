import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export const TOUR_STEPS = [
  {
    step: 1,
    route: '/',
    targetSelector: '[data-demo="hero-section"]',
    stage: '01. Executive Overview',
    title: 'The Problem: Fragmented Skill Ecosystem',
    description: 'SkillSetu connects fragmented labour-market demand, vocational training supply, and candidate career pathways into one unified real-time intelligence platform across Maharashtra.',
    whyItMatters: 'Without live demand telemetry, public training investments and ITI quotas are allocated using multi-year-old static surveys.',
    badge: 'Core Architecture',
  },
  {
    step: 2,
    route: '/government',
    targetSelector: '[data-demo="government-kpis"]',
    stage: '02. State Intelligence',
    title: 'State-Wide Labour-Market Sensing',
    description: 'Government leadership gains a single unified command view of active job postings, indexed technical skills, institutional training capacities, and emerging demand trends across Maharashtra.',
    whyItMatters: 'Establishes a single source of truth across 36 districts and major vocational boards (MSBTE, DVET, MSSDS).',
    badge: 'Live State KPIs',
  },
  {
    step: 3,
    route: '/government',
    targetSelector: '[data-demo="skill-gaps-table"]',
    stage: '03. Gap Analytics',
    title: 'Automated Skill Gap Detection',
    description: 'The platform dynamically computes Skill Gap % using the formula (Demand Frequency % − Curriculum Coverage % = Net Talent Deficit), prioritizing critical shortages like AI/ML, EV, and Cloud.',
    whyItMatters: 'Prevents public funding from being poured into saturated trades while high-demand technical sectors face critical talent shortages.',
    badge: 'Demand - Coverage = Gap',
  },
  {
    step: 4,
    route: '/government',
    targetSelector: '[data-demo="district-heatmap"]',
    stage: '04. Geo-Intelligence',
    title: 'Granular District-Level Telemetry',
    description: 'Macro state trends are broken down into district-level evidence across Pune, Mumbai, Nagpur, Chhatrapati Sambhajinagar, and rural vocational belts.',
    whyItMatters: 'Workforce demand in the Chakan EV corridor is drastically different from precision agriculture needs in Vidarbha.',
    badge: 'District Heatmap',
  },
  {
    step: 5,
    route: '/government/district/Pune',
    targetSelector: '[data-demo="district-micro-plan"]',
    stage: '05. Micro-Planning',
    title: 'Actionable District Training Micro-Plans',
    description: 'Moves government from passive analysis to concrete execution: recommends exact seat reallocations, equipment investments, and certified trainer requirements for Pune district.',
    whyItMatters: 'Turns abstract labour data into specific budget line items and operational training quotas.',
    badge: 'Pune Micro-Plan',
  },
  {
    step: 6,
    route: '/institute',
    targetSelector: '[data-demo="course-health-grid"]',
    stage: '06. Academic Alignment',
    title: 'Institute Curriculum Health & Obsolescence Flags',
    description: 'Training institutes and ITIs inspect course placement outcomes, flag obsolete syllabi (<30% placement with declining demand), and receive automated NCO/NSQF curriculum upgrade recommendations.',
    whyItMatters: 'Stops vocational institutions from graduating thousands of students into saturated, obsolete job roles.',
    badge: 'Obsolescence Flags',
  },
  {
    step: 7,
    route: '/employer',
    targetSelector: '[data-demo="employer-validation-queue"]',
    stage: '07. Industry Validation',
    title: 'Employer Feedback Loop & Calibration',
    description: 'AI-generated demand signals are never blindly trusted. Industry employers review, Confirm, Correct, or Reject skill signals, and submit direct hiring demands.',
    whyItMatters: 'Ensures state training policies remain grounded in genuine industry hiring consensus, preventing AI hallucination.',
    badge: 'Human-in-the-Loop',
  },
  {
    step: 8,
    route: '/student',
    targetSelector: '[data-demo="student-passport-radar"]',
    stage: '08. Candidate Pathway',
    title: 'Student Personalized Skill Passport',
    description: 'Individual candidates view verified competency radars, benchmark their current skills against target industry roles, and track personalized sequential learning roadmaps.',
    whyItMatters: 'Empowers youth with transparent career visibility, matching them directly with state welfare schemes and verified apprenticeships.',
    badge: 'Competency Radar',
  },
  {
    step: 9,
    route: '/student/copilot',
    targetSelector: '[data-demo="copilot-chat-container"]',
    stage: '09. Grounded AI',
    title: 'Evidence-Based AI Copilot (No Hallucinations)',
    description: 'Powered by Gemini 3.6 with strict database grounding and rule-based offline fallback. Answers queries with verifiable citations and explicitly admits when skills are unavailable.',
    whyItMatters: 'Students and officials get instant conversational intelligence backed by real indexed Maharashtra job postings.',
    badge: 'Grounded Intelligence',
  },
  {
    step: 10,
    route: '/student',
    targetSelector: '[data-demo="student-industry-alerts"]',
    stage: '10. Industry Telemetry',
    title: 'Real-Time Industry Technology Alerts',
    description: 'Interactive domain chips for 7 high-growth sectors (AI/ML, Data Science, Cloud, Cybersecurity, Robotics, EV, IoT) deliver targeted vacancy shifts and actionable next steps.',
    whyItMatters: 'Alerts students early to regional industrial investments (e.g. Chakan EV plants) so they can upskill before graduation.',
    badge: '7 Growth Sectors',
  },
  {
    step: 11,
    route: '/student',
    targetSelector: '[data-demo="skill-explainability-trigger"]',
    stage: '11. Explainable AI',
    title: '5-Dimension Grounded Skill Explainability',
    description: 'SkillSetu does not just say "learn this skill"—it provides transparent evidence across Demand Surge, Future Forecasts, Employer Consensus, Curriculum Deficit, and Academic Council Rationale.',
    whyItMatters: 'Builds trust and motivation by answering the fundamental question of why a specific competency is worth the student\'s time and effort.',
    badge: '5-Point Evidence',
  },
  {
    step: 12,
    route: '/government',
    targetSelector: '[data-demo="policy-whatif-simulator"]',
    stage: '12. Decision Support',
    title: 'Government Policy What-If Simulator',
    description: 'Decision-makers simulate the impact of adding training seats, curriculum stagnation over 1–5 years, or introducing new courses before investing state funds. Every output is clearly tagged SIMULATED ESTIMATE.',
    whyItMatters: 'Enables evidence-based risk assessment and budget optimization before committing tens of crores in public capital.',
    badge: 'Policy Simulator',
  },
  {
    step: 13,
    route: '/',
    targetSelector: null,
    stage: '13. Closed Loop Outcome',
    title: 'Closing the Loop: From Data to Measurable Impact',
    description: 'Labour Demand → Skill Gap Detection → Training Alignment → Employer Validation → Student Action → Policy Simulation → Measurable Employment.',
    whyItMatters: 'SkillSetu turns fragmented skill data into actionable, accountable, and scalable workforce transformation for Maharashtra.',
    badge: 'Measurable Outcomes',
  },
];

const TourContext = createContext(null);

export function TourProvider({ children }) {
  const [isTourOpen, setIsTourOpen] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();

  const totalSteps = TOUR_STEPS.length;
  const currentStep = TOUR_STEPS[currentStepIndex] || TOUR_STEPS[0];

  const startTour = useCallback(() => {
    setCurrentStepIndex(0);
    setIsTourOpen(true);
    const firstStep = TOUR_STEPS[0];
    if (location.pathname !== firstStep.route) {
      navigate(firstStep.route);
    }
  }, [location.pathname, navigate]);

  const exitTour = useCallback(() => {
    setIsTourOpen(false);
  }, []);

  const goToStep = useCallback(
    (stepNumber) => {
      const idx = Math.max(0, Math.min(totalSteps - 1, stepNumber - 1));
      setCurrentStepIndex(idx);
      const targetStep = TOUR_STEPS[idx];
      if (targetStep && location.pathname !== targetStep.route) {
        navigate(targetStep.route);
      }
    },
    [totalSteps, location.pathname, navigate]
  );

  const nextStep = useCallback(() => {
    if (currentStepIndex < totalSteps - 1) {
      goToStep(currentStepIndex + 2); // 1-indexed
    } else {
      exitTour();
    }
  }, [currentStepIndex, totalSteps, goToStep, exitTour]);

  const prevStep = useCallback(() => {
    if (currentStepIndex > 0) {
      goToStep(currentStepIndex); // 1-indexed
    }
  }, [currentStepIndex, goToStep]);

  // Global Keyboard Navigation (Escape, ArrowLeft, ArrowRight)
  useEffect(() => {
    if (!isTourOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        exitTour();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        nextStep();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prevStep();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isTourOpen, nextStep, prevStep, exitTour]);

  const value = {
    isTourOpen,
    currentStepIndex,
    currentStep,
    totalSteps,
    startTour,
    exitTour,
    nextStep,
    prevStep,
    goToStep,
  };

  return <TourContext.Provider value={value}>{children}</TourContext.Provider>;
}

export function useTour() {
  const context = useContext(TourContext);
  if (!context) {
    throw new Error('useTour must be used within a TourProvider');
  }
  return context;
}
