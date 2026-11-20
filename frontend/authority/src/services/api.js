/**
 * API client service for AquaShield AI.
 * All requests use relative URLs starting with /api (proxied by Vite).
 */

async function request(method, path, body = null, token = null) {
  const headers = {};

  if (body) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const options = {
    method,
    headers,
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(path, options);

  if (!response.ok) {
    let errorData = null;
    try {
      errorData = await response.json();
    } catch {
      // response body was not JSON
    }

    if (response.status === 401) {
      throw { status: 401, message: 'Session expired' };
    }
    if (response.status === 403) {
      throw { status: 403, message: 'Forbidden' };
    }
    if (response.status === 404) {
      throw { status: 404, message: 'Not found' };
    }
    if (response.status === 422) {
      throw {
        status: 422,
        message: 'Validation error',
        detail: errorData?.detail || 'Validation error',
      };
    }

    throw {
      status: response.status,
      message: errorData?.detail || `Request failed with status ${response.status}`,
    };
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  return await response.json();
}

export const api = {
  login: (email, password) =>
    request('POST', '/api/v1/auth/login', { email, password }),

  getMe: (token) =>
    request('GET', '/api/v1/auth/me', null, token),

  getUsers: (token) =>
    request('GET', '/api/v1/users', null, token),

  createUser: (token, data) =>
    request('POST', '/api/v1/users', data, token),

  updateUser: (token, id, data) =>
    request('PATCH', `/api/v1/users/${id}`, data, token),

  startSimulation: (token) =>
    request('POST', '/api/v1/simulation/start', null, token),

  pauseSimulation: (token) =>
    request('POST', '/api/v1/simulation/pause', null, token),

  resumeSimulation: (token) =>
    request('POST', '/api/v1/simulation/resume', null, token),

  stopSimulation: (token) =>
    request('POST', '/api/v1/simulation/stop', null, token),

  resetSimulation: (token) =>
    request('POST', '/api/v1/simulation/reset', null, token),

  getSimulationState: (token) =>
    request('GET', '/api/v1/simulation/state', null, token),

  getReadings: (token, limit = 100) =>
    request('GET', `/api/v1/monitoring/readings?limit=${limit}`, null, token),

  getAsset: (token, assetId) =>
    request('GET', `/api/v1/assets/${encodeURIComponent(assetId)}`, null, token),

  createInspection: (token, data) =>
    request('POST', '/api/v1/inspections', data, token),

  getInspections: (token) =>
    request('GET', '/api/v1/inspections', null, token),

  createMaintenance: (token, data) =>
    request('POST', '/api/v1/maintenance', data, token),

  getMaintenance: (token) =>
    request('GET', '/api/v1/maintenance', null, token),
};

export default api;
