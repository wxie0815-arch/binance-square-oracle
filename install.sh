#!/bin/bash
# ============================================================
# 币安广场流量预言机 — 一键安装脚本
# 作者: wxie0815-arch
# 版本: v5.0
# ============================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║     币安广场流量预言机 v5.0 安装程序          ║"
echo "  ║     Binance Square Oracle Installer           ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# 检测 Python 版本
echo -e "${CYAN}[1/6] 检查 Python 环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}未找到 Python3，请先安装 Python 3.8+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}  Python $PYTHON_VERSION${NC}"

# 初始化 Git Submodule（写作 Skill 依赖）
echo -e "${CYAN}[2/6] 初始化写作 Skill 子模块...${NC}"
if [ -f ".gitmodules" ]; then
    git submodule update --init --recursive
    echo -e "${GREEN}  写作 Skill 子模块已初始化:${NC}"
    echo "   - skills/crypto-content-writer  (二合一写作引擎)"
else
    echo -e "${YELLOW}  未找到 .gitmodules，跳过子模块初始化${NC}"
fi

# 安装 Python 依赖
echo -e "${CYAN}[3/6] 安装 Python 依赖...${NC}"
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt -q
    echo -e "${GREEN}  Python 依赖安装完成${NC}"
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt -q
    echo -e "${GREEN}  Python 依赖安装完成${NC}"
else
    echo -e "${RED}  未找到 pip，请手动安装: pip3 install -r requirements.txt${NC}"
    exit 1
fi

# 检查 OpenClaw API 配置
echo -e "${CYAN}[4/6] 检查 OpenClaw API 配置...${NC}"
python3 -c "
import sys, os
sys.path.insert(0, '.')
try:
    from config import get_llm_config
    cfg = get_llm_config()
    source = cfg.get('source', 'unknown')
    model = cfg.get('model', 'unknown')
    if source == 'system_default':
        print(f'  OpenClaw API 自动检测成功')
        print(f'  模型: {model}')
        print(f'  来源: {source} (零配置)')
    elif source == 'env':
        print(f'  环境变量 API 配置成功')
        print(f'  模型: {model}')
    else:
        print(f'  API 配置成功 (来源: {source})')
except Exception as e:
    print(f'  API 配置检测失败: {e}')
    print(f'  请检查 config.yaml 或环境变量设置')
"

# 检查可选 API 配置
echo -e "${CYAN}[5/7] 检查可选 API 配置...${NC}"
python3 -c "
import sys, os
sys.path.insert(0, '.')
import config
print(f'  L4 (6551 新闻):  ' + ('\033[0;32m已配置\033[0m' if config.HAS_6551_API else '\033[0;33m未配置 (可选)\033[0m'))
print(f'  L8 (广场发布):  ' + ('\033[0;32m已配置\033[0m' if config.HAS_SQUARE_API else '\033[0;33m未配置 (可选)\033[0m'))
if not config.HAS_6551_API or not config.HAS_SQUARE_API:
    print('\n  提示: 部分可选 API 未配置，预言机将以降级模式运行（跳过对应层级）。')
    print('  如需启用，请在 .env 或环境变量中设置 TOKEN_6551 / SQUARE_API_KEY。')
"

# 检查 config.yaml（可选高级配置）
echo -e "${CYAN}[6/7] 检查高级配置文件...${NC}"
if [ -f "config.yaml" ]; then
    echo -e "${GREEN}  找到 config.yaml 高级配置文件${NC}"
else
    if [ -f "config.yaml.example" ]; then
        echo -e "${YELLOW}  未找到 config.yaml，已提供示例文件 config.yaml.example${NC}"
        echo "   如需自定义配置，请执行: cp config.yaml.example config.yaml"
    fi
fi

# 验证核心模块
echo -e "${CYAN}[7/7] 验证核心模块...${NC}"
python3 -c "
import sys
sys.path.insert(0, '.')
modules = {
    'L0_square_monitor': '广场数据抓取',
    'data_digest': '数据精简层',
    'L7_article_generator': '文章生成引擎 v4.0',
    'writing_skill': '二阶段写作模块',
    'config': '配置管理',
}
all_ok = True
for mod, desc in modules.items():
    try:
        __import__(mod)
        print(f'  {desc} ({mod}) - OK')
    except Exception as e:
        print(f'  {desc} ({mod}) - FAIL: {e}')
        all_ok = False
if all_ok:
    print()
    print('  所有模块验证通过！')
else:
    print()
    print('  部分模块验证失败，请检查依赖安装')
"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          安装完成！                           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "快速开始："
echo -e "  ${CYAN}python3 oracle_main.py${NC}          # 运行预言机主程序"
echo -e "  ${CYAN}python3 oracle_main.py --help${NC}   # 查看所有参数"
echo ""
echo -e "生成文章示例："
echo -e "  ${CYAN}python3 oracle_main.py --deep --prompt \"写一篇关于近期BTC行情的分析\"${NC}"
echo ""
