export async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: options.body instanceof FormData ? {} : {'Content-Type': 'application/json'},
    body: options.body instanceof FormData ? options.body : options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : 'Dados inválidos. Verifique os campos.');
  }
  return response.status === 204 ? null : response.json();
}
export const fileURL = (id, path) => `/projects/${id}/file?path=${encodeURIComponent(path)}`;
