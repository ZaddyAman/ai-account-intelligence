// API Client - Supports both development and production
// In production, set VITE_API_BASE to your Railway backend URL

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export async function fetchVisitors() {
  const res = await fetch(`${API_BASE}/visitors`);
  if (!res.ok) throw new Error('Failed to fetch visitors');
  return res.json();
}

export async function analyzeVisitor(visitor) {
  const res = await fetch(`${API_BASE}/analyze/visitor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(visitor),
  });
  if (!res.ok) throw new Error('Analysis failed');
  return res.json();
}

export async function analyzeCompany(companyName, domain = null) {
  const res = await fetch(`${API_BASE}/analyze/company`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company_name: companyName, domain }),
  });
  if (!res.ok) throw new Error('Analysis failed');
  return res.json();
}

export async function analyzeBatch(companies) {
  const res = await fetch(`${API_BASE}/analyze/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      companies: companies.map(c => ({
        company_name: c.trim(),
        domain: null,
      })),
    }),
  });
  if (!res.ok) throw new Error('Batch analysis failed');
  return res.json();
}

export async function fetchHistory(limit = 10) {
  const res = await fetch(`${API_BASE}/history?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch history');
  return res.json();
}

export async function clearHistory() {
  const res = await fetch(`${API_BASE}/history/clear`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to clear history');
  return res.json();
}
