#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}DirectAdmin Telegram Bot Uninstaller${NC}"
echo "----------------------------------------"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root${NC}"
    exit
fi

# Load environment variables if .env exists
if [ -f /var/www/directadmin-bot/.env ]; then
    export $(cat /var/www/directadmin-bot/.env | grep -v '^#' | xargs)
fi

# Ask for confirmation
echo -e "${RED}WARNING: This will completely remove the DirectAdmin Telegram Bot and all its data!${NC}"
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 1
fi

# Remove webhook
if [ ! -z "$TELEGRAM_TOKEN" ]; then
    echo -e "${BLUE}Removing Telegram webhook...${NC}"
    curl "https://api.telegram.org/bot${TELEGRAM_TOKEN}/deleteWebhook"
fi

# Remove SSL certificates
if [ ! -z "$DOMAIN" ]; then
    echo -e "${BLUE}Removing SSL certificates...${NC}"
    certbot delete --cert-name $DOMAIN --non-interactive
fi

# Remove Nginx configuration
echo -e "${BLUE}Removing Nginx configuration...${NC}"
rm -f /etc/nginx/sites-enabled/directadmin-bot
rm -f /etc/nginx/sites-available/directadmin-bot
systemctl restart nginx

# Drop database and user
if [ ! -z "$DB_NAME" ] && [ ! -z "$DB_USER" ]; then
    echo -e "${BLUE}Removing database and user...${NC}"
    mysql -e "DROP DATABASE IF EXISTS ${DB_NAME};"
    mysql -e "DROP USER IF EXISTS '${DB_USER}'@'localhost';"
    mysql -e "FLUSH PRIVILEGES;"
fi

# Remove project directory
echo -e "${BLUE}Removing project files...${NC}"
rm -rf /var/www/directadmin-bot

echo -e "${GREEN}Uninstallation completed!${NC}"
echo -e "${BLUE}The following changes were made:${NC}"
echo "1. Removed Telegram webhook"
echo "2. Removed SSL certificates"
echo "3. Removed Nginx configuration"
echo "4. Dropped database and database user"
echo "5. Removed all project files"

# Optional: Remove PHP and other dependencies
read -p "Do you want to remove PHP and other installed dependencies? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Removing PHP and dependencies...${NC}"
    apt remove --purge -y php8.1-fpm php8.1-mysql php8.1-curl php8.1-mbstring php8.1-xml mariadb-server composer
    apt autoremove -y
    echo -e "${GREEN}Dependencies removed successfully!${NC}"
fi
