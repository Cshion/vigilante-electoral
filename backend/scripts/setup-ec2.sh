#!/bin/bash
#===============================================================================
# Vigilante Electoral - EC2 Ubuntu 24.04 Setup Script
#===============================================================================
# Este script configura un servidor EC2 fresco con Ubuntu 24.04 para correr
# el backend de Vigilante Electoral con FastAPI + Uvicorn + Nginx
#
# USO:
#   chmod +x setup-ec2.sh
#   sudo ./setup-ec2.sh
#
# DESPUES DE EJECUTAR:
#   1. Edita /opt/vigilante-electoral/.env con tus credenciales
#   2. Reinicia el servicio: sudo systemctl restart vigilante
#===============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="vigilante-electoral"
APP_DIR="/opt/${APP_NAME}"
APP_USER="vigilante"
SERVICE_NAME="vigilante-electoral"  # Consistent service name
PYTHON_VERSION="3.12"
DOMAIN=""  # Set if you have a domain for SSL

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

#===============================================================================
# CHECK ROOT
#===============================================================================
if [[ $EUID -ne 0 ]]; then
   print_error "Este script debe ejecutarse como root (sudo ./setup-ec2.sh)"
   exit 1
fi

print_header "Vigilante Electoral - Setup EC2 Ubuntu 24.04"

echo "Este script instalará:"
echo "  • Python ${PYTHON_VERSION} + pip + venv"
echo "  • Nginx como reverse proxy"
echo "  • Uvicorn como servidor ASGI"
echo "  • Systemd service para auto-restart"
echo "  • Firewall (UFW) configurado"
echo ""
read -p "¿Continuar? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

#===============================================================================
# 1. SYSTEM UPDATE
#===============================================================================
print_header "1/7 - Actualizando sistema"

apt update && apt upgrade -y
print_success "Sistema actualizado"

#===============================================================================
# 2. INSTALL DEPENDENCIES
#===============================================================================
print_header "2/7 - Instalando dependencias"

apt install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python3-pip \
    nginx \
    git \
    curl \
    htop \
    ufw \
    certbot \
    python3-certbot-nginx

print_success "Dependencias instaladas"

# Make python3.12 the default python3
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1

#===============================================================================
# 3. CREATE APP USER
#===============================================================================
print_header "3/7 - Creando usuario de aplicación"

if id "${APP_USER}" &>/dev/null; then
    print_warning "Usuario ${APP_USER} ya existe"
else
    useradd --system --create-home --shell /bin/bash ${APP_USER}
    print_success "Usuario ${APP_USER} creado"
fi

#===============================================================================
# 4. SETUP APPLICATION DIRECTORY
#===============================================================================
print_header "4/7 - Configurando directorio de aplicación"

mkdir -p ${APP_DIR}
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}

# Create directory structure
mkdir -p ${APP_DIR}/app
mkdir -p ${APP_DIR}/logs

print_success "Directorio ${APP_DIR} creado"

# Create requirements.txt
cat > ${APP_DIR}/requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn[standard]==0.27.0
httpx>=0.24,<0.26
supabase==2.3.4
pydantic-settings==2.1.0
pydantic==2.5.3
python-dotenv==1.0.0
beautifulsoup4==4.12.3
cachetools>=5.3.0
EOF

print_success "requirements.txt creado"

# Create .env template
cat > ${APP_DIR}/.env.template << 'EOF'
# ============================================
# Vigilante Electoral - Environment Variables
# ============================================
# Copia este archivo a .env y configura los valores
# cp .env.template .env && nano .env
# ============================================

# Application Mode
DEBUG=false

# Supabase Configuration (REQUIRED)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here

# CORS - Origins permitidos (separados por coma)
# Deja vacío para usar defaults basados en DEBUG
ALLOWED_ORIGINS=https://vigilante-electoral.vercel.app,https://tu-dominio.com

# Cron Protection - Secret para proteger endpoint /api/scrape
# Genera uno con: openssl rand -hex 32
CRON_SECRET=your-secret-here

# Optional: Override scrape interval (default: 15 min)
# SCRAPE_INTERVAL_MINUTES=15
EOF

# Copy template to .env if doesn't exist
if [ ! -f ${APP_DIR}/.env ]; then
    cp ${APP_DIR}/.env.template ${APP_DIR}/.env
    chmod 600 ${APP_DIR}/.env
    print_warning ".env creado desde template - DEBES CONFIGURARLO"
fi

# Create Python virtual environment
print_success "Creando entorno virtual Python..."
sudo -u ${APP_USER} python3 -m venv ${APP_DIR}/venv

# Install Python dependencies
print_success "Instalando dependencias Python..."
sudo -u ${APP_USER} ${APP_DIR}/venv/bin/pip install --upgrade pip
sudo -u ${APP_USER} ${APP_DIR}/venv/bin/pip install -r ${APP_DIR}/requirements.txt

print_success "Dependencias Python instaladas"

# Set ownership
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}

#===============================================================================
# 5. SETUP SYSTEMD SERVICE
#===============================================================================
print_header "5/7 - Configurando servicio systemd"

cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Vigilante Electoral FastAPI Backend
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin"
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes

# Logging
StandardOutput=append:${APP_DIR}/logs/uvicorn.log
StandardError=append:${APP_DIR}/logs/uvicorn-error.log

[Install]
WantedBy=multi-user.target
EOF

# Create log files with proper permissions
touch ${APP_DIR}/logs/uvicorn.log ${APP_DIR}/logs/uvicorn-error.log
chown ${APP_USER}:${APP_USER} ${APP_DIR}/logs/*.log

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}

print_success "Servicio ${SERVICE_NAME} configurado"

#===============================================================================
# 6. SETUP NGINX
#===============================================================================
print_header "6/7 - Configurando Nginx"

# Get server IP for default config
SERVER_IP=$(curl -s http://checkip.amazonaws.com || echo "your-server-ip")

cat > /etc/nginx/sites-available/vigilante << EOF
# Vigilante Electoral - Nginx Configuration
# 
# Para SSL con dominio propio, ejecuta:
# sudo certbot --nginx -d tu-dominio.com

upstream vigilante_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${SERVER_IP} _;  # Reemplaza con tu dominio si tienes uno

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logs
    access_log /var/log/nginx/vigilante-access.log;
    error_log /var/log/nginx/vigilante-error.log;

    # Health check - no log
    location = /health {
        access_log off;
        proxy_pass http://vigilante_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # API endpoints
    location / {
        proxy_pass http://vigilante_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Rate limiting for scrape endpoint
    location /api/scrape {
        limit_req zone=scrape burst=5 nodelay;
        proxy_pass http://vigilante_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Rate limiting zone (en nginx.conf)
if ! grep -q "limit_req_zone.*scrape" /etc/nginx/nginx.conf; then
    sed -i '/http {/a\    # Rate limiting for scrape endpoint\n    limit_req_zone $binary_remote_addr zone=scrape:10m rate=1r/m;' /etc/nginx/nginx.conf
fi

# Enable site
ln -sf /etc/nginx/sites-available/vigilante /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and restart nginx
nginx -t
systemctl restart nginx
systemctl enable nginx

print_success "Nginx configurado"

#===============================================================================
# 7. CONFIGURE FIREWALL
#===============================================================================
print_header "7/7 - Configurando Firewall"

ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (important!)
ufw allow 22/tcp comment 'SSH'

# Allow HTTP/HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Enable firewall
ufw --force enable

print_success "Firewall configurado"

#===============================================================================
# DEPLOYMENT HELPER SCRIPT
#===============================================================================
cat > ${APP_DIR}/deploy.sh << 'EOF'
#!/bin/bash
# Quick deployment script - run after updating code
set -e

APP_DIR="/opt/vigilante-electoral"
SERVICE_NAME="vigilante-electoral"
cd ${APP_DIR}

echo "🔄 Pulling latest code..."
# git pull origin main  # Uncomment if using git

echo "📦 Installing dependencies..."
${APP_DIR}/venv/bin/pip install -r requirements.txt

# Liberar puerto si está ocupado
echo "🔍 Verificando puerto 8000..."
if sudo fuser 8000/tcp 2>/dev/null; then
    echo "⚠️  Puerto 8000 ocupado, liberando..."
    sudo fuser -k 8000/tcp 2>/dev/null || true
    sleep 2
fi

echo "🔄 Restarting service..."
sudo systemctl restart ${SERVICE_NAME}

echo "✅ Deployment complete!"
echo "📊 Check status: sudo systemctl status ${SERVICE_NAME}"
echo "📋 View logs: tail -f ${APP_DIR}/logs/uvicorn.log"
EOF

chmod +x ${APP_DIR}/deploy.sh
chown ${APP_USER}:${APP_USER} ${APP_DIR}/deploy.sh

#===============================================================================
# FINAL SUMMARY
#===============================================================================
print_header "✅ INSTALACIÓN COMPLETA"

echo -e "${GREEN}El servidor está configurado. Siguiente pasos:${NC}\n"

echo -e "${YELLOW}1. Sube el código de la aplicación:${NC}"
echo "   scp -i tu-key.pem -r backend/app/* ubuntu@${SERVER_IP}:${APP_DIR}/app/"
echo ""

echo -e "${YELLOW}2. Configura las variables de entorno:${NC}"
echo "   sudo nano ${APP_DIR}/.env"
echo "   # Configura: SUPABASE_URL, SUPABASE_KEY, CRON_SECRET"
echo ""

echo -e "${YELLOW}3. Inicia el servicio:${NC}"
echo "   sudo systemctl start ${SERVICE_NAME}"
echo "   sudo systemctl status ${SERVICE_NAME}"
echo ""

echo -e "${YELLOW}4. (Opcional) Configura SSL con dominio:${NC}"
echo "   sudo certbot --nginx -d tu-dominio.com"
echo ""

echo -e "${YELLOW}5. (Opcional) Configura mTLS con Cloudflare:${NC}"
echo "   Si usas Cloudflare como proxy, ejecuta desde tu máquina local:"
echo "   ./configure-mtls.sh <EC2_IP> <PEM_FILE> <HOSTNAME> <CF_TOKEN> <ZONE_ID>"
echo "   Esto protege el servidor para que solo acepte conexiones de Cloudflare."
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Comandos útiles:${NC}"
echo "   Ver estado:     sudo systemctl status vigilante"
echo "   Ver logs:       tail -f ${APP_DIR}/logs/uvicorn.log"
echo "   Reiniciar:      sudo systemctl restart vigilante"
echo "   Test endpoint:  curl http://localhost/health"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
