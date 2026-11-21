#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox 接口每日整理
来源：https://526900.pages.dev/p/Sb3e96Z0（TVBox 接口中心）
做法：
  1. 抓取该页面，解析内嵌的 vodData（点播接口）与 liveData（直播接口）
  2. 对每个接口的多个镜像地址逐个测活（HTTP 200 + 有效 TVBox 配置 JSON）
  3. 每个接口选第一个可用的镜像作为首选地址，按名称、分类整理输出
  4. 输出：vod.txt / live.txt / interfaces.json / README.md
用法：
  python tvbox/crawl.py --out tvbox [--source URL] [--workers 10]
在 GitHub Actions 里每天定时跑，改动自动提交到仓库，直链即自动更新。
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests

DEFAULT_SOURCE = "https://526900.pages.dev/p/Sb3e96Z0"

# 镜像优先级：原始线路 > 分流策略 > 全球策略 > 备份三线 > 备份四线 > 备份五线
MIRROR_ORDER = ["original", "fenliu", "quanqiu", "backup3", "backup4", "backup5"]
MIRROR_LABEL = {
    "original": "原始线路",
    "fenliu": "分流策略",
    "quanqiu": "全球策略",
    "backup3": "备份三线",
    "backup4": "备份四线",
    "backup5": "备份五线",
    "url": "唯一地址",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def fetch_page(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def extract_array(page, name):
    """按括号深度提取 const <name> = [ ... ]; 中的数组体"""
    start = page.find(f"const {name} = [")
    if start < 0:
        raise ValueError(f"页面里找不到 {name}")
    i = page.find("[", start)
    depth = 0
    j = i
    while j < len(page):
        ch = page[j]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return page[i + 1:j]
        j += 1
    raise ValueError(f"{name} 数组括号不匹配")


def parse_entries(body):
    """解析 { name: "...", field: "url", ... } 对象列表"""
    entries = []
    for m in re.finditer(r"\{\s*name:\s*\"([^\"]+)\"(.*?)\}", body, re.S):
        name = m.group(1)
        rest = m.group(2)
        fields = dict(re.findall(r"(\w+):\s*\"([^\"]*)\"", rest))
        entries.append({"name": name, "fields": fields})
    return entries


def _clean_text(raw: bytes) -> str:
    """去 BOM、去开头的 // 注释行（有的接口 JSON 带注释头），再去空白"""
    text = raw.decode("utf-8", errors="ignore")
    text = text.lstrip("\ufeff \t\r\n")
    lines = text.splitlines()
    while lines and lines[0].lstrip().startswith("//"):
        lines.pop(0)
    return "\n".join(lines).strip()


def _m3u_channel_count(text: str) -> int:
    """M3U 里不同的频道地址数（去重）。只有广告/失效条目的过期订阅只有 1 个地址。"""
    urls = set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("http://") or line.startswith("https://"):
            urls.add(line.split("?")[0])
    return len(urls)


def check_url(url, timeout=15):
    """测活一个接口地址。返回 (status, detail)，
    status: alive / dead / unverified（连不上，可能是本机网络限制，不判死刑）"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout,
                         allow_redirects=True)
        if r.status_code != 200:
            return "dead", f"HTTP {r.status_code}"
        text = _clean_text(r.content[:2 * 1024 * 1024])
        if not text:
            return "dead", "空响应"
        if text.startswith("#EXTM3U"):
            n = _m3u_channel_count(text)
            if n >= 5:
                return "alive", f"M3U 播放列表（{n} 个频道）"
            return "dead", f"M3U 只有 {n} 个有效频道（疑似过期订阅）"
        try:
            cfg = json.loads(text)
        except Exception:
            # 可能是被截断的大 JSON：开头是 { 且含 sites/lives 关键字也算
            if text.startswith("{") and ('"sites"' in text or '"lives"' in text):
                return "alive", "JSON 配置（截断读取）"
            return "dead", "不是有效 JSON"
        if isinstance(cfg, dict) and ("sites" in cfg or "lives" in cfg):
            n_sites = len(cfg.get("sites", []))
            n_lives = len(cfg.get("lives", []))
            return "alive", f"TVBox 配置（sites {n_sites}，lives {n_lives}）"
        if isinstance(cfg, dict) and cfg:
            return "dead", "JSON 但无 sites/lives"
        return "dead", "JSON 为空"
    except requests.exceptions.ConnectTimeout:
        return "unverified", "连接超时"
    except requests.exceptions.ConnectionError as e:
        return "unverified", f"连不上：{str(e)[:60]}"
    except requests.exceptions.Timeout:
        return "unverified", "请求超时"
    except requests.exceptions.RequestException as e:
        return "unverified", f"请求失败：{str(e)[:60]}"


def check_url_retry(url, timeout=15):
    """测活一次，判死刑前再重试一次（有的源不稳定，单次结果不可信）"""
    status, detail = check_url(url, timeout)
    if status == "dead":
        time.sleep(2)
        status2, detail2 = check_url(url, timeout)
        if status2 == "alive":
            return status2, detail2 + "（重试后通过）"
    return status, detail


def process(entries, category, workers):
    """对一批接口测活，选首选地址。返回整理后的记录列表。"""
    jobs = []
    for e in entries:
        mirrors = []
        for key in MIRROR_ORDER + ["url"]:
            if key in e["fields"] and e["fields"][key]:
                mirrors.append((key, e["fields"][key]))
        jobs.append((e["name"], mirrors))

    results = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {}
        for name, mirrors in jobs:
            for key, url in mirrors:
                futs[pool.submit(check_url_retry, url)] = (name, key, url)
        for fut in as_completed(futs):
            name, key, url = futs[fut]
            try:
                status, detail = fut.result()
            except Exception as exc:
                status, detail = "unverified", f"检测异常：{exc}"
            results.setdefault(name, []).append(
                {"key": key, "label": MIRROR_LABEL.get(key, key),
                 "url": url, "status": status, "detail": detail})

    out = []
    for name, mirrors in jobs:
        tested = results.get(name, [])
        # 按镜像优先级排序
        order = {k: i for i, k in enumerate(MIRROR_ORDER + ["url"])}
        tested.sort(key=lambda x: order.get(x["key"], 99))
        primary = None
        for t in tested:
            if t["status"] == "alive":
                primary = t
                break
        if primary is None:
            # 没有一个确认活的：若有未验证的，保留第一个未验证的作首选（用户自己网络上可能通）
            for t in tested:
                if t["status"] == "unverified":
                    primary = dict(t)
                    primary["status"] = "unverified_primary"
                    break
        out.append({
            "name": name,
            "category": category,
            "primary": primary["url"] if primary else None,
            "primary_label": primary["label"] if primary else None,
            "primary_status": primary["status"] if primary else "dead",
            "mirrors": tested,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tvbox")
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()

    now = datetime.now(timezone.utc).astimezone()
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] 抓取 {args.source}")
    page = fetch_page(args.source)
    print(f"页面 {len(page)} 字节")

    vod_entries = parse_entries(extract_array(page, "vodData"))
    live_entries = parse_entries(extract_array(page, "liveData"))
    print(f"点播接口 {len(vod_entries)} 个，直播接口 {len(live_entries)} 个")

    vod = process(vod_entries, "点播", args.workers)
    live = process(live_entries, "直播", args.workers)

    vod_alive = sum(1 for x in vod if x["primary_status"] == "alive")
    vod_unver = sum(1 for x in vod if x["primary_status"] == "unverified_primary")
    live_alive = sum(1 for x in live if x["primary_status"] == "alive")
    live_unver = sum(1 for x in live if x["primary_status"] == "unverified_primary")
    print(f"点播：{vod_alive} 可用，{vod_unver} 未验证，"
          f"{len(vod) - vod_alive - vod_unver} 全死")
    print(f"直播：{live_alive} 可用，{live_unver} 未验证，"
          f"{len(live) - live_alive - live_unver} 全死")

    os.makedirs(args.out, exist_ok=True)

    def write_txt(path, items, title):
        listed = [x for x in items if x["primary"]]
        lines = [f"# {title}", f"# 来源：{args.source}",
                 f"# 更新时间：{stamp}（每天自动更新）",
                 f"# 本次可用：{len(listed)} 个（源站共 {len(items)} 个，全死的没列进来）",
                 "# 格式：名称,接口地址（直接粘贴到 TVBox 里用）", ""]
        for x in listed:
            if x["primary"]:
                mark = "" if x["primary_status"] == "alive" else "（未验证）"
                lines.append(f"{x['name']},{x['primary']}{mark}")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    write_txt(os.path.join(args.out, "vod.txt"), vod, "TVBox 点播接口")
    write_txt(os.path.join(args.out, "live.txt"), live, "TVBox 直播接口")

    data = {
        "source": args.source,
        "updated_at": stamp,
        "counts": {
            "vod_total": len(vod), "vod_alive": vod_alive,
            "vod_unverified": vod_unver,
            "live_total": len(live), "live_alive": live_alive,
            "live_unverified": live_unver,
        },
        "vod": vod,
        "live": live,
    }
    with open(os.path.join(args.out, "interfaces.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    dead_vod = [x["name"] for x in vod if x["primary_status"] == "dead"]
    dead_live = [x["name"] for x in live if x["primary_status"] == "dead"]
    unver_vod = [x["name"] for x in vod if x["primary_status"] == "unverified_primary"]
    unver_live = [x["name"] for x in live if x["primary_status"] == "unverified_primary"]

    readme = f"""# TVBox 接口整理

来源：[{args.source}]({args.source})（TVBox 接口中心）

每天自动抓取、测活、整理。接口有增减或换地址时，这里会自动跟着变。

- **更新时间：{stamp}**
- **点播接口：{len(vod)} 个**（测活通过 {vod_alive} 个，未验证 {vod_unver} 个）
- **直播接口：{len(live)} 个**（测活通过 {live_alive} 个，未验证 {live_unver} 个）

## 直链（直接粘贴到 TVBox 里用）

- 点播：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/vod.txt`
- 直播：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/live.txt`
- 完整数据（含全部镜像地址与测活状态）：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/interfaces.json`

## 文件说明

- `vod.txt` / `live.txt`：`名称,接口地址`，每行一个接口，首选地址是测活通过的镜像
- `interfaces.json`：每个接口的全部镜像地址、测活状态、备注

## 注意

- “未验证”是指本次抓取的机器连不上该地址（可能是网络限制），不等于死了；在你自己的网络或电视上可能能用，标出来是提醒你先试一下
- 全死的接口不会出现在 txt 里，只在 interfaces.json 里有记录
- 测活只看接口能不能打开、是不是有效的 TVBox 配置，不保证里面每个源都能播

## 本次状态

- 全死的点播接口：{("、".join(dead_vod) if dead_vod else "无")}
- 全死的直播接口：{("、".join(dead_live) if dead_live else "无")}
- 未验证的点播接口：{("、".join(unver_vod) if unver_vod else "无")}
- 未验证的直播接口：{("、".join(unver_live) if unver_live else "无")}
"""
    with open(os.path.join(args.out, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)

    print(f"写出：{args.out}/vod.txt、live.txt、interfaces.json、README.md")
    print(json.dumps(data["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
