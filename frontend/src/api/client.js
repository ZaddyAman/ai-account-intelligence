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

export async function analyzeVisitorStream(visitor, onProgress) {
  // Use streaming endpoint for real-time progress
  const response = await fetch(`${API_BASE}/analyze/visitor/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(visitor),
  });

  if (!response.ok) throw new Error('Analysis failed');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          if (onProgress) onProgress(data);

          if (data.step === 'DONE' && data.result) {
            return data.result;
          }
        } catch (e) {
          // Skip invalid JSON
        }
      }
    }
  }

  throw new Error('Stream ended without result');
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

// Streaming version with progress callback
export async function analyzeCompanyStream(companyName, domain = null, onProgress) {
  const query = domain ? `${companyName},${domain}` : companyName;
  const response = await fetch(`${API_BASE}/analyze/stream?q=${encodeURIComponent(query)}`);

  if (!response.ok) throw new Error('Analysis failed');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          if (onProgress) onProgress(data);

          if (data.step === 'DONE' && data.result) {
            return data.result;
          }
        } catch (e) {
          // Skip invalid JSON
        }
      }
    }
  }

  throw new Error('Stream ended without result');
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
