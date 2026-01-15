// Dashboard templates for Cloudflare Worker

interface Template {
  name: string;
  description: string;
  category: string;
  tags: string[];
}

export const templates: Template[] = [
  { name: 'node-exporter', description: 'Linux server metrics (CPU, memory, disk, network)', category: 'infrastructure', tags: ['node-exporter', 'linux', 'server'] },
  { name: 'nginx', description: 'Nginx web server metrics', category: 'web-server', tags: ['nginx', 'web', 'http'] },
  { name: 'docker', description: 'Docker container metrics via cAdvisor', category: 'containers', tags: ['docker', 'containers'] },
  { name: 'kubernetes-cluster', description: 'Kubernetes cluster overview', category: 'kubernetes', tags: ['kubernetes', 'k8s'] },
  { name: 'mysql', description: 'MySQL/MariaDB with InnoDB metrics', category: 'database', tags: ['mysql', 'innodb', 'database'] },
  { name: 'postgresql', description: 'PostgreSQL database metrics', category: 'database', tags: ['postgresql', 'database'] },
  { name: 'redis', description: 'Redis cache metrics', category: 'database', tags: ['redis', 'cache'] },
  { name: 'http-endpoints', description: 'HTTP endpoint monitoring via Blackbox', category: 'web-server', tags: ['http', 'blackbox'] },
];

function generateUid(): string {
  return Math.random().toString(36).substring(2, 10);
}

function createPanel(id: number, title: string, query: string, type: string = 'timeseries', unit: string = 'short', width: number = 12, height: number = 8, x: number = 0, y: number = 0) {
  return {
    id,
    type,
    title,
    gridPos: { h: height, w: width, x, y },
    targets: [{ expr: query, refId: 'A' }],
    datasource: { type: 'prometheus', uid: '${datasource}' },
    fieldConfig: {
      defaults: { unit, thresholds: { mode: 'absolute', steps: [{ color: 'green', value: null }] } },
      overrides: [],
    },
    options: type === 'timeseries' ? { legend: { displayMode: 'list', placement: 'bottom' } } : {},
  };
}

export function createFromTemplate(name: string, datasource: string, variables: Record<string, string> = {}): any {
  const uid = generateUid();
  const instance = variables.instance || '$instance';
  const job = variables.job || '$job';

  const dashboardBase = {
    id: null,
    uid,
    title: '',
    tags: [],
    timezone: 'browser',
    schemaVersion: 39,
    time: { from: 'now-6h', to: 'now' },
    refresh: '30s',
    templating: {
      list: [
        {
          name: 'datasource',
          type: 'datasource',
          query: 'prometheus',
          current: { text: datasource, value: datasource },
        },
      ],
    },
    annotations: { list: [] },
    panels: [] as any[],
  };

  switch (name) {
    case 'node-exporter': {
      dashboardBase.title = 'Node Exporter Dashboard';
      dashboardBase.tags = ['node-exporter', 'infrastructure'];
      dashboardBase.templating.list.push({
        name: 'instance',
        type: 'query',
        query: 'label_values(node_uname_info, instance)',
        refresh: 1,
      } as any);

      dashboardBase.panels = [
        createPanel(1, 'CPU Usage', `100 - (avg(irate(node_cpu_seconds_total{mode="idle",instance=~"${instance}"}[5m])) * 100)`, 'gauge', 'percent', 6, 6, 0, 0),
        createPanel(2, 'Memory Usage', `100 * (1 - (node_memory_MemAvailable_bytes{instance=~"${instance}"} / node_memory_MemTotal_bytes{instance=~"${instance}"}))`, 'gauge', 'percent', 6, 6, 6, 0),
        createPanel(3, 'Disk Usage', `100 - ((node_filesystem_avail_bytes{instance=~"${instance}",fstype!="tmpfs"} / node_filesystem_size_bytes{instance=~"${instance}",fstype!="tmpfs"}) * 100)`, 'gauge', 'percent', 6, 6, 12, 0),
        createPanel(4, 'Uptime', `time() - node_boot_time_seconds{instance=~"${instance}"}`, 'stat', 's', 6, 6, 18, 0),
        createPanel(5, 'CPU by Mode', `sum by(mode) (irate(node_cpu_seconds_total{instance=~"${instance}"}[5m])) * 100`, 'timeseries', 'percent', 12, 8, 0, 6),
        createPanel(6, 'Load Average', `node_load1{instance=~"${instance}"}`, 'timeseries', 'short', 12, 8, 12, 6),
        createPanel(7, 'Memory', `node_memory_MemTotal_bytes{instance=~"${instance}"} - node_memory_MemAvailable_bytes{instance=~"${instance}"}`, 'timeseries', 'bytes', 12, 8, 0, 14),
        createPanel(8, 'Network Traffic', `rate(node_network_receive_bytes_total{instance=~"${instance}",device!~"lo|veth.*"}[5m]) * 8`, 'timeseries', 'bps', 12, 8, 12, 14),
      ];
      break;
    }

    case 'docker': {
      dashboardBase.title = 'Docker Containers Dashboard';
      dashboardBase.tags = ['docker', 'containers'];
      dashboardBase.templating.list.push({
        name: 'container',
        type: 'query',
        query: 'label_values(container_last_seen{name!=""}, name)',
        multi: true,
        includeAll: true,
        refresh: 1,
      } as any);

      const container = '$container';
      dashboardBase.panels = [
        createPanel(1, 'Running Containers', 'count(container_last_seen{name!=""})', 'stat', 'short', 6, 4, 0, 0),
        createPanel(2, 'Total CPU Usage', 'sum(rate(container_cpu_usage_seconds_total{name!=""}[5m])) * 100', 'stat', 'percent', 6, 4, 6, 0),
        createPanel(3, 'Total Memory', 'sum(container_memory_usage_bytes{name!=""})', 'stat', 'bytes', 6, 4, 12, 0),
        createPanel(4, 'Container CPU', `rate(container_cpu_usage_seconds_total{name=~"${container}"}[5m]) * 100`, 'timeseries', 'percent', 12, 8, 0, 4),
        createPanel(5, 'Container Memory', `container_memory_usage_bytes{name=~"${container}"}`, 'timeseries', 'bytes', 12, 8, 12, 4),
        createPanel(6, 'Network Receive', `rate(container_network_receive_bytes_total{name=~"${container}"}[5m])`, 'timeseries', 'Bps', 12, 8, 0, 12),
        createPanel(7, 'Network Transmit', `rate(container_network_transmit_bytes_total{name=~"${container}"}[5m])`, 'timeseries', 'Bps', 12, 8, 12, 12),
      ];
      break;
    }

    case 'mysql': {
      dashboardBase.title = 'MySQL / InnoDB Dashboard';
      dashboardBase.tags = ['mysql', 'innodb', 'database'];
      dashboardBase.templating.list.push({
        name: 'instance',
        type: 'query',
        query: 'label_values(mysql_up, instance)',
        refresh: 1,
      } as any);

      dashboardBase.panels = [
        createPanel(1, 'MySQL Up', `mysql_up{instance=~"${instance}"}`, 'stat', 'short', 4, 4, 0, 0),
        createPanel(2, 'Uptime', `mysql_global_status_uptime{instance=~"${instance}"}`, 'stat', 's', 4, 4, 4, 0),
        createPanel(3, 'Connections', `mysql_global_status_threads_connected{instance=~"${instance}"}`, 'stat', 'short', 4, 4, 8, 0),
        createPanel(4, 'Queries/sec', `rate(mysql_global_status_queries{instance=~"${instance}"}[5m])`, 'stat', 'ops', 4, 4, 12, 0),
        createPanel(5, 'Buffer Pool Size', `mysql_global_variables_innodb_buffer_pool_size{instance=~"${instance}"}`, 'stat', 'bytes', 4, 4, 16, 0),
        createPanel(6, 'Slow Queries', `rate(mysql_global_status_slow_queries{instance=~"${instance}"}[5m])`, 'stat', 'ops', 4, 4, 20, 0),
        createPanel(7, 'Query Types', `rate(mysql_global_status_com_select{instance=~"${instance}"}[5m])`, 'timeseries', 'ops', 12, 8, 0, 4),
        createPanel(8, 'InnoDB Buffer Pool', `mysql_global_status_innodb_buffer_pool_bytes_data{instance=~"${instance}"}`, 'timeseries', 'bytes', 12, 8, 12, 4),
        createPanel(9, 'InnoDB Row Operations', `rate(mysql_global_status_innodb_rows_read{instance=~"${instance}"}[5m])`, 'timeseries', 'ops', 12, 8, 0, 12),
        createPanel(10, 'InnoDB I/O', `rate(mysql_global_status_innodb_data_reads{instance=~"${instance}"}[5m])`, 'timeseries', 'ops', 12, 8, 12, 12),
      ];
      break;
    }

    case 'postgresql': {
      dashboardBase.title = 'PostgreSQL Dashboard';
      dashboardBase.tags = ['postgresql', 'database'];
      dashboardBase.templating.list.push({
        name: 'instance',
        type: 'query',
        query: 'label_values(pg_up, instance)',
        refresh: 1,
      } as any);

      dashboardBase.panels = [
        createPanel(1, 'PostgreSQL Up', `pg_up{instance=~"${instance}"}`, 'stat', 'short', 4, 4, 0, 0),
        createPanel(2, 'Active Connections', `sum(pg_stat_activity_count{instance=~"${instance}",state="active"})`, 'stat', 'short', 4, 4, 4, 0),
        createPanel(3, 'Database Size', `sum(pg_database_size_bytes{instance=~"${instance}"})`, 'stat', 'bytes', 4, 4, 8, 0),
        createPanel(4, 'Transactions/sec', `sum(rate(pg_stat_database_xact_commit{instance=~"${instance}"}[5m]))`, 'stat', 'ops', 4, 4, 12, 0),
        createPanel(5, 'Transactions', `rate(pg_stat_database_xact_commit{instance=~"${instance}"}[5m])`, 'timeseries', 'ops', 12, 8, 0, 4),
        createPanel(6, 'Tuple Operations', `rate(pg_stat_database_tup_fetched{instance=~"${instance}"}[5m])`, 'timeseries', 'ops', 12, 8, 12, 4),
      ];
      break;
    }

    case 'redis': {
      dashboardBase.title = 'Redis Dashboard';
      dashboardBase.tags = ['redis', 'cache'];
      dashboardBase.templating.list.push({
        name: 'instance',
        type: 'query',
        query: 'label_values(redis_up, instance)',
        refresh: 1,
      } as any);

      dashboardBase.panels = [
        createPanel(1, 'Redis Up', `redis_up{instance=~"${instance}"}`, 'stat', 'short', 4, 4, 0, 0),
        createPanel(2, 'Connected Clients', `redis_connected_clients{instance=~"${instance}"}`, 'stat', 'short', 4, 4, 4, 0),
        createPanel(3, 'Memory Used', `redis_memory_used_bytes{instance=~"${instance}"}`, 'stat', 'bytes', 4, 4, 8, 0),
        createPanel(4, 'Commands/sec', `rate(redis_commands_processed_total{instance=~"${instance}"}[5m])`, 'stat', 'ops', 4, 4, 12, 0),
        createPanel(5, 'Memory Usage', `redis_memory_used_bytes{instance=~"${instance}"}`, 'timeseries', 'bytes', 12, 8, 0, 4),
        createPanel(6, 'Hit Rate', `rate(redis_keyspace_hits_total{instance=~"${instance}"}[5m])`, 'timeseries', 'ops', 12, 8, 12, 4),
      ];
      break;
    }

    case 'nginx': {
      dashboardBase.title = 'Nginx Dashboard';
      dashboardBase.tags = ['nginx', 'web-server'];
      dashboardBase.templating.list.push({
        name: 'instance',
        type: 'query',
        query: 'label_values(nginx_up, instance)',
        refresh: 1,
      } as any);

      dashboardBase.panels = [
        createPanel(1, 'Nginx Up', `nginx_up{instance=~"${instance}"}`, 'stat', 'short', 4, 4, 0, 0),
        createPanel(2, 'Active Connections', `nginx_connections_active{instance=~"${instance}"}`, 'stat', 'short', 4, 4, 4, 0),
        createPanel(3, 'Requests/sec', `rate(nginx_http_requests_total{instance=~"${instance}"}[5m])`, 'stat', 'reqps', 4, 4, 8, 0),
        createPanel(4, 'Connections', `nginx_connections_active{instance=~"${instance}"}`, 'timeseries', 'short', 12, 8, 0, 4),
        createPanel(5, 'Request Rate', `rate(nginx_http_requests_total{instance=~"${instance}"}[5m])`, 'timeseries', 'reqps', 12, 8, 12, 4),
      ];
      break;
    }

    case 'kubernetes-cluster': {
      dashboardBase.title = 'Kubernetes Cluster Overview';
      dashboardBase.tags = ['kubernetes', 'cluster'];

      dashboardBase.panels = [
        createPanel(1, 'Nodes', 'sum(kube_node_info)', 'stat', 'short', 4, 4, 0, 0),
        createPanel(2, 'Running Pods', 'sum(kube_pod_status_phase{phase="Running"})', 'stat', 'short', 4, 4, 4, 0),
        createPanel(3, 'Deployments', 'count(kube_deployment_created)', 'stat', 'short', 4, 4, 8, 0),
        createPanel(4, 'CPU Requests %', 'sum(kube_pod_container_resource_requests{resource="cpu"}) / sum(kube_node_status_allocatable{resource="cpu"}) * 100', 'gauge', 'percent', 4, 4, 12, 0),
        createPanel(5, 'Pod Status', 'sum by(phase) (kube_pod_status_phase)', 'timeseries', 'short', 12, 8, 0, 4),
        createPanel(6, 'Node CPU', '100 - (avg by(node) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)', 'timeseries', 'percent', 12, 8, 12, 4),
      ];
      break;
    }

    case 'http-endpoints': {
      dashboardBase.title = 'HTTP Endpoints Dashboard';
      dashboardBase.tags = ['http', 'blackbox'];

      dashboardBase.panels = [
        createPanel(1, 'Endpoint Status', 'probe_success', 'stat', 'short', 6, 4, 0, 0),
        createPanel(2, 'HTTP Duration', 'probe_http_duration_seconds', 'stat', 's', 6, 4, 6, 0),
        createPanel(3, 'SSL Expiry', 'probe_ssl_earliest_cert_expiry - time()', 'stat', 's', 6, 4, 12, 0),
        createPanel(4, 'Response Time', 'probe_http_duration_seconds', 'timeseries', 's', 24, 8, 0, 4),
      ];
      break;
    }

    default:
      return null;
  }

  return dashboardBase;
}
