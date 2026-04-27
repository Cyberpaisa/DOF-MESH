#!/bin/bash
# provision_vm.sh - Configuración del Laboratorio Soberano Defensivo
# Ejecutar como root dentro de Ubuntu Server ARM64 (UTM)

set -euo pipefail

echo "=== DOF-MESH :: Laboratorio de Análisis Defensivo ==="
echo "=== Provisionando VM soberana... ==="

# 1. Actualización base
apt-get update && apt-get upgrade -y

# 2. Instalar dependencias esenciales
apt-get install -y \
    curl wget git vim htop net-tools iputils-ping \
    ca-certificates gnupg lsb-release \
    ufw fail2ban

# 3. Instalar Docker (ARM64 oficial)
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 4. Crear usuario de laboratorio (no root)
LAB_USER="dofoperator"
useradd -m -s /bin/bash "$LAB_USER"
usermod -aG docker "$LAB_USER"

# 5. Instalar Ollama como el usuario de laboratorio (no como root)
echo ">>> Instalando Ollama como $LAB_USER..."
su - "$LAB_USER" -c "curl -fsSL https://ollama.com/install.sh | sh"

# 6. Configurar red interna aislada (sin gateway, sin DNS externo)
# Nota: En UTM, la interfaz debe estar en modo "Disconnected" o "Internal Network"
cat << 'NETCFG' > /etc/netplan/01-lab-network.yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 10.10.10.2/24
      routes: []  # Sin gateway = sin salida
      nameservers:
        addresses: []  # Sin DNS externo
NETCFG
netplan apply

# 7. Crear directorios del proyecto
mkdir -p /opt/dof-mesh/{models,logs,reports,lab}
chown -R "$LAB_USER:$LAB_USER" /opt/dof-mesh
chmod 755 /opt/dof-mesh/logs

# 8. Configurar firewall estricto
ufw --force reset
ufw default deny incoming
ufw default deny outgoing
ufw allow in on lo
ufw allow out on lo
ufw --force enable

echo "=== Provisionamiento completado ==="
