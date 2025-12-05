#!/bin/bash

##############################################################################
# AILinux Nova Dark - Quick Activation Script
# Use this if you have WP-CLI access
##############################################################################

echo "=========================================="
echo "AILinux Nova Dark - Quick Activation"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if WP-CLI is available
if ! command -v wp &> /dev/null; then
    echo -e "${YELLOW}⚠ WP-CLI not found${NC}"
    echo "Please activate theme manually via WordPress Admin:"
    echo "  Appearance → Themes → Activate 'AILinux Nova Dark'"
    echo ""
    exit 1
fi

echo -e "${BLUE}Checking WordPress installation...${NC}"

# Navigate to WordPress root (adjust path if needed)
WP_ROOT="/home/zombie/wordpress/html"

if [ ! -f "$WP_ROOT/wp-config.php" ]; then
    echo -e "${YELLOW}⚠ WordPress not found at: $WP_ROOT${NC}"
    echo "Please adjust WP_ROOT path in this script"
    exit 1
fi

cd "$WP_ROOT"

echo -e "${GREEN}✓ WordPress found${NC}"
echo ""

# Get current theme
CURRENT_THEME=$(wp theme list --status=active --field=name 2>/dev/null)
echo "Current active theme: $CURRENT_THEME"
echo ""

# Check if our theme exists
THEME_EXISTS=$(wp theme list --field=name | grep -c "ailinux-nova-dark-dev" || true)

if [ "$THEME_EXISTS" -eq 0 ]; then
    echo -e "${YELLOW}✗ Theme 'ailinux-nova-dark-dev' not found${NC}"
    echo "Please ensure theme is in:"
    echo "  $WP_ROOT/wp-content/themes/ailinux-nova-dark-dev/"
    exit 1
fi

echo -e "${GREEN}✓ Theme found${NC}"
echo ""

# Activate theme
echo -e "${BLUE}Activating AILinux Nova Dark...${NC}"

if wp theme activate ailinux-nova-dark-dev 2>/dev/null; then
    echo -e "${GREEN}✓ Theme activated successfully!${NC}"
    echo ""

    # Set default CSS++ theme if not set
    CSSPP_THEME=$(wp option get theme_mods_ailinux-nova-dark-dev 2>/dev/null | grep -o "ailinux_nova_dark_csspp_theme" || true)

    if [ -z "$CSSPP_THEME" ]; then
        echo -e "${BLUE}Setting default CSS++ theme (Zen Smoke)...${NC}"
        # Note: This requires custom WP-CLI command or manual Customizer setup
        echo -e "${YELLOW}⚠ Please set CSS++ theme via Customizer:${NC}"
        echo "  Admin → Appearance → Customize → CSS++ Theme"
    fi

    echo ""
    echo "=========================================="
    echo -e "${GREEN}✓ DEPLOYMENT COMPLETE${NC}"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Visit your site to verify theme is active"
    echo "2. Go to: Appearance → Customize → CSS++ Theme"
    echo "3. Select your preferred theme (Zen Smoke/Cyberpunk/Minimal)"
    echo "4. Click 'Publish'"
    echo ""
    echo "Theme is now live! 🎉"
    echo ""

else
    echo -e "${YELLOW}✗ Activation failed${NC}"
    echo "Please activate manually via WordPress Admin"
    exit 1
fi
