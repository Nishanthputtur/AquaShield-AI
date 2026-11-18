/**
 * Local storage helpers for AquaShield AI authentication token and user session.
 */

export function saveToken(token) {
  localStorage.setItem('aq_token', token);
}

export function getToken() {
  return localStorage.getItem('aq_token');
}

export function clearToken() {
  localStorage.removeItem('aq_token');
}

export function saveUser(user) {
  localStorage.setItem('aq_user', JSON.stringify(user));
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem('aq_user') || 'null');
  } catch {
    return null;
  }
}

export function clearUser() {
  localStorage.removeItem('aq_user');
}
