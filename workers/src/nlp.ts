// Natural language dashboard generation for Cloudflare Worker
// Supports OpenAI and OpenRouter APIs

const METRIC_PATTERNS: Record<string, { title: string; query: string; unit: string; type: string }> = {
  cpu: { title: 'CPU Usage', query: '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)', unit: 'percent', type: 'timeseries' },
  memory: { title: 'Memory Usage', query: '100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))', unit: 'percent', type: 'timeseries' },
  disk: { title: 'Disk Usage', query: '100 - ((node_filesystem_avail_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes) * 100)', unit: 'percent', type: 'timeseries' },
  network: { title: 'Network Traffic', query: 'rate(node_network_receive_bytes_total{device!~"lo|veth.*"}[5m]) * 8', unit: 'bps', type: 'timeseries' },
  http: { title: 'HTTP Requests', query: 'rate(http_requests_total[5m])', unit: 'reqps', type: 'timeseries' },
  latency: { title: 'Request Latency', query: 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))', unit: 's', type: 'timeseries' },
  error: { title: 'Error Rate', query: 'rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100', unit: 'percent', type: 'timeseries' },
  container: { title: 'Container CPU', query: 'rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100', unit: 'percent', type: 'timeseries' },
  database: { title: 'Database Queries', query: 'rate(pg_stat_database_xact_commit[5m])', unit: 'ops', type: 'timeseries' },
  redis: { title: 'Redis Commands', query: 'rate(redis_commands_processed_total[5m])', unit: 'ops', type: 'timeseries' },
};

function generateUid(): string {
  return Math.random().toString(36).substring(2, 10);
}

function createPanel(id: number, title: string, query: string, type: string, unit: string, x: number, y: number) {
  return {
    id,
    type,
    title,
    gridPos: { h: 8, w: 12, x, y },
    targets: [{ expr: query, refId: 'A' }],
    fieldConfig: { defaults: { unit }, overrides: [] },
    options: {},
  };
}

async function generateWithLLM(prompt: string, apiKey: string, useOpenRouter: boolean, modelName?: string): Promise<any> {
  const systemPrompt = `You are a Grafana dashboard generator. Given a natural language description,
output a JSON object with the following structure:
{
  "title": "Dashboard Title",
  "panels": [
    {
      "title": "Panel Title",
      "query": "PromQL query",
      "type": "timeseries|stat|gauge|table",
      "unit": "percent|bytes|s|ops|reqps|short"
    }
  ]
}

Use appropriate PromQL queries for Prometheus. Common metrics:
- CPU: node_cpu_seconds_total, container_cpu_usage_seconds_total
- Memory: node_memory_MemAvailable_bytes, container_memory_usage_bytes
- HTTP: http_requests_total, http_request_duration_seconds_bucket
- Database: pg_stat_database_xact_commit, mysql_global_status_queries

Only output valid JSON, no explanations.`;

  const baseUrl = useOpenRouter ? 'https://openrouter.ai/api/v1' : 'https://api.openai.com/v1';
  const model = useOpenRouter ? (modelName || 'openai/gpt-4o-mini') : 'gpt-4o-mini';

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${apiKey}`,
  };

  if (useOpenRouter) {
    headers['HTTP-Referer'] = 'https://grafana-toolkit.workers.dev';
    headers['X-Title'] = 'Grafana Dashboard Toolkit';
  }

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: prompt },
      ],
      temperature: 0.3,
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json() as any;
  const content = data.choices?.[0]?.message?.content || '';

  // Extract JSON from response
  const jsonMatch = content.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    return JSON.parse(jsonMatch[0]);
  }

  throw new Error('No JSON found in response');
}

function generateWithPatterns(prompt: string): any {
  const promptLower = prompt.toLowerCase();
  const panels: any[] = [];
  let panelId = 1;
  let y = 0;

  // Extract title
  const titleMatch = promptLower.match(/(?:create|make|build)?\s*(?:a|an)?\s*dashboard\s+(?:for\s+)?(.+?)(?:\s+showing|\s+with|\s+that|$)/);
  const title = titleMatch ? titleMatch[1].trim().replace(/\b\w/g, (c) => c.toUpperCase()) + ' Dashboard' : 'Generated Dashboard';

  // Find matching patterns
  for (const [keyword, config] of Object.entries(METRIC_PATTERNS)) {
    if (promptLower.includes(keyword)) {
      panels.push(createPanel(panelId, config.title, config.query, config.type, config.unit, (panelId - 1) % 2 * 12, y));
      if (panelId % 2 === 0) y += 8;
      panelId++;
    }
  }

  // Fallback if no patterns matched
  if (panels.length === 0) {
    if (promptLower.includes('server') || promptLower.includes('node')) {
      panels.push(createPanel(1, 'CPU Usage', METRIC_PATTERNS.cpu.query, 'gauge', 'percent', 0, 0));
      panels.push(createPanel(2, 'Memory Usage', METRIC_PATTERNS.memory.query, 'gauge', 'percent', 12, 0));
      panels.push(createPanel(3, 'Disk Usage', METRIC_PATTERNS.disk.query, 'timeseries', 'percent', 0, 8));
    } else if (promptLower.includes('web') || promptLower.includes('api')) {
      panels.push(createPanel(1, 'HTTP Requests', METRIC_PATTERNS.http.query, 'timeseries', 'reqps', 0, 0));
      panels.push(createPanel(2, 'Latency', METRIC_PATTERNS.latency.query, 'timeseries', 's', 12, 0));
      panels.push(createPanel(3, 'Error Rate', METRIC_PATTERNS.error.query, 'timeseries', 'percent', 0, 8));
    } else {
      panels.push(createPanel(1, 'System Overview', 'up', 'stat', 'short', 0, 0));
    }
  }

  return { title, panels };
}

export async function generateFromPrompt(
  prompt: string,
  datasource: string,
  openaiKey?: string,
  openrouterKey?: string,
  openrouterModel?: string
): Promise<any> {
  let spec: { title: string; panels: any[] };

  // Try OpenRouter first if key is provided
  if (openrouterKey) {
    try {
      spec = await generateWithLLM(prompt, openrouterKey, true, openrouterModel);
    } catch {
      spec = generateWithPatterns(prompt);
    }
  } else if (openaiKey) {
    try {
      spec = await generateWithLLM(prompt, openaiKey, false);
    } catch {
      spec = generateWithPatterns(prompt);
    }
  } else {
    spec = generateWithPatterns(prompt);
  }

  // Build dashboard
  const uid = generateUid();
  const panels = spec.panels.map((p: any, i: number) => ({
    id: i + 1,
    type: p.type || 'timeseries',
    title: p.title || 'Panel',
    gridPos: { h: 8, w: 12, x: (i % 2) * 12, y: Math.floor(i / 2) * 8 },
    targets: [{ expr: p.query, refId: 'A' }],
    datasource: { type: 'prometheus', uid: datasource },
    fieldConfig: { defaults: { unit: p.unit || 'short' }, overrides: [] },
    options: {},
  }));

  return {
    id: null,
    uid,
    title: spec.title,
    tags: [],
    timezone: 'browser',
    schemaVersion: 39,
    panels,
    time: { from: 'now-6h', to: 'now' },
    refresh: '30s',
    templating: { list: [] },
    annotations: { list: [] },
  };
}
