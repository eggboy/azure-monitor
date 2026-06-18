# otel-prometheus

A small Python application that emits **custom metrics with the OpenTelemetry SDK**
and pushes them to **Azure Monitor managed Prometheus** over the Prometheus
remote-write protocol, authenticated with Microsoft Entra ID.

## How it works

```
OpenTelemetry SDK (Counter / Histogram / UpDownCounter)
        |  PeriodicExportingMetricReader
        v
AzureMonitorRemoteWriteExporter  --(snappy protobuf + Entra bearer token)-->
        v
https://<workspace>.<region>-1.metrics.ingest.monitor.azure.com
        /dataCollectionRules/<dcr-immutable-id>
        /streams/Microsoft-PrometheusMetrics/api/v1/write?api-version=2023-04-24
        v
Azure Monitor workspace  -->  queryable via the Prometheus query endpoint
```

The exporter subclasses the OpenTelemetry
[`PrometheusRemoteWriteMetricsExporter`](https://pypi.org/project/opentelemetry-exporter-prometheus-remote-write/)
and overrides `_build_headers()` to attach a fresh `Authorization: Bearer`
token on every export. The token comes from
`azure.identity.get_bearer_token_provider`, which caches it and refreshes it
automatically before expiry, so a long-running process keeps exporting without
manual token management.

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- An existing Azure Monitor workspace (managed Prometheus)
- An identity the app authenticates as. Locally, `DefaultAzureCredential` uses
  your `az login` session.

### Do I need to create a data collection rule (DCR)?

**No.** Creating an Azure Monitor workspace automatically provisions a **default
DCR and data collection endpoint (DCE)** in a managed resource group named
`MA_<workspace>_<region>_managed`. This app sends to the workspace's default
ingestion endpoint, so it reuses that auto-created DCR — you do not create one.
You would only author a custom DCR for advanced scenarios (custom transforms,
routing to multiple workspaces, etc.), which this app does not require.

Look up the ingestion endpoint and DCR immutable ID from the workspace:

```bash
az resource show --ids "<azure-monitor-workspace-resource-id>" \
  --query "properties.defaultIngestionSettings"
```

This returns the `ingestionEndpoints.metrics` URL (→ `AZURE_MONITOR_INGESTION_ENDPOINT`)
and the `dataCollectionRuleImmutableId` (→ `AZURE_MONITOR_DCR_IMMUTABLE_ID`),
plus the `dataCollectionRuleResourceId` used as the role-assignment scope below.

### Required Azure role assignments

| Purpose | Role | Scope |
|---|---|---|
| **Send** metrics (remote write) | `Monitoring Metrics Publisher` | The workspace's data collection rule (DCR) |
| **Query** metrics (verification only) | `Monitoring Data Reader` | The Azure Monitor workspace |

Grant the publisher role to the identity the app runs as (see authentication
options below). For local development that is your signed-in user:

```bash
az role assignment create \
  --assignee "$(az ad signed-in-user show --query id -o tsv)" \
  --role "Monitoring Metrics Publisher" \
  --scope "<dataCollectionRuleResourceId>"
```

### Authentication options

The app uses `DefaultAzureCredential`, so **no service principal is required for
local use** — it picks up your `az login` session automatically. For
non-interactive or production runs, use one of the following (assign the same
`Monitoring Metrics Publisher` role on the DCR to whichever identity you choose):

- **Service principal** (CI, servers without managed identity):

  ```bash
  az ad sp create-for-rbac --name otel-prometheus-sp
  # then assign the role to the SP's appId:
  az role assignment create --assignee "<appId>" \
    --role "Monitoring Metrics Publisher" --scope "<dataCollectionRuleResourceId>"
  ```

  Provide credentials via env vars (read by `DefaultAzureCredential`):
  `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`.

- **Managed identity** (AKS, VM, Container Apps, App Service): assign the role to
  the managed identity. `DefaultAzureCredential` uses it automatically; for a
  user-assigned identity also set `AZURE_CLIENT_ID` to its client ID.

## Setup

```bash
uv sync
cp .env.example .env   # then edit .env with your workspace values
```

`.env` (git-ignored) configures the target workspace:

```dotenv
AZURE_MONITOR_INGESTION_ENDPOINT=https://<workspace>.<region>-1.metrics.ingest.monitor.azure.com
AZURE_MONITOR_DCR_IMMUTABLE_ID=dcr-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `AZURE_MONITOR_INGESTION_ENDPOINT` | yes | - | Workspace metrics ingestion host (no trailing path) |
| `AZURE_MONITOR_DCR_IMMUTABLE_ID` | yes | - | Default data collection rule immutable ID |
| `AZURE_MONITOR_API_VERSION` | no | `2023-04-24` | Remote-write API version |
| `OTEL_SERVICE_NAME` | no | `otel-prometheus-demo` | `service_name` label |
| `OTEL_JOB` | no | `otel-prometheus-demo` | `job` label |
| `OTEL_INSTANCE_ID` | no | hostname | `instance` label |
| `EXPORT_INTERVAL_SECONDS` | no | `15` | Export push interval |
| `RUN_SECONDS` | no | `0` | Stop after N seconds (`0` = run until Ctrl+C) |

## Run

```bash
uv run otel-prometheus
```

Run for a fixed duration with a faster push interval (useful for testing):

```bash
EXPORT_INTERVAL_SECONDS=10 RUN_SECONDS=30 uv run otel-prometheus
```

## Custom metrics emitted

| Metric | Type | Labels |
|---|---|---|
| `demo_requests_total` | Counter | `http_method`, `route`, `status_code` |
| `demo_request_duration_seconds` | Histogram (`_bucket`, `_count`, `_sum`) | `http_method`, `route`, `status_code` |
| `demo_active_connections` | UpDownCounter (gauge) | `pool` |

Every series also carries the `job`, `instance`, and `service_name` resource
labels, plus the `microsoft_amwresourceid` label that Azure adds on ingestion.

> Metric units are intentionally baked into the names (`_total`, `_seconds`)
> and the OpenTelemetry `unit` field is left unset. Setting `unit` makes the
> exporter append a unit suffix (e.g. `demo_requests_total_1`), which breaks
> Prometheus naming conventions.

## Verify ingestion

Allow up to a minute for ingestion latency, then query the workspace's
Prometheus query endpoint:

```bash
QEP="https://<workspace>.<region>.prometheus.monitor.azure.com"
TOKEN=$(az account get-access-token --resource https://prometheus.monitor.azure.com --query accessToken -o tsv)
curl -s -G "$QEP/api/v1/query" \
  --data-urlencode "query=demo_requests_total" \
  -H "Authorization: Bearer $TOKEN" | jq
```

## Develop

```bash
uvx ruff check --fix . && uvx ruff format .   # lint + format
uv run pytest -q                              # tests
uvx pip-audit                                 # vulnerability scan
uv run --with deptry deptry .                 # dependency hygiene
```
