import argparse
import json
import logging
import os
import statistics
import timeit
from typing import Dict, List

import time

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constantes
BENCHMARK_RESULTS_FILE = 'logs/mesh/benchmark_results.json'
COMPARE_RESULTS_FILE = 'logs/mesh/compare_results.json'

def benchmark_routing_latency(mesh_router: 'MeshRouterV2') -> float:
    """
    Mide la latencia de routing del MeshRouterV2.
    
    :param mesh_router: Instancia del MeshRouterV2
    :return: Latencia promedio en segundos
    """
    def route_message():
        mesh_router.route('mensaje_de_prueba')
    
    latency = timeit.timeit(route_message, number=1000)
    return latency / 1000

def benchmark_throughput(mesh_router: 'MeshRouterV2') -> float:
    """
    Mide el throughput de mensajes del MeshRouterV2.
    
    :param mesh_router: Instancia del MeshRouterV2
    :return: Throughput promedio en mensajes por segundo
    """
    def send_message():
        mesh_router.route('mensaje_de_prueba')
    
    start_time = time.time()
    for _ in range(1000):
        send_message()
    end_time = time.time()
    throughput = 1000 / (end_time - start_time)
    return throughput

def benchmark_circuit_breaker_overhead(mesh_router: 'MeshRouterV2') -> float:
    """
    Mide el overhead del circuit breaker del MeshRouterV2.
    
    :param mesh_router: Instancia del MeshRouterV2
    :return: Overhead promedio en segundos
    """
    def trigger_circuit_breaker():
        mesh_router.route('mensaje_de_prueba')
        # Simula un error para activar el circuit breaker
        raise Exception('Error de prueba')
    
    start_time = time.time()
    for _ in range(100):
        try:
            trigger_circuit_breaker()
        except Exception:
            pass
    end_time = time.time()
    overhead = (end_time - start_time) / 100
    return overhead

def generate_report(results: Dict[str, float]) -> None:
    """
    Genera un reporte JSON con los resultados del benchmark.
    
    :param results: Diccionario con los resultados del benchmark
    """
    with open(BENCHMARK_RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=4)

def compare_results(current_results: Dict[str, float]) -> None:
    """
    Compara los resultados actuales con los resultados anteriores.
    
    :param current_results: Diccionario con los resultados actuales del benchmark
    """
    if os.path.exists(BENCHMARK_RESULTS_FILE):
        with open(BENCHMARK_RESULTS_FILE, 'r') as f:
            previous_results = json.load(f)
        
        # Calcula los percentiles
        percentiles = {
            'p50': statistics.median([current_results['latency'], previous_results['latency']]),
            'p95': statistics.median_high([current_results['latency'], previous_results['latency']]),
            'p99': statistics.median_low([current_results['latency'], previous_results['latency']])
        }
        
        # Imprime la tabla de resultados
        print('Resultado del benchmark:')
        print('------------------------')
        print(f'Latencia: {current_results["latency"]:.2f} seg')
        print(f'Throughput: {current_results["throughput"]:.2f} msg/sec')
        print(f'Overhead del circuit breaker: {current_results["overhead"]:.2f} seg')
        print('Percentiles:')
        print(f'  p50: {percentiles["p50"]:.2f} seg')
        print(f'  p95: {percentiles["p95"]:.2f} seg')
        print(f'  p99: {percentiles["p99"]:.2f} seg')
        
        # Guarda los resultados de la comparación
        with open(COMPARE_RESULTS_FILE, 'w') as f:
            json.dump(percentiles, f, indent=4)

def main() -> None:
    parser = argparse.ArgumentParser(description='Ejecuta el benchmark del DOF Mesh')
    parser.add_argument('--compare', action='store_true', help='Compara con resultados anteriores')
    args = parser.parse_args()
    
    # Crea una instancia del MeshRouterV2
    mesh_router = MeshRouterV2()
    
    # Ejecuta el benchmark
    latency = benchmark_routing_latency(mesh_router)
    throughput = benchmark_throughput(mesh_router)
    overhead = benchmark_circuit_breaker_overhead(mesh_router)
    
    # Genera el reporte
    results = {
        'latency': latency,
        'throughput': throughput,
        'overhead': overhead
    }
    generate_report(results)
    
    # Compara con resultados anteriores si se especificó la opción --compare
    if args.compare:
        compare_results(results)

if __name__ == '__main__':
    main()