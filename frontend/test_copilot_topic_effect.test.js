import test from 'node:test';
import assert from 'node:assert/strict';

// Test the pure topic effect logic isolated from CopilotChat component
function runTopicEffect({
  initialPrompt,
  initialTopic,
  recommendationContext,
  autoSend,
  students = [],
  studentId = '',
  initialStudentId = '',
  hasAutoSent = false,
  onSetQuestion,
  onHandleSend,
}) {
  const topic = recommendationContext?.topic || initialTopic;
  if (!topic || hasAutoSent) return;

  // contextualQuery must NOT overwrite an explicit initialPrompt
  if (initialPrompt && initialPrompt.trim()) {
    return;
  }

  const targetRole =
    recommendationContext?.target_role ||
    (students.find((s) => s.user_id === (initialStudentId || studentId))?.target_role) ||
    'AI Engineer';

  const contextualQuery = `Explain why I should learn ${topic} based on my SkillSetu profile and current Maharashtra labour-market intelligence. My target role is ${targetRole}. Show the relevant demand signals, required competencies, my missing prerequisites, relevant SkillSetu courses/training, and a practical learning path.`;

  onSetQuestion(contextualQuery);

  if (autoSend || recommendationContext) {
    onHandleSend(contextualQuery, recommendationContext);
  }
}

test('topic effect preserves explicit initialPrompt without overwriting or dispatching unwanted request', () => {
  let questionState = 'Explain how to use Docker in Pune';
  let dispatched = false;

  runTopicEffect({
    initialPrompt: 'Explain how to use Docker in Pune',
    initialTopic: 'Generative AI',
    recommendationContext: { topic: 'Generative AI', target_role: 'AI Engineer' },
    autoSend: true,
    onSetQuestion: (q) => { questionState = q; },
    onHandleSend: () => { dispatched = true; },
  });

  // initialPrompt must remain untouched and pending in the input state
  assert.equal(questionState, 'Explain how to use Docker in Pune');
  // No unwanted request should be dispatched
  assert.equal(dispatched, false);
});

test('topic effect populates contextualQuery and dispatches when initialPrompt is empty', () => {
  let questionState = '';
  let dispatched = false;
  let sentQuery = '';

  runTopicEffect({
    initialPrompt: '',
    initialTopic: 'Generative AI',
    recommendationContext: { topic: 'Generative AI', target_role: 'AI Engineer' },
    autoSend: true,
    onSetQuestion: (q) => { questionState = q; },
    onHandleSend: (q) => {
      dispatched = true;
      sentQuery = q;
    },
  });

  assert.match(questionState, /Explain why I should learn Generative AI/);
  assert.equal(dispatched, true);
  assert.match(sentQuery, /target role is AI Engineer/);
});
