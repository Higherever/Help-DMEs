const API_BASE = "http://localhost:8000";
export function useApi() {
  async function get(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
    return res.json();
  }
  async function post(path, body, isFormData = false) {
    const opts = { method: "POST" };
    if (isFormData) { opts.body = body; }
    else { opts.headers = {"Content-Type":"application/json"}; opts.body = JSON.stringify(body); }
    const res = await fetch(`${API_BASE}${path}`, opts);
    return res.json();
  }
  async function patch(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "PATCH", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body)
    });
    return res.json();
  }
  return { get, post, patch, API_BASE };
}
