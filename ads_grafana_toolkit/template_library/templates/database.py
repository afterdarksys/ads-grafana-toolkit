"""Database dashboard templates for MySQL, PostgreSQL, and more."""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class MySQLTemplate(DashboardTemplate):
    """Dashboard template for MySQL/MariaDB metrics including InnoDB."""

    def __init__(self):
        super().__init__(
            name="mysql",
            description="MySQL/MariaDB monitoring with InnoDB metrics",
            category="database",
            tags=["mysql", "mariadb", "innodb", "database"],
            variables=[
                TemplateVariable(
                    name="instance",
                    description="MySQL instance",
                    default="localhost:9104",
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        instance = kwargs.get("instance", "$instance")
        job = kwargs.get("job", "mysql")

        dashboard = Dashboard(
            title=kwargs.get("title", "MySQL / InnoDB Dashboard"),
            description="MySQL and InnoDB metrics via mysqld_exporter",
            tags=["mysql", "innodb", "database"],
            datasource=ds,
            refresh="30s",
        )

        dashboard.add_variable(
            "instance",
            query=f'label_values(mysql_up, instance)',
            label="Instance",
        )

        # Overview Row
        dashboard.add_row("Overview")

        dashboard.add_panel(
            "MySQL Up",
            query=f'mysql_up{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        ).add_threshold(None, "red").add_threshold(1, "green")

        dashboard.add_panel(
            "Uptime",
            query=f'mysql_global_status_uptime{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
            unit="s",
        )

        dashboard.add_panel(
            "Current Connections",
            query=f'mysql_global_status_threads_connected{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Queries/sec",
            query=f'rate(mysql_global_status_queries{{instance=~"{instance}"}}[5m])',
            panel_type="stat",
            width=4,
            height=4,
            unit="qps",
        )

        dashboard.add_panel(
            "Slow Queries",
            query=f'rate(mysql_global_status_slow_queries{{instance=~"{instance}"}}[5m])',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Aborted Connections",
            query=f'rate(mysql_global_status_aborted_connects{{instance=~"{instance}"}}[5m])',
            panel_type="stat",
            width=4,
            height=4,
        )

        # Connections Row
        dashboard.add_row("Connections")

        dashboard.add_panel(
            "Connection Usage",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            f'mysql_global_status_threads_connected{{instance=~"{instance}"}}',
            legend="Connected"
        ).add_query(
            f'mysql_global_status_threads_running{{instance=~"{instance}"}}',
            legend="Running"
        ).add_query(
            f'mysql_global_variables_max_connections{{instance=~"{instance}"}}',
            legend="Max Connections"
        )

        dashboard.add_panel(
            "Connection Errors",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            f'rate(mysql_global_status_aborted_clients{{instance=~"{instance}"}}[5m])',
            legend="Aborted Clients"
        ).add_query(
            f'rate(mysql_global_status_aborted_connects{{instance=~"{instance}"}}[5m])',
            legend="Aborted Connects"
        )

        # Query Performance Row
        dashboard.add_row("Query Performance")

        dashboard.add_panel(
            "Query Rate",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="ops",
        ).add_query(
            f'rate(mysql_global_status_questions{{instance=~"{instance}"}}[5m])',
            legend="Questions"
        ).add_query(
            f'rate(mysql_global_status_queries{{instance=~"{instance}"}}[5m])',
            legend="Queries"
        )

        dashboard.add_panel(
            "Query Types",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="ops",
        ).add_query(
            f'rate(mysql_global_status_com_select{{instance=~"{instance}"}}[5m])',
            legend="SELECT"
        ).add_query(
            f'rate(mysql_global_status_com_insert{{instance=~"{instance}"}}[5m])',
            legend="INSERT"
        ).add_query(
            f'rate(mysql_global_status_com_update{{instance=~"{instance}"}}[5m])',
            legend="UPDATE"
        ).add_query(
            f'rate(mysql_global_status_com_delete{{instance=~"{instance}"}}[5m])',
            legend="DELETE"
        )

        # InnoDB Row
        dashboard.add_row("InnoDB")

        dashboard.add_panel(
            "InnoDB Buffer Pool Size",
            query=f'mysql_global_variables_innodb_buffer_pool_size{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
            unit="bytes",
        )

        dashboard.add_panel(
            "Buffer Pool Hit Rate",
            query=f'1 - (rate(mysql_global_status_innodb_buffer_pool_reads{{instance=~"{instance}"}}[5m]) / rate(mysql_global_status_innodb_buffer_pool_read_requests{{instance=~"{instance}"}}[5m]))',
            panel_type="gauge",
            width=4,
            height=4,
            unit="percentunit",
        ).add_threshold(None, "red").add_threshold(0.9, "yellow").add_threshold(0.99, "green")

        dashboard.add_panel(
            "InnoDB Row Lock Waits",
            query=f'rate(mysql_global_status_innodb_row_lock_waits{{instance=~"{instance}"}}[5m])',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Buffer Pool Usage",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bytes",
        ).add_query(
            f'mysql_global_status_innodb_buffer_pool_bytes_data{{instance=~"{instance}"}}',
            legend="Data"
        ).add_query(
            f'mysql_global_status_innodb_buffer_pool_bytes_dirty{{instance=~"{instance}"}}',
            legend="Dirty"
        ).add_query(
            f'mysql_global_variables_innodb_buffer_pool_size{{instance=~"{instance}"}}',
            legend="Total Size"
        )

        dashboard.add_panel(
            "InnoDB I/O",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="ops",
        ).add_query(
            f'rate(mysql_global_status_innodb_data_reads{{instance=~"{instance}"}}[5m])',
            legend="Reads"
        ).add_query(
            f'rate(mysql_global_status_innodb_data_writes{{instance=~"{instance}"}}[5m])',
            legend="Writes"
        ).add_query(
            f'rate(mysql_global_status_innodb_data_fsyncs{{instance=~"{instance}"}}[5m])',
            legend="Fsyncs"
        )

        # InnoDB Transactions Row
        dashboard.add_row("InnoDB Transactions & Locking")

        dashboard.add_panel(
            "InnoDB Row Operations",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="ops",
        ).add_query(
            f'rate(mysql_global_status_innodb_rows_read{{instance=~"{instance}"}}[5m])',
            legend="Rows Read"
        ).add_query(
            f'rate(mysql_global_status_innodb_rows_inserted{{instance=~"{instance}"}}[5m])',
            legend="Rows Inserted"
        ).add_query(
            f'rate(mysql_global_status_innodb_rows_updated{{instance=~"{instance}"}}[5m])',
            legend="Rows Updated"
        ).add_query(
            f'rate(mysql_global_status_innodb_rows_deleted{{instance=~"{instance}"}}[5m])',
            legend="Rows Deleted"
        )

        dashboard.add_panel(
            "InnoDB Locking",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            f'rate(mysql_global_status_innodb_row_lock_waits{{instance=~"{instance}"}}[5m])',
            legend="Row Lock Waits"
        ).add_query(
            f'mysql_global_status_innodb_row_lock_current_waits{{instance=~"{instance}"}}',
            legend="Current Waits"
        ).add_query(
            f'rate(mysql_global_status_innodb_row_lock_time{{instance=~"{instance}"}}[5m])',
            legend="Lock Time"
        )

        # InnoDB Log Row
        dashboard.add_row("InnoDB Redo Log")

        dashboard.add_panel(
            "Redo Log Writes",
            query=f'rate(mysql_global_status_innodb_log_writes{{instance=~"{instance}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="ops",
        )

        dashboard.add_panel(
            "Redo Log Bytes Written",
            query=f'rate(mysql_global_status_innodb_log_write_requests{{instance=~"{instance}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
        )

        # Replication Row (if applicable)
        dashboard.add_row("Replication")

        dashboard.add_panel(
            "Slave IO Running",
            query=f'mysql_slave_status_slave_io_running{{instance=~"{instance}"}}',
            panel_type="stat",
            width=6,
            height=4,
        ).add_threshold(None, "red").add_threshold(1, "green")

        dashboard.add_panel(
            "Slave SQL Running",
            query=f'mysql_slave_status_slave_sql_running{{instance=~"{instance}"}}',
            panel_type="stat",
            width=6,
            height=4,
        ).add_threshold(None, "red").add_threshold(1, "green")

        dashboard.add_panel(
            "Seconds Behind Master",
            query=f'mysql_slave_status_seconds_behind_master{{instance=~"{instance}"}}',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="s",
        )

        return dashboard


class PostgreSQLTemplate(DashboardTemplate):
    """Dashboard template for PostgreSQL metrics."""

    def __init__(self):
        super().__init__(
            name="postgresql",
            description="PostgreSQL monitoring (connections, queries, locks, replication)",
            category="database",
            tags=["postgresql", "postgres", "database"],
            variables=[
                TemplateVariable(
                    name="instance",
                    description="PostgreSQL instance",
                    default="localhost:9187",
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        instance = kwargs.get("instance", "$instance")

        dashboard = Dashboard(
            title=kwargs.get("title", "PostgreSQL Dashboard"),
            description="PostgreSQL metrics via postgres_exporter",
            tags=["postgresql", "database"],
            datasource=ds,
            refresh="30s",
        )

        dashboard.add_variable(
            "instance",
            query='label_values(pg_up, instance)',
            label="Instance",
        )

        dashboard.add_variable(
            "datname",
            query=f'label_values(pg_stat_database_tup_fetched{{instance=~"{instance}"}}, datname)',
            label="Database",
            multi=True,
            include_all=True,
        )

        # Overview
        dashboard.add_row("Overview")

        dashboard.add_panel(
            "PostgreSQL Up",
            query=f'pg_up{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        ).add_threshold(None, "red").add_threshold(1, "green")

        dashboard.add_panel(
            "Active Connections",
            query=f'sum(pg_stat_activity_count{{instance=~"{instance}",state="active"}})',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Idle Connections",
            query=f'sum(pg_stat_activity_count{{instance=~"{instance}",state="idle"}})',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Database Size",
            query=f'sum(pg_database_size_bytes{{instance=~"{instance}",datname=~"$datname"}})',
            panel_type="stat",
            width=4,
            height=4,
            unit="bytes",
        )

        dashboard.add_panel(
            "Transactions/sec",
            query=f'sum(rate(pg_stat_database_xact_commit{{instance=~"{instance}",datname=~"$datname"}}[5m]))',
            panel_type="stat",
            width=4,
            height=4,
            unit="tps",
        )

        dashboard.add_panel(
            "Cache Hit Ratio",
            query=f'sum(pg_stat_database_blks_hit{{instance=~"{instance}",datname=~"$datname"}}) / (sum(pg_stat_database_blks_hit{{instance=~"{instance}",datname=~"$datname"}}) + sum(pg_stat_database_blks_read{{instance=~"{instance}",datname=~"$datname"}}))',
            panel_type="gauge",
            width=4,
            height=4,
            unit="percentunit",
        ).add_threshold(None, "red").add_threshold(0.9, "yellow").add_threshold(0.99, "green")

        # Connections
        dashboard.add_row("Connections")

        dashboard.add_panel(
            "Connection States",
            query=f'pg_stat_activity_count{{instance=~"{instance}"}}',
            panel_type="timeseries",
            width=12,
            height=8,
        )

        dashboard.add_panel(
            "Connection Usage",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            f'sum(pg_stat_activity_count{{instance=~"{instance}"}})',
            legend="Current"
        ).add_query(
            f'pg_settings_max_connections{{instance=~"{instance}"}}',
            legend="Max"
        )

        # Queries
        dashboard.add_row("Queries")

        dashboard.add_panel(
            "Transactions",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="ops",
        ).add_query(
            f'rate(pg_stat_database_xact_commit{{instance=~"{instance}",datname=~"$datname"}}[5m])',
            legend="Commits {{datname}}"
        ).add_query(
            f'rate(pg_stat_database_xact_rollback{{instance=~"{instance}",datname=~"$datname"}}[5m])',
            legend="Rollbacks {{datname}}"
        )

        dashboard.add_panel(
            "Tuple Operations",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="ops",
        ).add_query(
            f'rate(pg_stat_database_tup_fetched{{instance=~"{instance}",datname=~"$datname"}}[5m])',
            legend="Fetched"
        ).add_query(
            f'rate(pg_stat_database_tup_inserted{{instance=~"{instance}",datname=~"$datname"}}[5m])',
            legend="Inserted"
        ).add_query(
            f'rate(pg_stat_database_tup_updated{{instance=~"{instance}",datname=~"$datname"}}[5m])',
            legend="Updated"
        ).add_query(
            f'rate(pg_stat_database_tup_deleted{{instance=~"{instance}",datname=~"$datname"}}[5m])',
            legend="Deleted"
        )

        # Locks
        dashboard.add_row("Locks")

        dashboard.add_panel(
            "Lock Types",
            query=f'pg_locks_count{{instance=~"{instance}",datname=~"$datname"}}',
            panel_type="timeseries",
            width=12,
            height=8,
        )

        dashboard.add_panel(
            "Deadlocks",
            query=f'rate(pg_stat_database_deadlocks{{instance=~"{instance}",datname=~"$datname"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
        )

        # Replication
        dashboard.add_row("Replication")

        dashboard.add_panel(
            "Replication Lag",
            query=f'pg_replication_lag{{instance=~"{instance}"}}',
            panel_type="timeseries",
            width=24,
            height=8,
            unit="s",
        )

        return dashboard


class RedisTemplate(DashboardTemplate):
    """Dashboard template for Redis metrics."""

    def __init__(self):
        super().__init__(
            name="redis",
            description="Redis monitoring (memory, commands, connections, replication)",
            category="database",
            tags=["redis", "cache", "database"],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        instance = kwargs.get("instance", "$instance")

        dashboard = Dashboard(
            title=kwargs.get("title", "Redis Dashboard"),
            description="Redis metrics via redis_exporter",
            tags=["redis", "cache"],
            datasource=ds,
            refresh="30s",
        )

        dashboard.add_variable(
            "instance",
            query='label_values(redis_up, instance)',
            label="Instance",
        )

        dashboard.add_row("Overview")

        dashboard.add_panel(
            "Redis Up",
            query=f'redis_up{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        ).add_threshold(None, "red").add_threshold(1, "green")

        dashboard.add_panel(
            "Uptime",
            query=f'redis_uptime_in_seconds{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
            unit="s",
        )

        dashboard.add_panel(
            "Connected Clients",
            query=f'redis_connected_clients{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Memory Used",
            query=f'redis_memory_used_bytes{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
            unit="bytes",
        )

        dashboard.add_panel(
            "Commands/sec",
            query=f'rate(redis_commands_processed_total{{instance=~"{instance}"}}[5m])',
            panel_type="stat",
            width=4,
            height=4,
            unit="ops",
        )

        dashboard.add_panel(
            "Hit Rate",
            query=f'redis_keyspace_hits_total{{instance=~"{instance}"}} / (redis_keyspace_hits_total{{instance=~"{instance}"}} + redis_keyspace_misses_total{{instance=~"{instance}"}})',
            panel_type="gauge",
            width=4,
            height=4,
            unit="percentunit",
        ).add_threshold(None, "red").add_threshold(0.8, "yellow").add_threshold(0.95, "green")

        dashboard.add_row("Memory")

        dashboard.add_panel(
            "Memory Usage",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bytes",
        ).add_query(
            f'redis_memory_used_bytes{{instance=~"{instance}"}}',
            legend="Used"
        ).add_query(
            f'redis_memory_max_bytes{{instance=~"{instance}"}}',
            legend="Max"
        )

        dashboard.add_panel(
            "Memory Fragmentation",
            query=f'redis_mem_fragmentation_ratio{{instance=~"{instance}"}}',
            panel_type="timeseries",
            width=12,
            height=8,
        )

        dashboard.add_row("Commands")

        dashboard.add_panel(
            "Command Rate",
            query=f'rate(redis_commands_processed_total{{instance=~"{instance}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="ops",
        )

        dashboard.add_panel(
            "Cache Hits/Misses",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="ops",
        ).add_query(
            f'rate(redis_keyspace_hits_total{{instance=~"{instance}"}}[5m])',
            legend="Hits"
        ).add_query(
            f'rate(redis_keyspace_misses_total{{instance=~"{instance}"}}[5m])',
            legend="Misses"
        )

        dashboard.add_row("Connections")

        dashboard.add_panel(
            "Connected Clients",
            query=f'redis_connected_clients{{instance=~"{instance}"}}',
            panel_type="timeseries",
            width=12,
            height=8,
        )

        dashboard.add_panel(
            "Blocked Clients",
            query=f'redis_blocked_clients{{instance=~"{instance}"}}',
            panel_type="timeseries",
            width=12,
            height=8,
        )

        return dashboard


register_template(MySQLTemplate())
register_template(PostgreSQLTemplate())
register_template(RedisTemplate())
