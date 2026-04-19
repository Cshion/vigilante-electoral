#!/bin/bash
#===============================================================================
# Vigilante Electoral - Configuración mTLS con Cloudflare
#===============================================================================
# Este script configura mTLS (mutual TLS) entre Cloudflare y el servidor EC2
# usando Per-hostname Authenticated Origin Pulls.
#
# PRERREQUISITOS:
#   - Servidor EC2 configurado con setup-ec2.sh
#   - Dominio configurado en Cloudflare (DNS proxied)
#   - API Token de Cloudflare con permisos:
#     * Zone.SSL and Certificates (Edit)
#     * Zone.Zone Settings (Edit)
#
# USO:
#   ./configure-mtls.sh <EC2_HOST> <PEM_FILE> <HOSTNAME> <CF_TOKEN> <ZONE_ID>
#
# EJEMPLO:
#   ./configure-mtls.sh 34.230.76.235 ~/mykey.pem api.midominio.com cfut_xxx 751964f9b...
#
# DESPUÉS DE EJECUTAR:
#   - El servidor solo aceptará conexiones desde Cloudflare
#   - Las conexiones directas al servidor serán rechazadas (403)
#===============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # Sin color

# Configuración
EC2_USER="ubuntu"
CERTS_DIR="$(pwd)/mtls-certs"
REMOTE_CERTS_DIR="/etc/nginx/certs"
NGINX_SITE="/etc/nginx/sites-available/vigilante"

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ $1${NC}"; }

cleanup() {
    if [ $? -ne 0 ]; then
        print_error "El script falló. Los certificados generados están en: $CERTS_DIR"
        echo "Puedes eliminarlos manualmente si deseas reintentar."
    fi
}
trap cleanup EXIT

#===============================================================================
# VALIDACIÓN DE ARGUMENTOS
#===============================================================================
if [ $# -lt 5 ]; then
    echo -e "${RED}Error: Faltan argumentos${NC}"
    echo ""
    echo "Uso: $0 <EC2_HOST> <PEM_FILE> <HOSTNAME> <CF_TOKEN> <ZONE_ID>"
    echo ""
    echo "Parámetros:"
    echo "  EC2_HOST     - IP o hostname del servidor EC2"
    echo "  PEM_FILE     - Ruta al archivo PEM para SSH"
    echo "  HOSTNAME     - Hostname configurado en Cloudflare (ej: api.midominio.com)"
    echo "  CF_TOKEN     - API Token de Cloudflare"
    echo "  ZONE_ID      - Zone ID de Cloudflare (ver en Overview del dominio)"
    echo ""
    echo "Ejemplo:"
    echo "  $0 34.230.76.235 ~/key.pem api.midominio.com cfut_xxx 751964f9b8fd..."
    exit 1
fi

EC2_HOST=$1
PEM_FILE=$2
HOSTNAME=$3
CF_TOKEN=$4
ZONE_ID=$5

# Validar que el archivo PEM existe
if [ ! -f "$PEM_FILE" ]; then
    print_error "Archivo PEM no encontrado: $PEM_FILE"
    exit 1
fi

# Verificar permisos del PEM
PEM_PERMS=$(stat -f "%OLp" "$PEM_FILE" 2>/dev/null || stat -c "%a" "$PEM_FILE" 2>/dev/null)
if [ "$PEM_PERMS" != "400" ] && [ "$PEM_PERMS" != "600" ]; then
    print_warning "Permisos del PEM muy abiertos. Corrigiendo..."
    chmod 400 "$PEM_FILE"
fi

# Verificar que openssl está instalado
if ! command -v openssl &> /dev/null; then
    print_error "openssl no está instalado"
    exit 1
fi

# Verificar que curl está instalado
if ! command -v curl &> /dev/null; then
    print_error "curl no está instalado"
    exit 1
fi

# Verificar que jq está instalado (para parsear respuestas JSON)
if ! command -v jq &> /dev/null; then
    print_warning "jq no está instalado. Instalando..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install jq 2>/dev/null || { print_error "No se pudo instalar jq. Instálalo con: brew install jq"; exit 1; }
    else
        sudo apt-get install -y jq 2>/dev/null || { print_error "No se pudo instalar jq"; exit 1; }
    fi
fi

print_header "Vigilante Electoral - Configuración mTLS"

echo "Configuración:"
echo "  Servidor EC2:  $EC2_HOST"
echo "  Usuario SSH:   $EC2_USER"
echo "  PEM:           $PEM_FILE"
echo "  Hostname:      $HOSTNAME"
echo "  Zone ID:       ${ZONE_ID:0:8}..."
echo "  Directorio:    $CERTS_DIR"
echo ""

#===============================================================================
# PASO 1: VERIFICAR CONEXIÓN SSH
#===============================================================================
print_header "1/6 - Verificando conexión SSH"

if ! ssh -i "$PEM_FILE" -o ConnectTimeout=10 -o BatchMode=yes "$EC2_USER@$EC2_HOST" "echo 'OK'" &>/dev/null; then
    print_error "No se pudo conectar a $EC2_HOST"
    echo "Verifica:"
    echo "  1. El servidor está corriendo"
    echo "  2. Security Group permite SSH (puerto 22)"
    echo "  3. El archivo PEM es correcto"
    exit 1
fi

print_success "Conexión SSH verificada"

#===============================================================================
# PASO 2: GENERAR CERTIFICADOS
#===============================================================================
print_header "2/6 - Generando certificados mTLS"

# Crear directorio para certificados
mkdir -p "$CERTS_DIR"

# Verificar si ya existen certificados
if [ -f "$CERTS_DIR/ca.pem" ] && [ -f "$CERTS_DIR/client.pem" ]; then
    echo ""
    read -p "Ya existen certificados en $CERTS_DIR. ¿Regenerar? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Usando certificados existentes"
        SKIP_CERT_GEN=true
    fi
fi

if [ "$SKIP_CERT_GEN" != "true" ]; then
    print_info "Generando CA (Certificate Authority)..."
    
    # Generar CA privkey
    openssl genrsa -out "$CERTS_DIR/ca.key" 4096 2>/dev/null
    
    # Generar CA cert (self-signed, válido por 10 años)
    openssl req -new -x509 -days 3650 -key "$CERTS_DIR/ca.key" \
        -out "$CERTS_DIR/ca.pem" \
        -subj "/C=DO/ST=Santo Domingo/L=Santo Domingo/O=Vigilante Electoral/OU=mTLS CA/CN=Vigilante Electoral mTLS CA" \
        2>/dev/null
    
    print_success "CA generado: ca.pem"
    
    print_info "Generando certificado cliente (para Cloudflare)..."
    
    # Generar client privkey
    openssl genrsa -out "$CERTS_DIR/client.key" 4096 2>/dev/null
    
    # Generar CSR (Certificate Signing Request)
    openssl req -new -key "$CERTS_DIR/client.key" \
        -out "$CERTS_DIR/client.csr" \
        -subj "/C=DO/ST=Santo Domingo/L=Santo Domingo/O=Vigilante Electoral/OU=Cloudflare Client/CN=$HOSTNAME" \
        2>/dev/null
    
    # Firmar el certificado cliente con la CA (válido por 1 año)
    openssl x509 -req -days 365 -in "$CERTS_DIR/client.csr" \
        -CA "$CERTS_DIR/ca.pem" -CAkey "$CERTS_DIR/ca.key" \
        -CAcreateserial \
        -out "$CERTS_DIR/client.pem" \
        2>/dev/null
    
    # Limpiar CSR (ya no se necesita)
    rm -f "$CERTS_DIR/client.csr"
    
    print_success "Certificado cliente generado: client.pem"
    
    # Mostrar información de los certificados
    echo ""
    print_info "Certificados generados en: $CERTS_DIR"
    echo "  - ca.key      : Clave privada de la CA (NO compartir)"
    echo "  - ca.pem      : Certificado público de la CA → va al servidor"
    echo "  - client.key  : Clave privada del cliente → va a Cloudflare"
    echo "  - client.pem  : Certificado del cliente → va a Cloudflare"
fi

#===============================================================================
# PASO 3: VERIFICAR ZONE-LEVEL AOP EN CLOUDFLARE
#===============================================================================
print_header "3/6 - Verificando configuración de Cloudflare"

print_info "Verificando Zone-Level Authenticated Origin Pulls..."

# Obtener estado de Zone-Level AOP
ZONE_AOP_RESPONSE=$(curl -s -X GET \
    "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/tls_client_auth" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json")

ZONE_AOP_STATUS=$(echo "$ZONE_AOP_RESPONSE" | jq -r '.result.value // "unknown"')

if [ "$ZONE_AOP_STATUS" == "on" ]; then
    print_warning "Zone-Level AOP está activado. Desactivando..."
    
    DISABLE_RESPONSE=$(curl -s -X PATCH \
        "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/tls_client_auth" \
        -H "Authorization: Bearer $CF_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"value":"off"}')
    
    if echo "$DISABLE_RESPONSE" | jq -e '.success' > /dev/null; then
        print_success "Zone-Level AOP desactivado"
    else
        print_error "No se pudo desactivar Zone-Level AOP"
        echo "$DISABLE_RESPONSE" | jq .
        exit 1
    fi
else
    print_success "Zone-Level AOP está desactivado (correcto para per-hostname)"
fi

#===============================================================================
# PASO 4: SUBIR CERTIFICADO A CLOUDFLARE
#===============================================================================
print_header "4/6 - Configurando Per-hostname AOP en Cloudflare"

print_info "Subiendo certificado cliente a Cloudflare..."

# Leer contenido de los certificados
CLIENT_CERT=$(cat "$CERTS_DIR/client.pem")
CLIENT_KEY=$(cat "$CERTS_DIR/client.key")

# Subir certificado
UPLOAD_RESPONSE=$(curl -s -X POST \
    "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/origin_tls_client_auth/hostnames/certificates" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -F "certificate=$CLIENT_CERT" \
    -F "private_key=$CLIENT_KEY")

# Verificar si el upload fue exitoso
if echo "$UPLOAD_RESPONSE" | jq -e '.success' > /dev/null 2>&1; then
    CERT_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.result.id')
    print_success "Certificado subido. ID: ${CERT_ID:0:16}..."
else
    # Puede que el certificado ya exista, verificar
    ERROR_CODE=$(echo "$UPLOAD_RESPONSE" | jq -r '.errors[0].code // "unknown"')
    if [ "$ERROR_CODE" == "1409" ]; then
        print_warning "El certificado ya existe. Obteniendo ID existente..."
        
        EXISTING_CERTS=$(curl -s -X GET \
            "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/origin_tls_client_auth/hostnames/certificates" \
            -H "Authorization: Bearer $CF_TOKEN")
        
        CERT_ID=$(echo "$EXISTING_CERTS" | jq -r '.result[0].id // empty')
        
        if [ -z "$CERT_ID" ]; then
            print_error "No se pudo obtener el ID del certificado existente"
            exit 1
        fi
        print_success "Usando certificado existente: ${CERT_ID:0:16}..."
    else
        print_error "Error al subir certificado a Cloudflare"
        echo "$UPLOAD_RESPONSE" | jq .
        exit 1
    fi
fi

print_info "Asociando certificado con hostname: $HOSTNAME"

# Asociar hostname con certificado
ASSOCIATE_RESPONSE=$(curl -s -X PUT \
    "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/origin_tls_client_auth/hostnames" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "[{\"hostname\":\"$HOSTNAME\",\"cert_id\":\"$CERT_ID\",\"enabled\":true}]")

if echo "$ASSOCIATE_RESPONSE" | jq -e '.success' > /dev/null 2>&1; then
    print_success "Hostname asociado correctamente"
else
    print_error "Error al asociar hostname"
    echo "$ASSOCIATE_RESPONSE" | jq .
    exit 1
fi

# Verificar configuración
print_info "Verificando configuración del hostname..."

HOSTNAME_STATUS=$(curl -s -X GET \
    "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/origin_tls_client_auth/hostnames/$HOSTNAME" \
    -H "Authorization: Bearer $CF_TOKEN")

ENABLED=$(echo "$HOSTNAME_STATUS" | jq -r '.result.enabled // false')
if [ "$ENABLED" == "true" ]; then
    print_success "mTLS habilitado para $HOSTNAME en Cloudflare"
else
    print_warning "mTLS podría no estar habilitado. Verifica en el dashboard de Cloudflare."
fi

#===============================================================================
# PASO 5: CONFIGURAR SERVIDOR
#===============================================================================
print_header "5/6 - Configurando servidor EC2"

print_info "Copiando CA al servidor..."

# Crear directorio de certs en el servidor
ssh -i "$PEM_FILE" "$EC2_USER@$EC2_HOST" "sudo mkdir -p $REMOTE_CERTS_DIR"

# Copiar CA al servidor
scp -i "$PEM_FILE" "$CERTS_DIR/ca.pem" "$EC2_USER@$EC2_HOST:/tmp/ca.pem"
ssh -i "$PEM_FILE" "$EC2_USER@$EC2_HOST" "sudo mv /tmp/ca.pem $REMOTE_CERTS_DIR/ca.pem && sudo chmod 644 $REMOTE_CERTS_DIR/ca.pem"

print_success "CA copiado a $REMOTE_CERTS_DIR/ca.pem"

print_info "Configurando Nginx para mTLS..."

# Crear backup de la configuración actual
ssh -i "$PEM_FILE" "$EC2_USER@$EC2_HOST" "sudo cp $NGINX_SITE ${NGINX_SITE}.backup.$(date +%Y%m%d%H%M%S)"

# Verificar si ya tiene mTLS configurado
MTLS_EXISTS=$(ssh -i "$PEM_FILE" "$EC2_USER@$EC2_HOST" "sudo grep -c 'ssl_client_certificate' $NGINX_SITE 2>/dev/null || echo 0")

if [ "$MTLS_EXISTS" -gt "0" ]; then
    print_warning "mTLS ya está configurado en Nginx"
    read -p "¿Actualizar configuración existente? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Saltando configuración de Nginx"
        SKIP_NGINX_CONFIG=true
    fi
fi

if [ "$SKIP_NGINX_CONFIG" != "true" ]; then
    # Script para agregar directivas mTLS al bloque server de HTTPS
    ssh -i "$PEM_FILE" "$EC2_USER@$EC2_HOST" "sudo bash -c '
    # Verificar si ya existe la configuración
    if grep -q \"ssl_client_certificate\" $NGINX_SITE; then
        echo \"Actualizando configuración existente...\"
        # Actualizar path del certificado si es diferente
        sed -i \"s|ssl_client_certificate .*|ssl_client_certificate $REMOTE_CERTS_DIR/ca.pem;|\" $NGINX_SITE
    else
        # Agregar después de ssl_certificate_key (dentro del bloque HTTPS 443)
        if grep -q \"ssl_certificate_key\" $NGINX_SITE; then
            sed -i \"/ssl_certificate_key/a\\\\\\n    # mTLS - Solo permite conexiones desde Cloudflare\\n    ssl_verify_client on;\\n    ssl_client_certificate $REMOTE_CERTS_DIR/ca.pem;\" $NGINX_SITE
        else
            echo \"⚠ No se encontró ssl_certificate_key. Asegúrate de tener SSL configurado.\"
            echo \"Puedes agregar manualmente estas líneas al bloque server 443:\"
            echo \"    ssl_verify_client on;\"
            echo \"    ssl_client_certificate $REMOTE_CERTS_DIR/ca.pem;\"
        fi
    fi
    '"

    print_success "Directivas mTLS agregadas a Nginx"
fi

# Verificar configuración de Nginx
print_info "Verificando configuración de Nginx..."

NGINX_TEST=$(ssh -i "$PEM_FILE" "$EC2_USER@$EC2_HOST" "sudo nginx -t 2>&1")

if echo "$NGINX_TEST" | grep -q "successful"; then
    print_success "Configuración de Nginx válida"
    
    # Reiniciar Nginx
    print_info "Reiniciando Nginx..."
    ssh -i "$PEM_FILE" "$EC2_USER@$EC2_HOST" "sudo systemctl restart nginx"
    print_success "Nginx reiniciado"
else
    print_error "Error en configuración de Nginx:"
    echo "$NGINX_TEST"
    print_warning "Restaurando backup..."
    ssh -i "$PEM_FILE" "$EC2_USER@$EC2_HOST" "sudo cp ${NGINX_SITE}.backup.* $NGINX_SITE 2>/dev/null && sudo systemctl restart nginx"
    exit 1
fi

#===============================================================================
# PASO 6: VERIFICAR FUNCIONAMIENTO
#===============================================================================
print_header "6/6 - Verificando funcionamiento"

# Esperar a que Nginx se levante completamente
sleep 2

print_info "Verificando que el API responde a través de Cloudflare..."

# Test a través del hostname (Cloudflare)
CLOUDFLARE_TEST=$(curl -s -o /dev/null -w "%{http_code}" "https://$HOSTNAME/health" 2>/dev/null || echo "000")

if [ "$CLOUDFLARE_TEST" == "200" ]; then
    print_success "API responde correctamente a través de Cloudflare (HTTP $CLOUDFLARE_TEST)"
elif [ "$CLOUDFLARE_TEST" == "000" ]; then
    print_warning "No se pudo conectar a https://$HOSTNAME/health"
    print_info "Puede tomar unos minutos para que Cloudflare propague la configuración"
else
    print_warning "Respuesta inesperada de Cloudflare: HTTP $CLOUDFLARE_TEST"
fi

print_info "Verificando que conexiones directas son rechazadas..."

# Test directo al servidor (debería fallar con 400 o cerrar conexión)
DIRECT_TEST=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "https://$EC2_HOST/health" -k 2>/dev/null || echo "000")

if [ "$DIRECT_TEST" == "400" ] || [ "$DIRECT_TEST" == "403" ] || [ "$DIRECT_TEST" == "000" ]; then
    print_success "Conexiones directas son rechazadas correctamente (HTTP $DIRECT_TEST)"
else
    print_warning "Conexión directa devolvió HTTP $DIRECT_TEST (esperado: 400/403)"
fi

#===============================================================================
# RESUMEN FINAL
#===============================================================================
print_header "✅ CONFIGURACIÓN mTLS COMPLETA"

echo -e "${GREEN}mTLS está configurado entre Cloudflare y el servidor.${NC}\n"

echo -e "${YELLOW}Archivos generados:${NC}"
echo "  $CERTS_DIR/ca.pem      → Copiado al servidor"
echo "  $CERTS_DIR/ca.key      → Guárdalo de forma segura (NO compartir)"
echo "  $CERTS_DIR/client.pem  → Subido a Cloudflare"
echo "  $CERTS_DIR/client.key  → Subido a Cloudflare"
echo ""

echo -e "${YELLOW}Configuración aplicada:${NC}"
echo "  • Cloudflare Per-hostname AOP: habilitado para $HOSTNAME"
echo "  • Nginx: ssl_verify_client on"
echo "  • Nginx: ssl_client_certificate $REMOTE_CERTS_DIR/ca.pem"
echo ""

echo -e "${YELLOW}Verificación:${NC}"
echo "  • A través de Cloudflare: curl https://$HOSTNAME/health"
echo "  • Conexión directa (debe fallar): curl -k https://$EC2_HOST/health"
echo ""

echo -e "${RED}⚠ IMPORTANTE:${NC}"
echo "  • Guarda $CERTS_DIR/ca.key de forma segura"
echo "  • El certificado cliente expira en 1 año"
echo "  • Para renovar, ejecuta este script nuevamente"
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Comandos útiles:${NC}"
echo "  Ver config Nginx:        ssh -i $PEM_FILE $EC2_USER@$EC2_HOST 'sudo cat $NGINX_SITE'"
echo "  Verificar cert en CF:    curl -s \"https://api.cloudflare.com/client/v4/zones/$ZONE_ID/origin_tls_client_auth/hostnames/$HOSTNAME\" -H \"Authorization: Bearer \$CF_TOKEN\" | jq"
echo "  Logs Nginx:              ssh -i $PEM_FILE $EC2_USER@$EC2_HOST 'sudo tail -f /var/log/nginx/error.log'"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
