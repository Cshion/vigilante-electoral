#!/bin/bash
#===============================================================================
# Vigilante Electoral - Deploy to EC2
#===============================================================================
# Sube el código del backend a un servidor EC2 ya configurado
#
# USO:
#   ./deploy-to-ec2.sh <IP_O_HOST> <PATH_A_PEM>
#
# EJEMPLO:
#   ./deploy-to-ec2.sh mi-servidor.com ~/mypem.pem
#===============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
EC2_USER="ubuntu"
APP_DIR="/opt/vigilante-electoral"
APP_USER="vigilante"

# Get script directory (where backend code is)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }

#===============================================================================
# ARGUMENT VALIDATION
#===============================================================================
if [ $# -lt 2 ]; then
    echo -e "${RED}Error: Faltan argumentos${NC}"
    echo ""
    echo "Uso: $0 <IP_O_HOST> <PATH_A_PEM>"
    echo ""
    echo "Ejemplo:"
    echo "  $0 <tu-ip-ec2> ~/.ssh/my-key.pem"
    echo "  $0 mi-servidor.com ~/.ssh/server.pem"
    exit 1
fi

EC2_HOST=$1
PEM_FILE=$2

# Validate PEM file exists
if [ ! -f "$PEM_FILE" ]; then
    print_error "Archivo PEM no encontrado: $PEM_FILE"
    exit 1
fi

# Check PEM permissions
PEM_PERMS=$(stat -f "%OLp" "$PEM_FILE" 2>/dev/null || stat -c "%a" "$PEM_FILE" 2>/dev/null)
if [ "$PEM_PERMS" != "400" ] && [ "$PEM_PERMS" != "600" ]; then
    print_warning "Permisos del PEM muy abiertos. Corrigiendo..."
    chmod 400 "$PEM_FILE"
    print_success "Permisos corregidos a 400"
fi

# Validate backend directory
if [ ! -f "$BACKEND_DIR/app/main.py" ]; then
    print_error "No se encontró el código del backend en: $BACKEND_DIR"
    exit 1
fi

print_header "Vigilante Electoral - Deploy to EC2"

echo "Host:        $EC2_HOST"
echo "Usuario:     $EC2_USER"
echo "PEM:         $PEM_FILE"
echo "Backend:     $BACKEND_DIR"
echo ""

#===============================================================================
# STEP 1: TEST CONNECTION
#===============================================================================
print_header "1/4 - Verificando conexión SSH"

if ! ssh -i "$PEM_FILE" -o ConnectTimeout=10 -o BatchMode=yes "$EC2_USER@$EC2_HOST" "echo 'Conexión OK'" 2>/dev/null; then
    print_error "No se pudo conectar a $EC2_HOST"
    echo ""
    echo "Verifica:"
    echo "  1. El servidor está corriendo"
    echo "  2. El Security Group permite SSH (puerto 22)"
    echo "  3. El archivo PEM es correcto"
    exit 1
fi

print_success "Conexión SSH establecida"

#===============================================================================
# STEP 2: CHECK SERVER SETUP
#===============================================================================
print_header "2/4 - Verificando configuración del servidor"

SERVER_CHECK=$(ssh -i "$PEM_FILE" "$EC2_USER@$EC2_HOST" "
    if [ -d $APP_DIR ]; then
        echo 'APP_DIR_OK'
    else
        echo 'APP_DIR_MISSING'
    fi
    if [ -f $APP_DIR/venv/bin/python ]; then
        echo 'VENV_OK'
    else
        echo 'VENV_MISSING'
    fi
")

if echo "$SERVER_CHECK" | grep -q "APP_DIR_MISSING"; then
    print_error "El servidor no está configurado. Ejecuta primero setup-ec2.sh"
    echo ""
    echo "Instrucciones:"
    echo "  1. scp -i $PEM_FILE scripts/setup-ec2.sh $EC2_USER@$EC2_HOST:~/"
    echo "  2. ssh -i $PEM_FILE $EC2_USER@$EC2_HOST"
    echo "  3. sudo chmod +x setup-ec2.sh && sudo ./setup-ec2.sh"
    exit 1
fi

if echo "$SERVER_CHECK" | grep -q "VENV_MISSING"; then
    print_warning "Entorno virtual no encontrado, se creará durante deploy"
fi

print_success "Servidor configurado correctamente"

#===============================================================================
# STEP 3: UPLOAD CODE
#===============================================================================
print_header "3/4 - Subiendo código"

# Create temp directory for upload
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Copy app directory
echo "Preparando archivos..."
cp -r "$BACKEND_DIR/app" "$TEMP_DIR/"
cp "$BACKEND_DIR/requirements.txt" "$TEMP_DIR/"

# Upload to server
echo "Subiendo a servidor..."
rsync -avz --progress \
    -e "ssh -i $PEM_FILE" \
    "$TEMP_DIR/" \
    "$EC2_USER@$EC2_HOST:/tmp/vigilante-deploy/"

print_success "Código subido"

#===============================================================================
# STEP 4: INSTALL AND RESTART
#===============================================================================
print_header "4/4 - Instalando y reiniciando servicio"

ssh -i "$PEM_FILE" "$EC2_USER@$EC2_HOST" << 'REMOTE_SCRIPT'
set -e

APP_DIR="/opt/vigilante-electoral"
DEPLOY_DIR="/tmp/vigilante-deploy"
SERVICE_NAME="vigilante-electoral"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "📦 Moviendo código..."
sudo rm -rf $APP_DIR/app
sudo mv $DEPLOY_DIR/app $APP_DIR/
sudo cp $DEPLOY_DIR/requirements.txt $APP_DIR/

echo "🔧 Ajustando permisos..."
sudo chown -R vigilante:vigilante $APP_DIR

echo "📦 Instalando/actualizando dependencias..."
sudo -u vigilante $APP_DIR/venv/bin/pip install -q --upgrade -r $APP_DIR/requirements.txt

# ============================================================================
# CREAR SERVICIO SYSTEMD SI NO EXISTE
# ============================================================================
if [ ! -f "$SERVICE_FILE" ]; then
    echo "⚙️  Creando servicio systemd (no existía)..."
    sudo tee $SERVICE_FILE > /dev/null << 'SERVICEEOF'
[Unit]
Description=Vigilante Electoral API
After=network.target

[Service]
Type=simple
User=vigilante
Group=vigilante
WorkingDirectory=/opt/vigilante-electoral
Environment="PATH=/opt/vigilante-electoral/venv/bin"
ExecStart=/opt/vigilante-electoral/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
    echo "✓ Servicio systemd creado y habilitado"
fi

# ============================================================================
# LIBERAR PUERTO 8000 SI ESTÁ OCUPADO
# ============================================================================
echo "🔍 Verificando puerto 8000..."
if sudo fuser 8000/tcp 2>/dev/null; then
    echo "⚠️  Puerto 8000 ocupado, liberando..."
    sudo fuser -k 8000/tcp 2>/dev/null || true
    sleep 2
    echo "✓ Puerto liberado"
fi

echo "🔄 Reiniciando servicio..."
sudo systemctl restart $SERVICE_NAME

# Wait for service to start
sleep 3

echo "✅ Verificando estado..."
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "Servicio corriendo ✓"
else
    echo "⚠️  Servicio no está corriendo. Checking logs..."
    sudo journalctl -u $SERVICE_NAME -n 20 --no-pager
    exit 1
fi

# Test health endpoint
echo "🏥 Probando health endpoint..."
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health || echo "000")
if [ "$HEALTH" = "200" ]; then
    echo "Health check OK ✓"
elif [ "$HEALTH" = "503" ]; then
    echo "⚠️  Servicio corriendo pero DB no conectada (configura .env)"
else
    echo "⚠️  Health check retornó: $HEALTH"
fi

# Cleanup
rm -rf $DEPLOY_DIR

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  DEPLOY COMPLETO"
echo "═══════════════════════════════════════════════════════════════"
REMOTE_SCRIPT

print_success "Deploy completado!"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Servidor desplegado exitosamente${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "URLs:"
echo "  • Health: http://$EC2_HOST/health"
echo "  • API:    http://$EC2_HOST/"
echo "  • Docs:   DESHABILITADO en producción (DEBUG=false)"
echo ""
echo "Si aún no configuraste .env:"
echo "  ssh -i $PEM_FILE $EC2_USER@$EC2_HOST"
echo "  sudo nano /opt/vigilante-electoral/.env"
echo ""
