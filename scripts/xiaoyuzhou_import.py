#!/usr/bin/env python3
r"""
xiaoyuzhou_import.py — 小宇宙单集一键导入 Obsidian

用法:
    python xiaoyuzhou_import.py <小宇宙集单URL>
    python xiaoyuzhou_import.py <URL> --podcast 面基 --ep 153 --host 厚望
    python xiaoyuzhou_import.py <URL> --no-llm   # 只生成逐字稿，跳过 AI 摘要
    python xiaoyuzhou_import.py <URL> --vault-root "D:\Your Obsidian Vault"

环境变量（已与现有脚本共用）:
    ASSEMBLYAI_API_KEY        转录 API key
    ANTHROPIC_API_KEY         Claude API key（内容生成）
    XIAOYUZHOU_ACCESS_TOKEN   可选，私有播客时提供

依赖:
    pip install anthropic requests opencc-python-reimplemented
    （assemblyai、playwright 已有）
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ─── 路径配置 ──────────────────────────────────────────────────────────────
DEFAULT_VAULT_ROOT = None
DEFAULT_BASE_DIR = "02-博主素材库"

# 播客标题（API 返回值） → vault 子目录名
# 如遇未收录的播客，脚本会提示并询问
PODCAST_DIR_MAP: dict[str, str] = {
    "面基": "面基",
    "给女孩的商业第一课": "给女孩的商业第一课",
    "八分半": "八分半",
    "孟岩的投资实证": "孟岩",
    "曲率电台": "曲率",
    "刘润·进化岛": "刘润",
    "斯斯与嘉宾": "斯斯",
    "张小珺Jùn": "张小珺",
    "李诞": "李诞",
}

# ─── 环境变量 ──────────────────────────────────────────────────────────────
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
XIAOYUZHOU_TOKEN = os.getenv("XIAOYUZHOU_ACCESS_TOKEN", "").strip()

ASSEMBLYAI_BASE = "https://api.assemblyai.com/v2"


# ══════════════════════════════════════════════════════════════════════════════
# 1. 小宇宙集单抓取
# ══════════════════════════════════════════════════════════════════════════════

def extract_eid(url: str) -> str:
    """从集单 URL 中提取 episode ID"""
    m = re.search(r"/episode/([a-f0-9]+)", url)
    if not m:
        raise ValueError(f"无法从 URL 中提取 episode ID：{url}")
    return m.group(1)


def _http_json(url: str, *, method="GET", headers=None, payload=None, timeout=30) -> dict:
    data = None
    hdrs = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _xiaoyuzhou_headers() -> dict:
    local_time = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    return {
        "Host": "api.xiaoyuzhoufm.com",
        "User-Agent": "Xiaoyuzhou/2.57.1 (build:1576; iOS 17.4.1)",
        "Market": "AppStore",
        "App-BuildNo": "1576",
        "OS": "ios",
        "x-jike-access-token": XIAOYUZHOU_TOKEN,
        "BundleID": "app.podcast.cosmos",
        "App-Version": "2.57.1",
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Local-Time": local_time,
        "Timezone": "Asia/Shanghai",
    }


def _iso_date(value: str) -> str:
    if not value:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    except ValueError:
        return value[:10]


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _extract_audio_url(item: dict) -> str:
    enclosure = item.get("enclosure") or {}
    if isinstance(enclosure, dict) and enclosure.get("url"):
        return enclosure["url"]
    return (((item.get("media") or {}).get("source") or {}).get("url")) or ""


def fetch_episode_official(eid: str) -> dict | None:
    """用官方 API 拉取单集详情（需要 XIAOYUZHOU_ACCESS_TOKEN）"""
    if not XIAOYUZHOU_TOKEN:
        return None
    try:
        data = _http_json(
            "https://api.xiaoyuzhoufm.com/v1/episode/get",
            method="POST",
            headers=_xiaoyuzhou_headers(),
            payload={"eid": eid},
        )
        item = data.get("data") or data
        if not item or not item.get("title"):
            return None
        return {
            "eid": eid,
            "title": (item.get("title") or "").strip(),
            "date": _iso_date(item.get("pubDate") or ""),
            "audio_url": _extract_audio_url(item),
            "show_notes": _strip_html(item.get("shownotes") or item.get("description") or ""),
            "podcast_title": (((item.get("podcast") or {}).get("title")) or "").strip(),
        }
    except Exception as exc:
        print(f"  [官方 API 失败，改用网页解析] {exc}", file=sys.stderr)
        return None


def fetch_episode_webpage(eid: str) -> dict:
    """解析集单页面的 __NEXT_DATA__ JSON"""
    url = f"https://www.xiaoyuzhoufm.com/episode/{eid}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html_text = resp.read().decode("utf-8", errors="replace")

    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>\s*(\{.*?\})\s*</script>', html_text, re.DOTALL)
    if not m:
        raise RuntimeError("页面中未找到 __NEXT_DATA__，可能需要登录或页面结构变更")

    page_data = json.loads(m.group(1))
    item = page_data["props"]["pageProps"]["episode"]

    return {
        "eid": eid,
        "title": (item.get("title") or "").strip(),
        "date": _iso_date(item.get("pubDate") or ""),
        "audio_url": _extract_audio_url(item),
        "show_notes": _strip_html(item.get("shownotes") or item.get("description") or ""),
        "podcast_title": (((item.get("podcast") or {}).get("title")) or "").strip(),
    }


def fetch_episode(url: str) -> dict:
    """主入口：先尝试官方 API，fallback 到网页解析"""
    eid = extract_eid(url)
    print(f"📌 Episode ID: {eid}")

    episode = fetch_episode_official(eid) or fetch_episode_webpage(eid)

    if not episode.get("audio_url"):
        raise RuntimeError("未能获取音频 URL，请检查集单是否公开")

    print(f"   标题: {episode['title']}")
    print(f"   日期: {episode['date']}")
    print(f"   播客: {episode['podcast_title']}")
    print(f"   音频: {episode['audio_url'][:60]}...")
    return episode


# ══════════════════════════════════════════════════════════════════════════════
# 2. AssemblyAI 转录
# ══════════════════════════════════════════════════════════════════════════════

def _aai_headers() -> dict:
    if not ASSEMBLYAI_API_KEY:
        raise RuntimeError("请设置环境变量 ASSEMBLYAI_API_KEY")
    return {"authorization": ASSEMBLYAI_API_KEY, "content-type": "application/json"}


def submit_transcription(audio_url: str) -> str:
    """提交转录任务，返回 transcript_id"""
    import requests
    payload = {
        "audio_url": audio_url,
        "speech_models": ["universal-3-pro", "universal-2"],
        "language_code": "zh",
        "speaker_labels": True,
        "speakers_expected": 2,
    }
    resp = requests.post(f"{ASSEMBLYAI_BASE}/transcript", json=payload, headers=_aai_headers(), timeout=30)
    resp.raise_for_status()
    tid = resp.json()["id"]
    print(f"✅ 转录任务已提交: {tid}")
    return tid


def wait_for_transcript(transcript_id: str, poll_interval: int = 8) -> dict:
    """轮询直到转录完成，返回完整响应"""
    import requests
    url = f"{ASSEMBLYAI_BASE}/transcript/{transcript_id}"
    print("⏳ 等待转录完成", end="", flush=True)
    while True:
        resp = requests.get(url, headers=_aai_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status == "completed":
            print(" ✓")
            return data
        if status == "error":
            raise RuntimeError(f"转录失败: {data.get('error')}")
        print(".", end="", flush=True)
        time.sleep(poll_interval)


# ══════════════════════════════════════════════════════════════════════════════
# 3. 逐字稿重建
# ══════════════════════════════════════════════════════════════════════════════

def _ms_to_ts(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60:02d}:{s % 60:02d}"


try:
    from opencc import OpenCC as _OpenCC
    _t2s = _OpenCC("t2s").convert
except Exception:
    _t2s = lambda x: x  # noqa: E731


def _merge_chinese_spaces(text: str) -> str:
    text = re.sub(r"(?<=[一-鿿])\s+(?=[一-鿿])", "", text)
    text = re.sub(r"(?<=[一-鿿])\s+(?=[，。！？；：、）】》])", "", text)
    text = re.sub(r"(?<=[（【《])\s+(?=[一-鿿])", "", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    return _t2s(text)


def rebuild_transcript(utterances: list[dict]) -> str:
    """
    从 AssemblyAI utterances 重建逐字稿。
    说话人标签保留为 spk_a / spk_b（用户自行替换为真实姓名）。
    """
    if not utterances:
        return "（无转录内容）"

    # 统一说话人标签
    speaker_map: dict[str, str] = {}
    counter = 1
    for utt in utterances:
        raw = str(utt.get("speaker") or "").upper()
        if raw not in speaker_map:
            speaker_map[raw] = f"spk{counter}"
            counter += 1

    lines: list[str] = []
    current_spk: str | None = None
    buffer: list[str] = []
    ts_first: int = 0

    def flush():
        if buffer and current_spk:
            text = _merge_chinese_spaces(" ".join(buffer))
            lines.append(f"\n**{current_spk} [{_ms_to_ts(ts_first)}]**")
            lines.append(text)

    for utt in utterances:
        raw = str(utt.get("speaker") or "").upper()
        spk = speaker_map[raw]
        text = _merge_chinese_spaces(utt.get("text") or "")
        if not text:
            continue
        if spk != current_spk:
            flush()
            current_spk = spk
            ts_first = utt.get("start") or 0
            buffer = [text]
        else:
            buffer.append(text)

    flush()
    return "\n".join(lines).strip()


# ══════════════════════════════════════════════════════════════════════════════
# 4. Claude API：生成导读 / 章节速览 / 要点回顾
# ══════════════════════════════════════════════════════════════════════════════

GENERATE_PROMPT = """\
你在帮用户整理播客笔记存入 Obsidian。

播客：{podcast}
本期标题：{title}

{context}

---

请严格按以下格式输出三个部分，不要任何额外说明：

## 导读

> [一段话，概括本期核心内容、嘉宾背景和最值得收听的理由，100-150 字]

### 章节速览

- **[MM:SS] 章节标题**
  一句话描述
（至少 5 个章节；时间戳从逐字稿提取，格式固定为 MM:SS）

### 要点回顾

**Q: [核心问题]**
A: [精炼回答，2-3 句]

（3-5 组 Q&A，选最有信息量的观点）\
"""


def generate_content(episode: dict, transcript: str) -> str:
    """用 claude -p 子进程生成摘要三段（与 Claude Code 共用认证，无需额外 API key）"""
    import shutil
    import subprocess
    import tempfile

    claude_bin = shutil.which("claude")
    if not claude_bin or not Path(claude_bin).exists():
        print("⚠️  找不到 claude 可执行文件，跳过 AI 生成")
        return _empty_sections()

    # 构建上下文：show notes 优先，逐字稿补充
    parts: list[str] = []
    if episode.get("show_notes"):
        parts.append(f"## Show Notes（官方简介）\n{episode['show_notes']}")
    parts.append(f"## 逐字稿\n{transcript}")
    context = "\n\n".join(parts)

    prompt = GENERATE_PROMPT.format(
        podcast=episode.get("podcast_title", ""),
        title=episode["title"],
        context=context,
    )

    system_prompt = "你是专业的播客内容整理助手，擅长提炼核心信息。输出使用中文。"

    # 写入临时文件避免命令行转义问题
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False) as f:
        f.write(prompt)
        prompt_file = f.name

    print("🤖 调用 Claude 生成导读...")
    try:
        result = subprocess.run(
            [claude_bin, "-p", system_prompt],
            input=Path(prompt_file).read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
        if result.returncode != 0:
            print(f"⚠️  claude 调用失败: {result.stderr[:200]}")
            return _empty_sections()
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print("⚠️  claude 调用超时，跳过 AI 生成")
        return _empty_sections()
    finally:
        Path(prompt_file).unlink(missing_ok=True)


def _empty_sections() -> str:
    return """\
## 导读

> （待填写）

### 章节速览

- **[00:00] **


### 要点回顾

**Q: **
A: \
"""


# ══════════════════════════════════════════════════════════════════════════════
# 5. 组装 Markdown & 写入 Vault
# ══════════════════════════════════════════════════════════════════════════════

def _extract_ep_num(title: str) -> str:
    for pattern in [
        r"[Ee][Pp]?[.\s#_-]*(\d{2,4})",
        r"^#?(\d{2,4})[.\s#_-]",
        r"第\s*(\d{1,4})\s*[期集]",
    ]:
        m = re.search(pattern, title)
        if m:
            return m.group(1).zfill(3)
    return ""


def _clean_filename(title: str, ep_num: str = "") -> str:
    # Remove leading "37." / "E150." / "EP150 " style prefix that duplicates ep_num
    if ep_num:
        title = re.sub(r"^[Ee][Pp]?\s*\d+[.\s_-]*", "", title)
        title = re.sub(r"^\d+[.\s_-]+", "", title)
    title = re.sub(r'[\\/:*?"<>|]', "，", title)
    return re.sub(r"\s+", " ", title).strip()[:120]


def build_markdown(
    episode: dict,
    transcript: str,
    generated: str,
    ep_num: str,
    host: str,
) -> str:
    title = episode["title"]
    date = episode["date"]
    podcast = episode.get("podcast_title", "")
    ep_label = f"{ep_num} · " if ep_num else ""
    heading_title = _clean_filename(title, ep_num)

    return f"""\
---
title: "{title}"
ep: "{ep_num}"
date: {date}
podcast: {podcast}
host: {host or "（待填写）"}
tags:
  - 待补充
---

# {ep_label}{heading_title}

{generated}

---

## 原文逐字稿

{transcript}
"""


def resolve_podcast_dir(podcast_title: str, cli_override: str) -> str:
    """确定播客子目录名，优先级：CLI 参数 > 映射表 > 询问用户"""
    if cli_override:
        return cli_override
    mapped = PODCAST_DIR_MAP.get(podcast_title)
    if mapped:
        return mapped
    # 未收录：询问用户
    print(f"\n⚠️  播客「{podcast_title}」不在目录映射表中。")
    name = input("请输入 vault 子目录名（直接回车使用播客标题）: ").strip()
    return name or podcast_title


def write_to_vault(content: str, base_dir: Path, podcast_dir: str, filename: str) -> Path:
    dest_dir = base_dir / podcast_dir / "播客"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_text(content, encoding="utf-8")
    return dest


# ══════════════════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="小宇宙单集一键导入 Obsidian",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="小宇宙集单 URL")
    parser.add_argument("--podcast", default="", help="vault 子目录名（如 '面基'），未填则自动检测")
    parser.add_argument("--ep", default="", help="集数编号（如 '153'），未填则从标题提取")
    parser.add_argument("--host", default="", help="主播名，写入 frontmatter")
    parser.add_argument("--no-llm", action="store_true", help="跳过 Claude 摘要生成，只输出逐字稿")
    parser.add_argument("--vault-root", required=True, help="Obsidian Vault 根目录")
    parser.add_argument("--base-dir", default=DEFAULT_BASE_DIR, help="Vault 内的博主素材库目录")
    args = parser.parse_args()

    print("\n═══ 小宇宙播客导入 ═══\n")

    # 1. 获取集单信息
    episode = fetch_episode(args.url)

    # 2. 确定播客目录
    podcast_dir = resolve_podcast_dir(episode["podcast_title"], args.podcast)

    # 3. 确定集数编号
    ep_num = args.ep.zfill(3) if args.ep else _extract_ep_num(episode["title"])

    # 4. 转录
    print("\n🎙️  开始转录...")
    transcript_id = submit_transcription(episode["audio_url"])
    result = wait_for_transcript(transcript_id)
    transcript = rebuild_transcript(result.get("utterances") or [])
    seg_count = len([l for l in transcript.splitlines() if l.startswith("**spk")])
    print(f"   转录完成，共 {seg_count} 个说话段落")

    # 5. 生成内容
    if args.no_llm:
        generated = _empty_sections()
    else:
        generated = generate_content(episode, transcript)

    # 6. 组装并写入
    base_dir = Path(args.vault_root) / args.base_dir
    content = build_markdown(episode, transcript, generated, ep_num, args.host)

    clean_title = _clean_filename(episode["title"], ep_num)
    filename = f"{ep_num}-{clean_title}.md" if ep_num else f"{clean_title}.md"

    dest = write_to_vault(content, base_dir, podcast_dir, filename)

    print(f"\n✅ 已写入：{dest}")
    print("\n📋 下一步：")
    print("   1. 在文件中全局替换 spk1/spk2 → 真实说话人名")
    print("   2. 补充 frontmatter 的 host 和 tags")
    if args.no_llm:
        print("   3. 手动补写导读/章节速览/要点回顾")
    else:
        print("   3. 检查 AI 生成的导读是否准确，按需微调")


if __name__ == "__main__":
    main()
