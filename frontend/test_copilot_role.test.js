import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveEffectiveCopilotRole } from './src/utils/copilotRole.js';

test('resolveEffectiveCopilotRole enforces authenticated non-admin role when urlRole conflicts', () => {
  const role = resolveEffectiveCopilotRole({
    authRole: 'STUDENT',
    isAuthenticated: true,
    urlRole: 'employee',
    roleOverride: null,
  });
  assert.equal(role, 'student');
});

test('resolveEffectiveCopilotRole enforces employee role when urlRole is student', () => {
  const role = resolveEffectiveCopilotRole({
    authRole: 'EMPLOYEE',
    isAuthenticated: true,
    urlRole: 'student',
    roleOverride: null,
  });
  assert.equal(role, 'employee');
});

test('resolveEffectiveCopilotRole enforces authenticated role over roleOverride for non-admin', () => {
  const role = resolveEffectiveCopilotRole({
    authRole: 'EMPLOYER',
    isAuthenticated: true,
    urlRole: null,
    roleOverride: 'student',
  });
  assert.equal(role, 'employer');
});

test('resolveEffectiveCopilotRole allows urlRole for unauthenticated users', () => {
  const role = resolveEffectiveCopilotRole({
    authRole: null,
    isAuthenticated: false,
    urlRole: 'employee',
    roleOverride: null,
  });
  assert.equal(role, 'employee');
});

test('resolveEffectiveCopilotRole allows urlRole for admin users', () => {
  const role = resolveEffectiveCopilotRole({
    authRole: 'ADMIN',
    isAuthenticated: true,
    urlRole: 'employee',
    roleOverride: null,
  });
  assert.equal(role, 'employee');
});

test('resolveEffectiveCopilotRole defaults to admin for admin users without urlRole', () => {
  const role = resolveEffectiveCopilotRole({
    authRole: 'ADMIN',
    isAuthenticated: true,
    urlRole: null,
    roleOverride: null,
  });
  assert.equal(role, 'admin');
});

test('resolveEffectiveCopilotRole ignores invalid urlRole and defaults to student when unauthenticated', () => {
  const role = resolveEffectiveCopilotRole({
    authRole: null,
    isAuthenticated: false,
    urlRole: 'hacker_role',
    roleOverride: null,
  });
  assert.equal(role, 'student');
});
