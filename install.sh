#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}DirectAdmin Telegram Bot Installer${NC}"
echo "----------------------------------------"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root${NC}"
    exit
fi

# Install required packages
echo -e "${GREEN}Installing required packages...${NC}"
apt update
apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Create project directory
echo -e "${GREEN}Creating project directory...${NC}"
mkdir -p /var/www
cd /var/www

# Clone repository
echo -e "${GREEN}Cloning repository...${NC}"
git clone https://github.com/Troniza/DirectAdmin-Sell-Telegram-Bot.git
cd DirectAdmin-Sell-Telegram-Bot

# Set permissions
chown -R $SUDO_USER:$SUDO_USER /var/www/DirectAdmin-Sell-Telegram-Bot

# Create virtual environment
echo -e "${GREEN}Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Install requirements
echo -e "${GREEN}Installing requirements...${NC}"
pip install -r requirements.txt

# Create .env file
echo -e "${GREEN}Setting up environment variables...${NC}"
echo "Please provide the following information:"

read -p "Enter Telegram Bot Token: " BOT_TOKEN
read -p "Enter DirectAdmin URL (e.g., https://example.com:2222): " DA_URL
read -p "Enter DirectAdmin Username: " DA_USERNAME
read -p "Enter DirectAdmin Password: " DA_PASSWORD
read -p "Enter ZarinPal Merchant ID: " MERCHANT_ID
read -p "Enter Admin User ID (Telegram): " ADMIN_ID
read -p "Enter Support Group ID (Telegram): " SUPPORT_GROUP
read -p "Enter your domain for webhook (e.g., https://example.com): " WEBHOOK_URL

# Create .env file
cat > .env << EOL
TELEGRAM_TOKEN=$BOT_TOKEN
DA_URL=$DA_URL
DA_USERNAME=$DA_USERNAME
DA_PASSWORD=$DA_PASSWORD
ZARINPAL_MERCHANT_ID=$MERCHANT_ID
ZARINPAL_SANDBOX=false
ADMIN_USER_ID=$ADMIN_ID
SUPPORT_GROUP_ID=$SUPPORT_GROUP
WEBHOOK_URL=$WEBHOOK_URL/webhook
WEBHOOK_PORT=8443
EOL

# Configure Nginx
echo -e "${GREEN}Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/directadmin-bot << EOL
server {
    listen 443 ssl;
    server_name $WEBHOOK_URL;

    ssl_certificate /etc/letsencrypt/live/$WEBHOOK_URL/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$WEBHOOK_URL/privkey.pem;

    location /webhook {
        proxy_pass http://127.0.0.1:8443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOL

# Enable site and get SSL certificate
ln -s /etc/nginx/sites-available/directadmin-bot /etc/nginx/sites-enabled/
certbot --nginx -d $WEBHOOK_URL --non-interactive --agree-tos --email admin@$WEBHOOK_URL
nginx -t && systemctl restart nginx

# Create systemd service
echo -e "${GREEN}Creating systemd service...${NC}"
cat > /etc/systemd/system/directadmin-bot.service << EOL
[Unit]
Description=DirectAdmin Telegram Bot
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=/var/www/DirectAdmin-Sell-Telegram-Bot
Environment=PATH=/var/www/DirectAdmin-Sell-Telegram-Bot/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/var/www/DirectAdmin-Sell-Telegram-Bot/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Setup firewall
echo -e "${GREEN}Configuring firewall...${NC}"
ufw allow 80
ufw allow 443
ufw --force enable

# Start and enable service
systemctl daemon-reload
systemctl enable directadmin-bot
systemctl start directadmin-bot

echo -e "${GREEN}Installation completed!${NC}"
echo -e "${BLUE}The bot is now running as a system service.${NC}"
echo -e "${BLUE}You can check the status using: systemctl status directadmin-bot${NC}"
echo -e "${BLUE}View logs using: journalctl -u directadmin-bot -f${NC}"

# Show service status
systemctl status directadmin-bot
