import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { serveStatic } from 'hono/cloudflare-workers';
import { templates, createFromTemplate } from './templates';
import { generateFromPrompt } from './nlp';

type Bindings = {
  DB: D1Database;
  OPENAI_API_KEY?: string;
  OPENROUTER_API_KEY?: string;
  OPENROUTER_MODEL?: string;
  ANTHROPIC_API_KEY?: string;
  ANTHROPIC_MODEL?: string;
};

const app = new Hono<{ Bindings: Bindings }>();

// Middleware
app.use('*', cors());

// Health check
app.get('/api/health', (c) => c.json({ status: 'ok', version: '0.1.0' }));

// Stats
app.get('/api/stats', async (c) => {
  const db = c.env.DB;
  const dashboards = await db.prepare('SELECT COUNT(*) as c FROM dashboards').first<{ c: number }>();
  const datasources = await db.prepare('SELECT COUNT(*) as c FROM datasources').first<{ c: number }>();
  const history = await db.prepare('SELECT COUNT(*) as c FROM dashboard_history').first<{ c: number }>();

  return c.json({
    dashboards: dashboards?.c || 0,
    datasources: datasources?.c || 0,
    history_entries: history?.c || 0,
  });
});

// Dashboard endpoints
app.get('/api/dashboards', async (c) => {
  const db = c.env.DB;
  const search = c.req.query('search');
  const limit = parseInt(c.req.query('limit') || '100');
  const offset = parseInt(c.req.query('offset') || '0');

  let query = 'SELECT id, uid, title, description, tags, template_name, created_at, updated_at FROM dashboards WHERE 1=1';
  const params: any[] = [];

  if (search) {
    query += ' AND (title LIKE ? OR description LIKE ?)';
    params.push(`%${search}%`, `%${search}%`);
  }

  query += ' ORDER BY updated_at DESC LIMIT ? OFFSET ?';
  params.push(limit, offset);

  const results = await db.prepare(query).bind(...params).all();

  return c.json({
    dashboards: results.results.map((row: any) => ({
      ...row,
      tags: JSON.parse(row.tags || '[]'),
    })),
  });
});

app.post('/api/dashboards', async (c) => {
  const db = c.env.DB;
  const body = await c.req.json();
  const source = body.source || 'sdk';

  let dashboard: any;

  if (source === 'template') {
    dashboard = createFromTemplate(body.template, body.datasource || 'Prometheus', body.variables || {});
    if (body.title) dashboard.title = body.title;
  } else if (source === 'nlp') {
    dashboard = await generateFromPrompt(
      body.prompt,
      body.datasource || 'Prometheus',
      c.env.OPENAI_API_KEY,
      c.env.OPENROUTER_API_KEY,
      c.env.OPENROUTER_MODEL,
      c.env.ANTHROPIC_API_KEY,
      c.env.ANTHROPIC_MODEL
    );
  } else {
    dashboard = createBasicDashboard(body);
  }

  const uid = dashboard.uid || generateUid();

  await db.prepare(`
    INSERT INTO dashboards (uid, title, description, tags, json_data, template_name)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(uid) DO UPDATE SET
      title = excluded.title,
      description = excluded.description,
      tags = excluded.tags,
      json_data = excluded.json_data,
      updated_at = datetime('now')
  `).bind(
    uid,
    dashboard.title || 'Untitled',
    dashboard.description || '',
    JSON.stringify(dashboard.tags || []),
    JSON.stringify(dashboard),
    body.template || null
  ).run();

  return c.json({ uid, title: dashboard.title, json: dashboard });
});

app.get('/api/dashboards/:uid', async (c) => {
  const db = c.env.DB;
  const uid = c.req.param('uid');

  const row = await db.prepare('SELECT * FROM dashboards WHERE uid = ?').bind(uid).first();
  if (!row) return c.json({ error: 'Dashboard not found' }, 404);

  return c.json({
    ...(row as any),
    tags: JSON.parse((row as any).tags || '[]'),
    json_data: JSON.parse((row as any).json_data),
  });
});

app.delete('/api/dashboards/:uid', async (c) => {
  const db = c.env.DB;
  const uid = c.req.param('uid');

  const result = await db.prepare('DELETE FROM dashboards WHERE uid = ?').bind(uid).run();
  if (result.meta.changes === 0) return c.json({ error: 'Dashboard not found' }, 404);

  return c.json({ status: 'deleted' });
});

app.get('/api/dashboards/:uid/export', async (c) => {
  const db = c.env.DB;
  const uid = c.req.param('uid');

  const row = await db.prepare('SELECT json_data FROM dashboards WHERE uid = ?').bind(uid).first();
  if (!row) return c.json({ error: 'Dashboard not found' }, 404);

  return c.json(JSON.parse((row as any).json_data));
});

// Templates
app.get('/api/templates', (c) => {
  return c.json({ templates });
});

app.get('/api/templates/:name', (c) => {
  const name = c.req.param('name');
  const template = templates.find((t) => t.name === name);
  if (!template) return c.json({ error: 'Template not found' }, 404);
  return c.json(template);
});

app.post('/api/templates/:name/preview', async (c) => {
  const name = c.req.param('name');
  const body = await c.req.json();
  const datasource = body.datasource || 'Prometheus';

  const dashboard = createFromTemplate(name, datasource, body.variables || {});
  if (!dashboard) return c.json({ error: 'Template not found' }, 404);

  return c.json({
    title: dashboard.title,
    panels: dashboard.panels?.length || 0,
    json: dashboard,
  });
});

// NLP generation
app.post('/api/generate', async (c) => {
  const body = await c.req.json();
  if (!body.prompt) return c.json({ error: 'prompt is required' }, 400);

  const dashboard = await generateFromPrompt(
    body.prompt,
    body.datasource || 'Prometheus',
    c.env.OPENAI_API_KEY,
    c.env.OPENROUTER_API_KEY,
    c.env.OPENROUTER_MODEL,
    c.env.ANTHROPIC_API_KEY,
    c.env.ANTHROPIC_MODEL
  );

  return c.json({
    title: dashboard.title,
    panels: dashboard.panels?.length || 0,
    json: dashboard,
  });
});

// Datasources
app.get('/api/datasources', async (c) => {
  const db = c.env.DB;
  const results = await db.prepare('SELECT * FROM datasources ORDER BY is_default DESC, name').all();
  return c.json({ datasources: results.results });
});

app.post('/api/datasources', async (c) => {
  const db = c.env.DB;
  const body = await c.req.json();

  await db.prepare(`
    INSERT INTO datasources (name, type, uid, is_default)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(name) DO UPDATE SET type = excluded.type, uid = excluded.uid, is_default = excluded.is_default
  `).bind(body.name, body.type || 'prometheus', body.uid || null, body.is_default ? 1 : 0).run();

  return c.json({ status: 'created', name: body.name });
});

// Serve static files
app.get('/*', serveStatic({ root: './' }));
app.get('/', serveStatic({ path: './index.html' }));

// Helper functions
function generateUid(): string {
  return Math.random().toString(36).substring(2, 10);
}

function createBasicDashboard(body: any): any {
  const uid = generateUid();
  const panels = (body.panels || []).map((p: any, i: number) => ({
    id: i + 1,
    type: p.type || 'timeseries',
    title: p.title || 'Panel',
    gridPos: { h: 8, w: 12, x: (i % 2) * 12, y: Math.floor(i / 2) * 8 },
    targets: p.query ? [{ expr: p.query, refId: 'A' }] : [],
    fieldConfig: { defaults: { unit: p.unit || 'short' }, overrides: [] },
    options: {},
  }));

  return {
    id: null,
    uid,
    title: body.title || 'Untitled',
    description: body.description || '',
    tags: body.tags || [],
    timezone: 'browser',
    schemaVersion: 39,
    panels,
    time: { from: 'now-6h', to: 'now' },
    templating: { list: [] },
    annotations: { list: [] },
  };
}

export default app;
