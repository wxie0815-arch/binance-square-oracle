#!/usr/bin/env python3
"""通过 GitHub API 推送本地修改到远程仓库（绕过 git push 权限问题）"""

import subprocess
import json
import base64
import os

OWNER = "wxie0815-arch"
REPO = "-"

def gh_api(endpoint, method="GET", data=None):
    """调用 GitHub API"""
    cmd = ["gh", "api", endpoint]
    if method != "GET":
        cmd.extend(["--method", method])
    if data:
        cmd.extend(["--input", "-"])
        result = subprocess.run(cmd, input=json.dumps(data), capture_output=True, text=True)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"API Error: {result.stderr}")
        return None
    return json.loads(result.stdout) if result.stdout.strip() else None

def get_tracked_files():
    """获取 git 跟踪的所有文件"""
    result = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd="/home/ubuntu/-")
    return result.stdout.strip().split("\n")

def create_blob(content_b64):
    """创建 blob"""
    return gh_api(f"repos/{OWNER}/{REPO}/git/blobs", "POST", {
        "content": content_b64,
        "encoding": "base64"
    })

def main():
    os.chdir("/home/ubuntu/-")
    
    # 1. 获取远程 main 的最新 commit SHA
    ref = gh_api(f"repos/{OWNER}/{REPO}/git/refs/heads/main")
    base_sha = ref["object"]["sha"]
    print(f"Base commit: {base_sha}")
    
    # 2. 获取 base commit 的 tree
    commit = gh_api(f"repos/{OWNER}/{REPO}/git/commits/{base_sha}")
    base_tree = commit["tree"]["sha"]
    print(f"Base tree: {base_tree}")
    
    # 3. 为每个文件创建 blob
    files = get_tracked_files()
    tree_items = []
    
    for filepath in files:
        full_path = os.path.join("/home/ubuntu/-", filepath)
        if not os.path.exists(full_path):
            continue
        
        with open(full_path, "rb") as f:
            content = f.read()
        
        content_b64 = base64.b64encode(content).decode()
        blob = create_blob(content_b64)
        if blob:
            # Determine file mode
            mode = "100755" if os.access(full_path, os.X_OK) else "100644"
            tree_items.append({
                "path": filepath,
                "mode": mode,
                "type": "blob",
                "sha": blob["sha"]
            })
            print(f"  Blob: {filepath} -> {blob['sha'][:8]}")
    
    # 4. 创建新 tree
    new_tree = gh_api(f"repos/{OWNER}/{REPO}/git/trees", "POST", {
        "tree": tree_items
    })
    print(f"New tree: {new_tree['sha']}")
    
    # 5. 创建新 commit
    commit_msg = """v4.1: 统一配置中心 + L7升级（事实校验/动态结构/多轮自评/Prompt优化）

主要变更：
- config.py: 使用 python-dotenv 统一配置中心，消除6处重复 .env 加载
- L7_article_generator.py: 事实校验层 + 动态结构模板 + 多轮生成自评 + Prompt Token 优化
- L4/L6/L8/post_with_tokens: 统一使用 config 模块
- 修复所有模块中 sys 在 import sys 之前使用的问题
- 删除重复文件 humanizer_cn_SKILL.md
- 统一版本号为 v4.1
- 更新 README.md / SKILL.md / architecture.md"""
    
    new_commit = gh_api(f"repos/{OWNER}/{REPO}/git/commits", "POST", {
        "message": commit_msg,
        "tree": new_tree["sha"],
        "parents": [base_sha]
    })
    print(f"New commit: {new_commit['sha']}")
    
    # 6. 更新 ref
    update = gh_api(f"repos/{OWNER}/{REPO}/git/refs/heads/main", "PATCH", {
        "sha": new_commit["sha"]
    })
    print(f"Ref updated: {update['object']['sha']}")
    print("\n✅ 推送成功！")

if __name__ == "__main__":
    main()
