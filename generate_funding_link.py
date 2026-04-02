
#!/usr/bin/env python3
"""Generate sovereign funding link for Avalanche wallet."""

import sys
sys.path.insert(0, '.')

from core.tools.funding_tools import GenerateSovereignLinkTool

def main():
    """Generate funding link for 15.5 USDC to Avalanche wallet."""
    
    # Create an instance of the tool
    tool = GenerateSovereignLinkTool()
    
    # Generate the funding link for 15.5 USDC to the Avalanche wallet
    result = tool._run(
        amount=15.5,
        to_address="0x185CE8a11d12FCFf4e0c50DE807aFDF60DdEEa9C",
        to_chain="43114",  # Avalanche C-Chain
        to_token="USDC",   # USDC token
        label="URGENTE: Recarga de USDC para motor de yield en Avalanche"
    )
    
    print(result)
    
    # Also extract just the URL for easy copying
    lines = result.split('\n')
    for line in lines:
        if line.startswith('🔗'):
            print("\n" + "="*80)
            print("ENLACE DIRECTO PARA COPIAR:")
            print(line[2:].strip())
            print("="*80)

if __name__ == "__main__":
    main()
