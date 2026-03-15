#!/usr/bin/env python3
"""通过 GitHub Contents API 逐文件推送修改"""

import subprocess
import json
import base64
import os
import time

OWNER = "wxie0815-arch"
REPO = "-"
COMMIT_MSG = "v4.1: 统一配置中心 + L7升级（事实校验/动态结构/多轮自评/Prompt优化）"

def gh_api(endpoint, method="GET", data=None):
    cmd = ["gh", "api", endpoint]
    if method != "GET":
        cmd.extend(["--method", method])
    if data:
        cmd.extend(["--input", "-"])
        result = subprocess.run(cmd, input=json.dumps(data), capture_output=True, text=True)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else None, ""

def get_remote_sha(filepath):
    """获取远程文件的 SHA"""
    data, err = gh_api(f"repos/{OWNER}/{REPO}/contents/{filepath}")
    if data:
        return data.get("sha", "")
    return ""

def update_file(filepath, local_path):
    """创建或更新远程文件"""
    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    
    remote_sha = get_remote_sha(filepath)
    payload = {
        "message": COMMIT_MSG,
        "content": content_b64,
    }
    if remote_sha:
        payload["sha"] = remote_sha
    
    data, err = gh_api(f"repos/{OWNER}/{REPO}/contents/{filepath}", "PUT", payload)
    if data:
        return True, data.get("commit", {}).get("sha", "")[:8]
    return False, err

def delete_file(filepath):
    """删除远程文件"""
    remote_sha = get_remote_sha(filepath)
    if not remote_sha:
        return True, "not found"
    
    data, err = gh_api(f"repos/{OWNER}/{REPO}/contents/{filepath}", "DELETE", {
        "message": COMMIT_MSG,
        "sha": remote_sha,
    })
    if data is not None or "200" in str(err) or not err:
        return True, "deleted"
    return False, err

def main():
    os.chdir("/home/ubuntu/-")
    
    # 修改的文件列表
    modified_files = [
        "config.py",
        "oracle_main.py",
        "L4_news_kol.py",
        "L6_article_generator.py",
        "L6_style_analyzer.py",
        "L7_article_generator.py",
        "L8_square_publisher.py",
        "post_with_tokens.py",
        ".env.example",
        "README.md",
        "SKILL.md",
        "architecture.md",
    ]
    
    # 需要删除的文件
    deleted_files = [
        "humanizer_cn_SKILL.md",
    ]
    
    print("=== 开始推送修改 ===\n")
    
    # 更新文件
    for filepath in modified_files:
        local_path = os.path.join("/home/ubuntu/-", filepath)
        if not os.path.exists(local_path):
            print(f"  ⚠️  {filepath} 不存在，跳过")
            continue
        
        ok, info = update_file(filepath, local_path)
        if ok:
            print(f"  ✅ {filepath} -> commit {info}")
        else:
            print(f"  ❌ {filepath}: {info}")
        time.sleep(0.5)  # 避免 rate limit
    
    # 删除文件
    for filepath in deleted_files:
        ok, info = delete_file(filepath)
        if ok:
            print(f"  🗑️  {filepath} -> {info}")
        else:
            print(f"  ❌ {filepath}: {info}")
        time.sleep(0.5)
    
    print("\n=== 推送完成 ===")

if __name__ == "__main__":
    main()
