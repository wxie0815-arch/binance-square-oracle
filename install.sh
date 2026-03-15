#!/bin/bash
# ============================================================
# Binance Square Oracle v1.0 — Install Script
# Author: wxie0815-arch
# ============================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║     Binance Square Oracle v1.0 Installer     ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Check Python
echo -e "${CYAN}[1/5] Checking Python environment...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 not found. Please install Python 3.8+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}  Python $PYTHON_VERSION${NC}"

# 2. Init Git Submodules
echo -e "${CYAN}[2/5] Initializing Git submodules...${NC}"
if [ -f ".gitmodules" ]; then
    git submodule update --init --recursive 2>/dev/null || true
    echo -e "${GREEN}  Submodules initialized${NC}"
else
    echo -e "${YELLOW}  No .gitmodules found, skipping${NC}"
fi

# 3. Install Python dependencies
echo -e "${CYAN}[3/5] Installing Python dependencies...${NC}"
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt -q
    echo -e "${GREEN}  Dependencies installed${NC}"
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt -q
    echo -e "${GREEN}  Dependencies installed${NC}"
else
    echo -e "${RED}  pip not found. Run: pip3 install -r requirements.txt${NC}"
    exit 1
fi

# 4. Verify core modules
echo -e "${CYAN}[4/5] Verifying core modules...${NC}"
python3 -c "
import sys, os
sys.path.insert(0, '.')
modules = {
    'config': 'Configuration',
    'collect': 'Data Collection',
    'oracle': 'Oracle Engine',
    'publish': 'Square Publisher',
}
all_ok = True
for mod, desc in modules.items():
    try:
        m = __import__(mod)
        ver = getattr(m, 'VERSION', '')
        ver_str = f' v{ver}' if ver else ''
        print(f'  {desc} ({mod}{ver_str}) - OK')
    except Exception as e:
        print(f'  {desc} ({mod}) - FAIL: {e}')
        all_ok = False
if all_ok:
    print('  All modules verified!')
else:
    print('  Some modules failed. Please check dependencies.')
"

# 5. Check optional enhancements
echo -e "${CYAN}[5/5] Checking optional enhancements...${NC}"
echo ""

HAS_SQUARE=""
HAS_6551=""

if [ -n "$SQUARE_API_KEY" ]; then
    echo -e "  ${GREEN}[ENABLED]${NC} L8 Square Publishing (SQUARE_API_KEY configured)"
    HAS_SQUARE="yes"
else
    echo -e "  ${YELLOW}[NOT SET]${NC} L8 Square Publishing"
    echo -e "           Set ${CYAN}SQUARE_API_KEY${NC} to enable auto-publishing to Binance Square."
fi

if [ -n "$TOKEN_6551" ]; then
    echo -e "  ${GREEN}[ENABLED]${NC} L4 News Enhancement (TOKEN_6551 configured)"
    HAS_6551="yes"
else
    echo -e "  ${YELLOW}[NOT SET]${NC} L4 News Enhancement"
    echo -e "           Set ${CYAN}TOKEN_6551${NC} to enable hot news + KOL signal enrichment."
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Installation Complete!              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Quick Start (OpenClaw):"
echo -e "  Tell your Agent: ${CYAN}\"Use deep_analysis style to analyze BTC\"${NC}"
echo ""
echo -e "Quick Start (CLI):"
echo -e "  ${CYAN}python3 -c \"from oracle import run_oracle; r = run_oracle(style_name='deep_analysis'); print(r['final_article'])\"${NC}"
echo ""
echo -e "Available styles: daily_express, deep_analysis, onchain_insight, meme_hunter,"
echo -e "                  kol_style, oracle, project_research, trading_signal, tutorial"
echo -e "DIY: Add your own .md file to ${CYAN}prompts/${NC} directory!"
echo ""
