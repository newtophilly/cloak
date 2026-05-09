// Tiny example API client — public function plus underscore-private helpers.
//
// Demonstrates how `cloak context` and `cloak obfuscate` treat JS files.

const _BASE_HEADERS = {
  "User-Agent": "example-client/1.0",
  "Accept": "application/json",
};

const _TIMEOUT_MS = 5000;

function _buildHeaders(token) {
  return {
    ..._BASE_HEADERS,
    Authorization: `Bearer ${token}`,
  };
}

function _normalizePath(path) {
  if (!path.startsWith("/")) return `/${path}`;
  return path;
}

export async function fetchJson(baseUrl, path, token) {
  const url = baseUrl + _normalizePath(path);
  const response = await fetch(url, {
    headers: _buildHeaders(token),
    signal: AbortSignal.timeout(_TIMEOUT_MS),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}
