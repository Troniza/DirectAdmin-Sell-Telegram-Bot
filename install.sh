#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}DirectAdmin Telegram Bot Installer${NC}"
echo "----------------------------------------"

# Create project directory
PROJECT_DIR="directadmin-tgbot"
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${GREEN}Creating project directory...${NC}"
    mkdir -p "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# Clone repository if not exists
if [ ! -d ".git" ]; then
    echo -e "${GREEN}Cloning repository...${NC}"
    git clone https://github.com/YOUR_USERNAME/directadmin-tgbot.git .
fi

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
BACKUP_ENABLED=true
BACKUP_FREQUENCY=daily
BACKUP_RETENTION_DAYS=7
EOL

echo -e "${GREEN}Environment variables set successfully!${NC}"

# Set up webhook
echo -e "${GREEN}Setting up webhook...${NC}"
read -p "Enter your domain for webhook (e.g., https://example.com): " WEBHOOK_URL

# Create systemd service
echo -e "${GREEN}Creating systemd service...${NC}"
sudo tee /etc/systemd/system/directadmin-tgbot.service << EOL
[Unit]
Description=DirectAdmin Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$(pwd)/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable directadmin-tgbot
sudo systemctl start directadmin-tgbot

echo -e "${GREEN}Installation completed!${NC}"
echo -e "${BLUE}The bot is now running as a system service.${NC}"
echo -e "${BLUE}You can check the status using: sudo systemctl status directadmin-tgbot${NC}"
