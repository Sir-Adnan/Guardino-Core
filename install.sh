#!/bin/bash
set -e

# ==================================================
#   GUARDINO CORE - ULTIMATE AUTO INSTALLER v2.1
#   Architecture: Python FastAPI, PostgreSQL, Redis, Docker, Nginx
#   Language: English (Terminal Safe)
# ==================================================

export DEBIAN_FRONTEND=noninteractive

# --- COLORS & THEME ---
BOLD='\033[1m'; RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'
INSTALL_DIR="/opt/guardino-core"
REPO_URL="https://github.com/Sir-Adnan/Guardino-Core.git"

if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ ERROR: This script must be run as root! (Use 'sudo -i')${NC}" 
   exit 1
fi

clear
echo -e "${CYAN}${BOLD}"
echo "  ██████  ██    ██  █████  ██████  ██████  ██ ███    ██  ██████  "
echo " ██       ██    ██ ██   ██ ██   ██ ██   ██ ██ ████   ██ ██    ██ "
echo " ██   ███ ██    ██ ███████ ██████  ██   ██ ██ ██ ██  ██ ██    ██ "
echo " ██    ██ ██    ██ ██   ██ ██   ██ ██   ██ ██ ██  ██ ██ ██    ██ "
echo "  ██████   ██████  ██   ██ ██   ██ ██████  ██ ██   ████  ██████  "
echo -e "${NC}\n${GREEN} 🚀 Welcome to Guardino Core Auto-Installer v2.1${NC}\n"

# --- 1. GET DOMAIN & SSL PREFERENCE ---
IP=$(curl -s --max-time 3 https://api.ipify.org || echo "127.0.0.1")
echo -e "${YELLOW}Server Public IP: ${IP}${NC}"
read -p "🌐 Enter Domain/Subdomain (Leave blank to use IP only): " DOMAIN

if [[ -z "$DOMAIN" ]]; then
    DOMAIN=$IP
    SYSTEM_DOMAIN="http://$IP"
    INSTALL_SSL="n"
    echo -e "${YELLOW}⚠️ Running in IP-only mode. SSL will be disabled.${NC}"
else
    read -p "🔒 Install SSL (HTTPS) for $DOMAIN using Certbot? (y/n): " INSTALL_SSL
    if [[ "$INSTALL_SSL" == "y" || "$INSTALL_SSL" == "Y" ]]; then
        SYSTEM_DOMAIN="https://$DOMAIN"
    else
        SYSTEM_DOMAIN="http://$DOMAIN"
    fi
fi

# --- 2. INSTALL SYSTEM PACKAGES ---
echo -e "\n${YELLOW}📦 Installing System Packages...${NC}"
apt-get update -yq
apt-get install -yq curl git wget nginx certbot python3-certbot-nginx openssl

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}🐳 Installing Docker Engine...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
fi

# --- 3. CLONE REPOSITORY & CLEANUP ---
echo -e "\n${YELLOW}📥 Cloning Repository...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "🧹 Cleaning up old installation..."
    cd "$INSTALL_DIR" && docker compose down -v 2>/dev/null || true
    cd /
    rm -rf "$INSTALL_DIR"
fi
git clone "$REPO_URL" "$INSTALL_DIR"
cd "$INSTALL_DIR"

# --- 4. PATCH FILES ---
echo -e "\n${YELLOW}🔧 Patching source files...${NC}"
cat <<EOF > requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic[email]==2.5.2
pydantic-settings==2.1.0
SQLAlchemy==2.0.23
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.13.0
celery==5.3.6
redis==5.0.1
httpx==0.25.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==3.2.2
python-multipart==0.0.6
EOF

cat <<EOF > Dockerfile
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# --- 5. GENERATE CREDENTIALS ---
echo -e "\n${YELLOW}🔐 Configuring Database and Credentials...${NC}"
DB_PASS="GP_$(openssl rand -hex 8)"
SECRET_KEY=$(openssl rand -hex 32)

cat <<EOF > .env
PROJECT_NAME="Guardino Core API"
VERSION="1.0.0"
SYSTEM_DOMAIN="${SYSTEM_DOMAIN}"
POSTGRES_USER=guardino_admin
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_DB=guardino_core_db
POSTGRES_HOST=db
POSTGRES_PORT=5432
SECRET_KEY=${SECRET_KEY}
EOF

sed -i "s/POSTGRES_PASSWORD:.*/POSTGRES_PASSWORD: ${DB_PASS}/" docker-compose.yml
find "$INSTALL_DIR/frontend" -type f \( -name "*.html" -o -name "*.js" \) -exec sed -i "s|http://localhost:8000|${SYSTEM_DOMAIN}|g" {} +

# --- 6. NGINX CONFIGURATION (FIXED) ---
echo -e "\n${YELLOW}🌐 Setting up Nginx Reverse Proxy...${NC}"
cat <<EOF > /etc/nginx/sites-available/guardino
server {
    listen 80;
    server_name ${DOMAIN};
    charset utf-8;

    location ~ ^/(api|sub|docs|openapi.json) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /assets/ {
        root ${INSTALL_DIR}/frontend;
    }

    location /admin {
        root ${INSTALL_DIR}/frontend;
        index index.html login.html;
        try_files \$uri \$uri/ /admin/login.html;
    }

    location / {
        root ${INSTALL_DIR}/frontend/reseller;
        index index.html login.html;
        try_files \$uri \$uri/ /login.html;
    }
}
EOF

ln -sf /etc/nginx/sites-available/guardino /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

# --- 7. DEPLOYMENT ---
echo -e "\n${YELLOW}🐳 Building and Launching Docker Containers...${NC}"
docker compose up -d --build

echo -e "\n${CYAN}⏳ Waiting for Database Initialization (20 seconds)...${NC}"
sleep 20

# --- 8. INITIALIZE DATABASE ---
echo -e "\n${YELLOW}🗄️ Initializing Database Tables...${NC}"
docker exec guardino_api python -c "
import asyncio
from app.models import Base
from app.core.database import engine
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✅ Tables Created Successfully!')
asyncio.run(init())
"

echo -e "\n${YELLOW}👑 Creating Super Admin...${NC}"
docker exec guardino_api python create_superadmin.py

# --- 9. SSL SETUP ---
if [[ "$INSTALL_SSL" == "y" || "$INSTALL_SSL" == "Y" ]]; then
    echo -e "\n${YELLOW}🔒 Installing SSL Certificate...${NC}"
    certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m admin@${DOMAIN} --redirect || echo -e "${RED}⚠️ SSL Setup Failed.${NC}"
fi

# --- 10. DONE ---
clear
echo -e "${GREEN}${BOLD}✅ Guardino Core Deployed Successfully!${NC}\n"
echo -e "===================================================="
echo -e "🌍 Resellers Panel:   ${SYSTEM_DOMAIN}"
echo -e "👑 Super Admin Panel: ${SYSTEM_DOMAIN}/admin/login.html"
echo -e "📚 API Swagger Docs:  ${SYSTEM_DOMAIN}/docs"
echo -e "====================================================\n"
echo -e "${YELLOW}🔑 Admin Credentials:${NC}"
echo -e "Username: ${BOLD}guardino_admin${NC}"
echo -e "Password: ${BOLD}Admin@12345${NC}\n"
echo -e "====================================================\n"
