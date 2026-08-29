import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useTour } from '../context/TourContext';

export default function DemoTour() {
  const location = useLocation();
  const {
    isTourOpen,
    currentStepIndex,
    currentStep,
    totalSteps,
    nextStep,
    prevStep,
    exitTour,
  } = useTour();

  const [targetRect, setTargetRect] = useState(null);
  const [popoverPos, setPopoverPos] = useState({ top: 0, left: 0, placement: 'bottom' });
  const popoverRef = useRef(null);

  // Position calculation and scroll synchronization
  const updatePosition = useCallback(() => {
    if (!isTourOpen || !currentStep) return;

    if (!currentStep.targetSelector) {
      setTargetRect(null);
      return;
    }

    // Verify route synchronization before finding target
    const expectedRoute = currentStep.route ? currentStep.route.split('?')[0] : null;
    if (expectedRoute && location.pathname !== expectedRoute) {
      setTargetRect(null);
      return;
    }

    const el = document.querySelector(currentStep.targetSelector);
    if (el) {
      const rect = el.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        setTargetRect({
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
          bottom: rect.bottom,
          right: rect.right,
        });

        // Position popover
        const popoverWidth = Math.min(460, window.innerWidth - 32);
        const popoverHeight = 320;
        const padding = 12;

        let left = Math.max(
          16,
          Math.min(
            rect.left + (rect.width / 2) - (popoverWidth / 2),
            window.innerWidth - popoverWidth - 16
          )
        );

        let top;
        let placement = 'bottom';

        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;

        // 1. If enough space below the element, place below
        if (spaceBelow >= popoverHeight + padding) {
          top = rect.bottom + padding;
          placement = 'bottom';
        }
        // 2. If enough space above the element, place above
        else if (spaceAbove >= popoverHeight + padding) {
          top = rect.top - popoverHeight - padding;
          placement = 'top';
        }
        // 3. For tall elements occupying large vertical space, anchor to the side with more room
        else if (spaceAbove > spaceBelow) {
          top = Math.max(16, rect.top - popoverHeight - padding);
          placement = 'top';
        } else {
          top = Math.max(16, Math.min(rect.bottom + padding, window.innerHeight - popoverHeight - 16));
          placement = 'bottom';
        }

        setPopoverPos({ top, left, placement });
        return;
      }
    }
    setTargetRect(null);
  }, [isTourOpen, currentStep, location.pathname]);

  // Auto-scroll to element and continuously track position across layout shifts / smooth scrolls
  useEffect(() => {
    if (!isTourOpen || !currentStep) return;

    const expectedRoute = currentStep.route ? currentStep.route.split('?')[0] : null;
    let attempts = 0;
    const maxAttempts = 40; // 4s total search window for async rendered components

    const alignAndTrack = () => {
      attempts += 1;

      // Check route synchronization first
      if (expectedRoute && location.pathname !== expectedRoute) {
        setTargetRect(null);
        if (currentStepIndex === 4) {
          console.log('[Tour Step 5] Waiting for route transition:', {
            currentRoute: location.pathname,
            expectedRoute,
          });
        }
        return;
      }

      if (!currentStep.targetSelector) {
        setTargetRect(null);
        return;
      }

      const el = document.querySelector(currentStep.targetSelector);
      if (el) {
        const rect = el.getBoundingClientRect();

        // Step 5 Instrumentation / Logging
        if (currentStepIndex === 4) {
          console.log('=== TOUR STEP 5 DEBUG ===');
          console.log('TOUR STEP = 5');
          console.log('CURRENT ROUTE =', location.pathname);
          console.log('EXPECTED ROUTE =', expectedRoute);
          console.log('TARGET SELECTOR =', currentStep.targetSelector);
          console.log('TARGET FOUND =', true);
          console.log('TARGET RECT =', rect);
          console.log('TARGET HEIGHT =', rect.height);
          console.log('TARGET TOP =', rect.top);
          console.log('TARGET BOTTOM =', rect.bottom);
          console.log('SCROLL POSITION =', window.pageYOffset);
        }

        if (rect.width > 0 && rect.height > 0) {
          // Calculate intended viewport position
          let targetY;
          if (rect.height > window.innerHeight * 0.45) {
            targetY = el.getBoundingClientRect().top + window.pageYOffset - 80;
          } else {
            targetY = el.getBoundingClientRect().top + window.pageYOffset - Math.max(80, (window.innerHeight - rect.height) / 2);
          }

          // If the element is not comfortably in view, smoothly scroll to it
          const isComfortablyInView = rect.top >= 60 && rect.bottom <= window.innerHeight + 100;
          if (!isComfortablyInView || Math.abs(window.pageYOffset - targetY) > 50) {
            window.scrollTo({ top: Math.max(0, targetY), behavior: 'smooth' });
          }

          updatePosition();
        }
      } else {
        if (currentStepIndex === 4) {
          console.log('=== TOUR STEP 5 DEBUG ===');
          console.log('TOUR STEP = 5');
          console.log('CURRENT ROUTE =', location.pathname);
          console.log('EXPECTED ROUTE =', expectedRoute);
          console.log('TARGET SELECTOR =', currentStep.targetSelector);
          console.log('TARGET FOUND =', false);
        }
        if (attempts >= maxAttempts) {
          setTargetRect(null);
        }
      }
    };

    // Run polling interval for smooth transition
    const interval = setInterval(alignAndTrack, 100);

    // Also observe DOM and body resize events to handle async data loading shifts
    const resizeObserver = new ResizeObserver(() => {
      updatePosition();
      const el = currentStep.targetSelector ? document.querySelector(currentStep.targetSelector) : null;
      if (el) {
        const rect = el.getBoundingClientRect();
        if (rect.top < 40 || rect.top > window.innerHeight - 80) {
          const targetY = rect.height > window.innerHeight * 0.45
            ? el.getBoundingClientRect().top + window.pageYOffset - 80
            : el.getBoundingClientRect().top + window.pageYOffset - Math.max(80, (window.innerHeight - rect.height) / 2);
          window.scrollTo({ top: Math.max(0, targetY), behavior: 'smooth' });
        }
      }
    });

    resizeObserver.observe(document.body);

    return () => {
      clearInterval(interval);
      resizeObserver.disconnect();
    };
  }, [isTourOpen, currentStepIndex, currentStep, location.pathname, updatePosition]);

  // Handle window resize and all container scrolls (capture phase)
  useEffect(() => {
    if (!isTourOpen) return;
    const handleScrollOrResize = () => updatePosition();
    window.addEventListener('resize', handleScrollOrResize);
    window.addEventListener('scroll', handleScrollOrResize, { capture: true, passive: true });
    return () => {
      window.removeEventListener('resize', handleScrollOrResize);
      window.removeEventListener('scroll', handleScrollOrResize, { capture: true });
    };
  }, [isTourOpen, updatePosition]);

  if (!isTourOpen || !currentStep) return null;

  const isLastStep = currentStepIndex === totalSteps - 1;
  const progressPct = Math.round(((currentStepIndex + 1) / totalSteps) * 100);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto pointer-events-auto font-sans">
      {/* Semi-Transparent Dimmed Backdrop with Crisp Cutout (Zero Blur) */}
      <svg
        className="fixed inset-0 w-full h-full pointer-events-none z-40 transition-opacity duration-300"
        style={{ width: '100vw', height: '100vh' }}
        aria-hidden="true"
      >
        <defs>
          <mask id="tour-spotlight-cutout">
            {/* White reveals the dark overlay everywhere */}
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            {/* Black cuts a hole out for the active element, leaving it 100% bright & crisp */}
            {targetRect && (
              <rect
                x={targetRect.left - 6}
                y={targetRect.top - 6}
                width={targetRect.width + 12}
                height={targetRect.height + 12}
                rx="12"
                ry="12"
                fill="black"
              />
            )}
          </mask>
        </defs>
        <rect
          x="0"
          y="0"
          width="100%"
          height="100%"
          fill="rgba(2, 6, 23, 0.55)"
          mask="url(#tour-spotlight-cutout)"
        />
      </svg>

      {/* Backdrop Click Handler to Exit Tour */}
      <div
        onClick={exitTour}
        className="fixed inset-0 z-30 cursor-default"
        aria-label="Click to exit tour"
      />

      {/* Target Element Spotlight (Border & Subtle Ambient Glow) */}
      {targetRect && (
        <div
          style={{
            position: 'fixed',
            top: targetRect.top - 6,
            left: targetRect.left - 6,
            width: targetRect.width + 12,
            height: targetRect.height + 12,
          }}
          className="rounded-xl ring-2 ring-teal-400 border border-teal-300/60 shadow-[0_0_25px_rgba(45,212,191,0.35)] pointer-events-none transition-all duration-300 z-40"
        />
      )}

      {/* Step 13: Full Ecosystem Summary Modal (Centered) */}
      {isLastStep ? (
        <div className="fixed inset-0 flex items-center justify-center p-4 z-50">
          <div
            ref={popoverRef}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl max-w-2xl w-full p-6 sm:p-8 animate-scale-in max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-teal-700 to-emerald-600 flex items-center justify-center text-white font-bold text-sm shadow-sm">
                  ✓
                </div>
                <div>
                  <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-teal-600 dark:text-teal-400">
                    Step {currentStep.step} of {totalSteps} • {currentStep.stage}
                  </span>
                  <h3 className="text-xl font-black text-slate-900 dark:text-white">
                    {currentStep.title}
                  </h3>
                </div>
              </div>
              <button
                onClick={exitTour}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                aria-label="Exit SIH Demo Tour"
              >
                ✕
              </button>
            </div>

            {/* Continuous Feedback Loop Infographic */}
            <div className="mt-5 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3 text-center">
                The Complete SkillSetu Intelligence Feedback Loop
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                <div className="p-2.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div className="text-base mb-1">📡</div>
                  <div className="font-bold text-slate-900 dark:text-white">1. Labour Demand</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Live Job Sensing</div>
                </div>
                <div className="p-2.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div className="text-base mb-1">⚡</div>
                  <div className="font-bold text-slate-900 dark:text-white">2. Skill Deficits</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Automated Gaps</div>
                </div>
                <div className="p-2.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div className="text-base mb-1">🎓</div>
                  <div className="font-bold text-slate-900 dark:text-white">3. Institutes</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Curriculum Update</div>
                </div>
                <div className="p-2.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div className="text-base mb-1">🏢</div>
                  <div className="font-bold text-slate-900 dark:text-white">4. Employers</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Human Validation</div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center text-xs mt-2">
                <div className="p-2.5 rounded-lg bg-teal-50 dark:bg-teal-950/40 border border-teal-200 dark:border-teal-800 shadow-2xs">
                  <div className="text-base mb-1">🎯</div>
                  <div className="font-bold text-teal-900 dark:text-teal-200">5. Student Action</div>
                  <div className="text-[10px] text-teal-700 dark:text-teal-400 mt-0.5">5D Explainability</div>
                </div>
                <div className="p-2.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 shadow-2xs">
                  <div className="text-base mb-1">🧪</div>
                  <div className="font-bold text-indigo-900 dark:text-indigo-200">6. Policy Simulator</div>
                  <div className="text-[10px] text-indigo-700 dark:text-indigo-400 mt-0.5">What-If Models</div>
                </div>
                <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 shadow-2xs">
                  <div className="text-base mb-1">📈</div>
                  <div className="font-bold text-emerald-900 dark:text-emerald-200">7. Impact</div>
                  <div className="text-[10px] text-emerald-700 dark:text-emerald-400 mt-0.5">Higher Placement</div>
                </div>
              </div>
            </div>

            {/* 7 Key Differentiators */}
            <div className="mt-5 space-y-2">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Core Competitive Differentiators
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                <div className="flex items-start gap-2 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-teal-600 dark:text-teal-400 font-bold">✓</span>
                  <div><strong className="text-slate-800 dark:text-slate-200">Evidence-Based:</strong> Real Maharashtra job postings and data.gov.in integration.</div>
                </div>
                <div className="flex items-start gap-2 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-teal-600 dark:text-teal-400 font-bold">✓</span>
                  <div><strong className="text-slate-800 dark:text-slate-200">Human-in-the-Loop:</strong> Employers validate and calibrate AI signals.</div>
                </div>
                <div className="flex items-start gap-2 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-teal-600 dark:text-teal-400 font-bold">✓</span>
                  <div><strong className="text-slate-800 dark:text-slate-200">5D Explainability:</strong> Tells students WHY a skill matters before learning.</div>
                </div>
                <div className="flex items-start gap-2 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-teal-600 dark:text-teal-400 font-bold">✓</span>
                  <div><strong className="text-slate-800 dark:text-slate-200">Policy Simulator:</strong> Pre-tests seat additions and stagnation risk.</div>
                </div>
                <div className="flex items-start gap-2 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-teal-600 dark:text-teal-400 font-bold">✓</span>
                  <div><strong className="text-slate-800 dark:text-slate-200">Grounded Copilot:</strong> Zero hallucination with database citation.</div>
                </div>
                <div className="flex items-start gap-2 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-teal-600 dark:text-teal-400 font-bold">✓</span>
                  <div><strong className="text-slate-800 dark:text-slate-200">District Actionable:</strong> Generates concrete trainer & equipment micro-plans.</div>
                </div>
              </div>
            </div>

            {/* Closing Statement */}
            <div className="mt-5 p-3.5 rounded-xl bg-gradient-to-r from-teal-500/10 via-emerald-500/10 to-teal-500/10 border border-teal-500/20 text-center">
              <p className="text-sm font-bold text-teal-900 dark:text-teal-200">
                “SkillSetu turns fragmented skill data into actionable, accountable decisions.”
              </p>
            </div>

            {/* Actions */}
            <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <button
                onClick={prevStep}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
              >
                ← Previous Step
              </button>
              <button
                onClick={exitTour}
                className="px-6 py-2.5 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-700 text-white shadow-md transition-colors"
              >
                Complete SIH Demo Tour 🎉
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Steps 1 to 12: Floating Popover Attached to Target or Fixed in Viewport */
        <div
          style={
            targetRect
              ? {
                  position: 'fixed',
                  top: popoverPos.top,
                  left: popoverPos.left,
                  transform: 'none',
                  width: 'min(460px, calc(100vw - 32px))',
                }
              : {
                  position: 'fixed',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: 'min(460px, calc(100vw - 32px))',
                }
          }
          className="z-50 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl p-5 animate-fade-in transition-all duration-200"
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 font-mono text-[10px] font-bold border border-teal-200 dark:border-teal-800">
                Step {currentStep.step} of {totalSteps}
              </span>
              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 truncate max-w-[200px]">
                {currentStep.stage}
              </span>
            </div>
            <button
              onClick={exitTour}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs px-1.5 py-0.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Exit Tour (Esc)"
            >
              ✕
            </button>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-100 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden mb-3.5">
            <div
              className="bg-gradient-to-r from-teal-500 to-emerald-400 h-full rounded-full transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          {/* Title & Description */}
          <h4 className="text-base font-bold text-slate-900 dark:text-white leading-tight mb-2">
            {currentStep.title}
          </h4>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed mb-3">
            {currentStep.description}
          </p>

          {/* Why it Matters Callout */}
          <div className="p-2.5 rounded-lg bg-amber-50/80 dark:bg-amber-950/30 border border-amber-200/80 dark:border-amber-800/40 text-[11px] text-amber-900 dark:text-amber-200 leading-snug mb-4">
            <span className="font-bold">Why it matters: </span>
            {currentStep.whyItMatters}
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
            <button
              onClick={exitTour}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 font-medium transition-colors"
            >
              Skip Tour
            </button>

            <div className="flex items-center gap-2">
              {currentStepIndex > 0 && (
                <button
                  onClick={prevStep}
                  className="px-3 py-1.5 font-semibold rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  Back
                </button>
              )}
              <button
                onClick={nextStep}
                className="px-4 py-1.5 font-bold rounded-lg bg-teal-600 hover:bg-teal-700 text-white shadow-xs transition-colors flex items-center gap-1"
              >
                <span>Next</span>
                <span>→</span>
              </button>
            </div>
          </div>

          {/* Keyboard hint */}
          <div className="mt-2.5 text-[10px] text-slate-400 dark:text-slate-500 text-center font-mono flex items-center justify-center gap-3">
            <span>[← / →] Navigate</span>
            <span>•</span>
            <span>[Esc] Exit Tour</span>
          </div>
        </div>
      )}
    </div>
  );
}
