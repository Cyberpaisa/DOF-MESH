```python
import prometheus_client

def export_prometheus(mesh_metrics):
    # Create a Prometheus Gauge object for each metric
    node_count_gauge = prometheus_client.Gauge('node_count', 'Total registered nodes')
    active_nodes_gauge = prometheus_client.Gauge('active_nodes', 'Nodes with active status')
    total_messages_gauge = prometheus_client.Gauge('total_messages', 'Processed messages')
    events_per_minute_gauge = prometheus_client.Gauge('events_per_minute', 'Current throughput')
    health_score_gauge = prometheus_client.Gauge('health_score', 'Global mesh health')
    avg_latency_ms_gauge = prometheus_client.Gauge('avg_latency_ms', 'EWMA average latency')

    # Update metric values
    node_count_gauge.set(mesh_metrics['node_count'])
    active_nodes_gauge.set(mesh_metrics['active_nodes'])
    total_messages_gauge.set(mesh_metrics['total_messages'])
    events_per_minute_gauge.set(mesh_metrics['events_per_minute'])
    health_score_gauge.set(mesh_metrics['health_score'])
    avg_latency_ms_gauge.set(mesh_metrics['avg_latency_ms'])

    # Expose metrics to Prometheus
    prometheus_client.start_http_server(8000)
```
