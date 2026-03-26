import json
import random
from typing import List, Dict, Any

class GeopoliticalAnalyzer:
    """
    Analizador Geopolítico Q-AION.
    Categoriza eventos globales y predice su impacto en sectores de mercado.
    """
    def __init__(self):
        self.impact_map = {
            "CONFLICT": {"energy": 0.8, "defense": 0.9, "tech": -0.3},
            "ELECTION": {"finance": 0.5, "healthcare": 0.4, "retail": 0.2},
            "TRADE_WAR": {"tech": -0.5, "shipping": 0.7, "manufacturing": -0.4}
        }

    def analyze_headlines(self, headlines: List[str]) -> Dict[str, Any]:
        """
        Analiza titulares para detectar categorías de impacto.
        """
        print(f"[📡] ANALIZADOR: Procesando {len(headlines)} eventos críticos...")
        
        detected_impacts = {}
        for h in headlines:
            h_upper = h.upper()
            if "WAR" in h_upper or "STRIKE" in h_upper:
                self._merge_impacts(detected_impacts, "CONFLICT")
            if "TARIFF" in h_upper or "TRADE" in h_upper:
                self._merge_impacts(detected_impacts, "TRADE_WAR")
            if "VOTE" in h_upper or "ELECTION" in h_upper:
                self._merge_impacts(detected_impacts, "ELECTION")

        return {
            "signals": detected_impacts,
            "global_sentiment": "STRESS" if len(detected_impacts) > 1 else "STABLE",
            "timestamp": time.time() if 'time' in globals() else 0
        }

    def _merge_impacts(self, current, category):
        if category in self.impact_map:
            for sector, val in self.impact_map[category].items():
                current[sector] = current.get(sector, 0) + val

if __name__ == "__main__":
    analyzer = GeopoliticalAnalyzer()
    news = ["Tensions rise in trade talks", "Election results finalized in emerging market"]
    report = analyzer.analyze_headlines(news)
    print(json.dumps(report, indent=2))
