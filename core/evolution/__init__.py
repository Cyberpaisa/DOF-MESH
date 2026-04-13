"""DOF-MESH Evolution Engine — AlphaEvolve for governance patterns."""
from core.evolution.genome import PatternGene, load_gene_pool, save_gene_pool
from core.evolution.fitness import compute_fitness
from core.evolution.operators import mutate, crossover, select_survivors
from core.evolution.population import GeneticPopulation

__all__ = [
    "PatternGene", "load_gene_pool", "save_gene_pool",
    "compute_fitness",
    "mutate", "crossover", "select_survivors",
    "GeneticPopulation",
]
