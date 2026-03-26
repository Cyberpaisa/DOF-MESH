import torch
import torch.nn as nn
from typing import List, Dict, Any

class DistributedMoERouter(nn.Module):
    """
    Simulación de un Ruteador de Expertos Distribuido para Inferencia de Alta Escala.
    El fallo sutil reside en la sincronización de KV-Cache durante el ruteo Top-K.
    """
    def __init__(self, num_experts=32, d_model=4096, top_k=2):
        super().__init__()
        self.num_experts = num_experts
        self.top_k = top_k
        self.gate = nn.Linear(d_model, num_experts, bias=False)
        self.experts = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(num_experts)])

    def forward(self, x, kv_cache=None):
        # x shape: [batch_size, seq_len, d_model]
        batch_size, seq_len, d_model = x.shape
        
        # Gating logic
        gate_logits = self.gate(x) # [batch_size, seq_len, num_experts]
        weights, indices = torch.topk(gate_logits, self.top_k, dim=-1)
        weights = torch.softmax(weights, dim=-1)

        # Simulación de ruteo distribuido
        output = torch.zeros_like(x)
        
        for k in range(self.top_k):
            expert_idx = indices[:, :, k] # [batch_size, seq_len]
            
            # ATENCIÓN: Aquí es donde la gestión de KV-Cache falla al no segmentar 
            # las cabezas de atención por experto en el buffer global.
            if kv_cache is not None:
                # El buffer se sobrescribe de manera no determinista si varios 
                # expertos acceden al mismo offset de memoria.
                kv_cache.update(expert_idx, x) 

            # Cálculo de la contribución del experto (Simplificado)
            # NOTA: En un sistema real, esto iría a nodos remotos.
            for i in range(self.num_experts):
                mask = (expert_idx == i)
                if mask.any():
                    output[mask] += weights[:, :, k][mask].unsqueeze(-1) * self.experts[i](x[mask])

        return output, kv_cache

# NOTA PARA EL AUDITOR:
# Tenemos un problema de 'Attention Drift' y 'Race Conditions' en el KV-Cache 
# cuando seq_len > 1M tokens. El buffer de memoria asume que el ruteo es 
# secuencial, pero en hardware paralelo (Metal/NPU) los punteros de memoria 
# colisionan. ¿Cómo rediseñarías el esquema de direccionamiento para 1T parámetros?
