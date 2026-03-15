#!/usr/bin/env python3
"""
writing_skill.py - 写作引擎模块 v1.0 (终版)
================================================================
- 彻底移除所有 AI 模型选配配置，统一调用 OpenClaw 系统 API
"""

import os
import config

# ---------------------------------------------------------------------------
# Skill Prompt 加载
# ---------------------------------------------------------------------------
SKILLS_DIR = os.path.join(os.path.dirname(__file__), "skills")

def _load_skill_prompt(skill_name: str) -> str:
    """加载指定 skill 的 SKILL.md 内容（去掉 YAML frontmatter）"""
    skill_path = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    if not os.path.exists(skill_path):
        print(f"[WritingSkill] 警告: Skill not found: {skill_path}")
        return ""
    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()
    parts = content.split("---", 2)
    if len(parts) >= 3:
        return parts[2].strip()
    return content.strip()

# ---------------------------------------------------------------------------
# 内置 Humanizer 规则
# ---------------------------------------------------------------------------
HUMANIZER_SYSTEM_PROMPT = """你是一名资深的中文 Web3 内容编辑。你的任务是对文章进行去 AI 味润色。

## 必须执行的规则

### 禁用词（发现即删除或替换）
赋能、颗粒度、闭环、底层逻辑、生态位、维度、全链路、破局、范式、协同、
综上所述、不得不说、值得注意的是、欢迎关注、建议收藏、干货满满、未来可期、前景广阔、
此外、然而、因此、总而言之、不可忽视的是

### 禁用结构
- 三段排比：\"不仅仅是X，更是Y\"、\"创新、突破与变革\"
- 空洞归因：\"研究表明\"、\"业内人士指出\"、\"各大机构认为\"
- 升华结尾：\"让我们拭目以待\"、\"未来充满无限可能\"

### 必须采用
- 代币格式：所有代币前后加空格，如 $BTC 、 $ETH
- 具体数字：将\"大幅下跌\"改为具体百分比
- 口语化：多用\"说实话\"、\"其实\"、\"反正\"、\"有点慌\"、\"没想到\"
- 开放式结尾：用具体问题结束，如\"你今天账户什么情况？\"

### 输出要求
直接输出润色后的文章正文，不要输出任何分析过程或检测报告。"""

# ---------------------------------------------------------------------------
# 写作引擎类
# ---------------------------------------------------------------------------
class WritingSkill:
    """写作引擎 v1.0 (终版)"""

    def __init__(self):
        self.writer_prompt = _load_skill_prompt("crypto-content-writer")
        if not self.writer_prompt:
            print("[WritingSkill] 警告: crypto-content-writer skill 未找到，使用内置 prompt")
            self.writer_prompt = self._fallback_writer_prompt()

    def generate_article(self, core_digest: str, style_fingerprint: str,
                         user_prompt: str, style_prompt: str) -> dict:
        """v1.0 二阶段写作流程"""

        # 阶段一：生成初稿
        writer_user_prompt = f"""# 核心情报\n{core_digest}\n\n# 写作风格指纹\n{style_fingerprint}\n\n# 用户要求\n{user_prompt}\n\n# 具体风格要求\n{style_prompt}"""
        draft = config.call_llm(
            system_prompt=self.writer_prompt,
            user_prompt=writer_user_prompt,
            max_tokens=3000
        )

        # 阶段二：去AI味润色
        humanized_article = config.call_llm(
            system_prompt=HUMANIZER_SYSTEM_PROMPT,
            user_prompt=draft,
            max_tokens=3000
        )

        return {
            "draft": draft,
            "final_article": humanized_article,
        }

    def _fallback_writer_prompt(self) -> str:
        """当 crypto-content-writer skill 未找到时的备用 prompt"""
        return """你是一名顶级的加密货币内容创作者。请根据以下核心情报、写作风格指GIN和用户要求，创作一篇高质量的分析文章。"""
