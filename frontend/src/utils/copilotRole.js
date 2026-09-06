export function resolveEffectiveCopilotRole({ authRole, isAuthenticated, urlRole, roleOverride }) {
  const validRoles = ['government', 'institute', 'student', 'employer', 'admin', 'employee'];
  if (isAuthenticated && authRole) {
    const lowerAuth = authRole.toLowerCase();
    if (lowerAuth !== 'admin') {
      if (validRoles.includes(lowerAuth)) {
        return lowerAuth;
      }
      return 'student';
    }
  }
  if (urlRole && validRoles.includes(urlRole.toLowerCase())) {
    return urlRole.toLowerCase();
  }
  if (roleOverride && validRoles.includes(roleOverride.toLowerCase())) {
    return roleOverride.toLowerCase();
  }
  if (isAuthenticated && authRole && validRoles.includes(authRole.toLowerCase())) {
    return authRole.toLowerCase();
  }
  return 'student';
}
