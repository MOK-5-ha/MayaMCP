# TODOs

- [ ] Add Grafana dashboard JSON for MayaMCP metrics
  - Create a dashboard JSON (store at `monitoring/grafana/maya-mcp-dashboard.json`).
  - Panels to include (Prometheus metrics exposed at `/metrics`):
    - `maya_config_memory_mb` (gauge)
    - `maya_config_max_containers` (gauge)
    - `maya_container_memory_usage_bytes` (gauge)
    - `maya_container_memory_limit_bytes` (gauge)
    - `maya_container_cpu_usage_seconds_total` (counter)
    - `maya_process_uptime_seconds` (gauge)
  - Prometheus datasource config: target `<modal-app-host>`, `metrics_path: /metrics`, `scheme: https`.
  - Add basic alerts (e.g., high memory usage %, low headroom, sustained CPU usage).
  - Document import steps in README and link to the JSON path.
  - Optional: version the dashboard file and include changelog notes.

