import prometheus_client

def export_prometheus(mesh_metrics):
    # Crear un objeto Prometheus Gauge para cada métrica
    node_count_gauge = prometheus_client.Gauge('node_count', 'Total de nodos registrados')
    active_nodes_gauge = prometheus_client.Gauge('active_nodes', 'Nodos con status active')
    total_messages_gauge = prometheus_client.Gauge('total_messages', 'Mensajes procesados')
    events_per_minute_gauge = prometheus_client.Gauge('events_per_minute', 'Throughput actual')
    health_score_gauge = prometheus_client.Gauge('health_score', 'Salud global del mesh')
    avg_latency_ms_gauge = prometheus_client.Gauge('avg_latency_ms', 'Latencia promedio EWMA')

    # Actualizar los valores de las métricas
    node_count_gauge.set(mesh_metrics['node_count'])
    active_nodes_gauge.set(mesh_metrics['active_nodes'])
    total_messages_gauge.set(mesh_metrics['total_messages'])
    events_per_minute_gauge.set(mesh_metrics['events_per_minute'])
    health_score_gauge.set(mesh_metrics['health_score'])
    avg_latency_ms_gauge.set(mesh_metrics['avg_latency_ms'])

    # Exponer las métricas a Prometheus
    prometheus_client.start_http_server(8000)