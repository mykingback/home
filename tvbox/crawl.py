#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox 接口每日整理（双源）
来源：
  A: https://526900.pages.dev/p/Sb3e96Z0（TVBox 接口中心）
  B: https://tvbox.shenzjd.com/（TvBox 资源导航）
做法：
  1. 同时抓取两个站：A 站解析内嵌的 vodData（点播）与 liveData（直播）；
     B 站解析首页卡片，🔌 TVBox 接口配置 → 点播，📡 直播源 → 直播
  2. 按地址去重：地址（归一化后）已有的跳过，没有的追加；
     同名的新地址并入该接口的镜像列表
  3. 对每个接口的多个镜像地址逐个测活（HTTP 200 + 有效 TVBox 配置/M3U/TXT）
  4. 每个接口选第一个可用的镜像作为首选地址，按名称、分类整理输出
  5. 输出：vod.txt / live.txt / interfaces.json / README.md
用法：
  python tvbox/crawl.py --out tvbox [--workers 10]
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
from urllib.parse import quote, unquote, urlparse

import requests

SOURCE_A = "https://526900.pages.dev/p/Sb3e96Z0"
SOURCE_B = "https://tvbox.shenzjd.com/"
SOURCE_NAMES = {"A": SOURCE_A, "B": SOURCE_B}

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


def norm_url(u):
    """归一化地址，用于去重：scheme/host 小写，路径统一百分号编码，去末尾斜杠。
    中文与 %XX 形式会归一成同一个地址。"""
    u = u.strip()
    p = urlparse(u)
    scheme = p.scheme.lower()
    host = p.netloc.lower()
    path = quote(unquote(p.path), safe="/:@&=%+$,;~*'()!")
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    q = p.query
    return f"{scheme}://{host}{path}" + (f"?{q}" if q else "")


# ---------------- 来源 A：526900.pages.dev ----------------

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


def parse_entries_a(body, source):
    """解析 A 站 { name: "...", field: "url", ... } 对象列表"""
    entries = []
    for m in re.finditer(r"\{\s*name:\s*\"([^\"]+)\"(.*?)\}", body, re.S):
        name = m.group(1)
        rest = m.group(2)
        fields = dict(re.findall(r"(\w+):\s*\"([^\"]*)\"", rest))
        entries.append({"name": name, "fields": fields, "source": source})
    return entries


def parse_source_a():
    page = fetch_page(SOURCE_A)
    print(f"A 站页面 {len(page)} 字节")
    vod = parse_entries_a(extract_array(page, "vodData"), "A")
    live = parse_entries_a(extract_array(page, "liveData"), "A")
    print(f"A 站：点播 {len(vod)} 个，直播 {len(live)} 个")
    return vod, live


# ---------------- 来源 B：tvbox.shenzjd.com ----------------

def parse_source_b():
    page = fetch_page(SOURCE_B)
    print(f"B 站页面 {len(page)} 字节")
    heads = [(m.start(), m.group(1)) for m in
             re.finditer(r"<h[123][^>]*>([^<]{2,30})</h[123]>", page)]
    vod, live = [], []
    for m in re.finditer(
            r'href="/source/(\d+)">([^<]+)</a>.*?<button[^>]*class="[^"]*__url"[^>]*>([^<]+)</button>',
            page, re.S):
        pos, sid, name, url = m.start(), m.group(1), m.group(2), m.group(3).strip()
        section = "?"
        for hpos, hname in heads:
            if hpos < pos:
                section = hname
            else:
                break
        entry = {"name": name, "fields": {"url": url}, "source": "B"}
        if "接口配置" in section:
            vod.append(entry)
        elif "直播源" in section:
            live.append(entry)
        # 其他分区（软件下载等）不是接口，跳过
    print(f"B 站：点播 {len(vod)} 个，直播 {len(live)} 个")
    return vod, live


# ---------------- 测活 ----------------

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


def _txt_channel_count(text: str) -> int:
    """TXT 直播源（名称,地址 每行）里不同的频道地址数"""
    urls = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"[,，]", line, maxsplit=1)
        if len(parts) == 2:
            u = parts[1].strip()
            if u.startswith("http://") or u.startswith("https://"):
                urls.add(u.split("?")[0])
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
            # TXT 直播源：名称,地址 的行
            n = _txt_channel_count(text)
            if n >= 5:
                return "alive", f"TXT 直播源（{n} 个频道）"
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


# ---------------- 合并 ----------------

def merge_entries(a_entries, b_entries):
    """双源合并。a_entries（A 站）为基准；b_entries（B 站）按地址去重：
    地址已有的跳过；同名的新地址并入该接口的镜像；新名字追加为新接口。
    返回 (合并后条目, 跳过数, 并入镜像数, 新增接口数)。"""
    by_name = {}
    url_seen = {}
    merged = []
    for e in a_entries:
        merged.append(e)
        by_name[e["name"]] = e
        for key, url in e["fields"].items():
            if url:
                url_seen[norm_url(url)] = (e["name"], key)
    skipped = 0
    merged_mirror = 0
    added = 0
    for e in b_entries:
        url = e["fields"].get("url", "")
        if not url:
            continue
        if norm_url(url) in url_seen:
            skipped += 1
            continue
        if e["name"] in by_name:
            # 同名新地址：并入镜像列表
            target = by_name[e["name"]]
            target["fields"][f"b_mirror_{len(target['fields'])}"] = url
            target.setdefault("b_mirror_sources", {})[f"b_mirror_{len(target['fields']) - 1}"] = "B"
            url_seen[norm_url(url)] = (e["name"], "b_mirror")
            merged_mirror += 1
        else:
            merged.append(e)
            by_name[e["name"]] = e
            url_seen[norm_url(url)] = (e["name"], "url")
            added += 1
    return merged, skipped, merged_mirror, added


def process(entries, category, workers):
    """对一批接口测活，选首选地址。返回整理后的记录列表。"""
    jobs = []
    for e in entries:
        mirrors = []
        for key in MIRROR_ORDER + ["url"]:
            if key in e["fields"] and e["fields"][key]:
                mirrors.append((key, e["fields"][key], e["source"]))
        # B 站并入的额外镜像
        for key, url in sorted(e["fields"].items()):
            if key.startswith("b_mirror_"):
                mirrors.append((key, url, "B"))
        jobs.append((e["name"], mirrors))

    results = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {}
        for name, mirrors in jobs:
            for key, url, src in mirrors:
                futs[pool.submit(check_url_retry, url)] = (name, key, url, src)
        for fut in as_completed(futs):
            name, key, url, src = futs[fut]
            try:
                status, detail = fut.result()
            except Exception as exc:
                status, detail = "unverified", f"检测异常：{exc}"
            label = MIRROR_LABEL.get(key, "shenzjd 补充")
            results.setdefault(name, []).append(
                {"key": key, "label": label, "url": url, "status": status,
                 "detail": detail, "source": src})

    out = []
    for name, mirrors in jobs:
        tested = results.get(name, [])
        # 按镜像优先级排序：A 站原有顺序优先，B 站补充镜像排最后
        order = {k: i for i, k in enumerate(MIRROR_ORDER + ["url"])}
        tested.sort(key=lambda x: order.get(x["key"], 90))
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
        sources = sorted({t["source"] for t in tested})
        out.append({
            "name": name,
            "category": category,
            "primary": primary["url"] if primary else None,
            "primary_label": primary["label"] if primary else None,
            "primary_status": primary["status"] if primary else "dead",
            "sources": sources,
            "mirrors": tested,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tvbox")
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()

    now = datetime.now(timezone.utc).astimezone()
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")

    a_vod, a_live = parse_source_a()
    b_vod, b_live = parse_source_b()

    vod, vod_skip, vod_mirror, vod_add = merge_entries(a_vod, b_vod)
    live, live_skip, live_mirror, live_add = merge_entries(a_live, b_live)
    print(f"合并：点播跳过重复地址 {vod_skip}，并入同名镜像 {vod_mirror}，"
          f"新增接口 {vod_add}；直播跳过 {live_skip}，并入 {live_mirror}，新增 {live_add}")
    print(f"合并后：点播 {len(vod)} 个接口，直播 {len(live)} 个接口")

    vod_out = process(vod, "点播", args.workers)
    live_out = process(live, "直播", args.workers)

    vod_alive = sum(1 for x in vod_out if x["primary_status"] == "alive")
    vod_unver = sum(1 for x in vod_out if x["primary_status"] == "unverified_primary")
    live_alive = sum(1 for x in live_out if x["primary_status"] == "alive")
    live_unver = sum(1 for x in live_out if x["primary_status"] == "unverified_primary")
    print(f"点播：{vod_alive} 可用，{vod_unver} 未验证，"
          f"{len(vod_out) - vod_alive - vod_unver} 全死")
    print(f"直播：{live_alive} 可用，{live_unver} 未验证，"
          f"{len(live_out) - live_alive - live_unver} 全死")

    os.makedirs(args.out, exist_ok=True)

    def write_txt(path, items, title):
        listed = [x for x in items if x["primary"]]
        lines = [f"# {title}", f"# 来源：{SOURCE_A} / {SOURCE_B}",
                 f"# 更新时间：{stamp}（每天自动更新）",
                 f"# 本次可用：{len(listed)} 个（两站合计 {len(items)} 个，全死的没列进来）",
                 "# 格式：名称,接口地址（直接粘贴到 TVBox 里用）", ""]
        for x in listed:
            mark = "" if x["primary_status"] == "alive" else "（未验证）"
            lines.append(f"{x['name']},{x['primary']}{mark}")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    write_txt(os.path.join(args.out, "vod.txt"), vod_out, "TVBox 点播接口")
    write_txt(os.path.join(args.out, "live.txt"), live_out, "TVBox 直播接口")

    data = {
        "sources": [SOURCE_A, SOURCE_B],
        "updated_at": stamp,
        "counts": {
            "vod_total": len(vod_out), "vod_alive": vod_alive,
            "vod_unverified": vod_unver,
            "live_total": len(live_out), "live_alive": live_alive,
            "live_unverified": live_unver,
            "dedup_skipped": vod_skip + live_skip,
            "added_from_b": vod_add + live_add,
        },
        # 镜像用紧凑数组 [名称, 地址, 状态, 备注, 来源站]，文件小、推得动
        "vod": [{**x, "mirrors": [[m["label"], m["url"], m["status"],
                                    m["detail"], m["source"]]
                                   for m in x["mirrors"]]}
                for x in vod_out],
        "live": [{**x, "mirrors": [[m["label"], m["url"], m["status"],
                                     m["detail"], m["source"]]
                                    for m in x["mirrors"]]}
                 for x in live_out],
    }
    with open(os.path.join(args.out, "interfaces.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    dead_vod = [x["name"] for x in vod_out if x["primary_status"] == "dead"]
    dead_live = [x["name"] for x in live_out if x["primary_status"] == "dead"]
    unver_vod = [x["name"] for x in vod_out if x["primary_status"] == "unverified_primary"]
    unver_live = [x["name"] for x in live_out if x["primary_status"] == "unverified_primary"]
    new_from_b = ([x["name"] for x in vod_out if "B" in x["sources"] and x["name"] not in
                   {e["name"] for e in a_vod}] +
                  [x["name"] for x in live_out if "B" in x["sources"] and x["name"] not in
                   {e["name"] for e in a_live}])

    readme = f"""# TVBox 接口整理

来源（每天自动抓取两个站，按地址去重、新的追加）：

- A 站：[{SOURCE_A}]({SOURCE_A})（TVBox 接口中心）
- B 站：[{SOURCE_B}]({SOURCE_B})（TvBox 资源导航）

每天自动抓取、测活、整理。任一站的接口有增减或换地址时，这里会自动跟着变。

- **更新时间：{stamp}**
- **点播接口：{len(vod_out)} 个**（测活通过 {vod_alive} 个，未验证 {vod_unver} 个）
- **直播接口：{len(live_out)} 个**（测活通过 {live_alive} 个，未验证 {live_unver} 个）
- **本次 B 站新追加：{len(new_from_b)} 个**（地址在 A 站没有的）

## 直链（直接粘贴到 TVBox 里用）

- 点播：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/vod.txt`
- 直播：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/live.txt`
- 完整数据（含全部镜像地址与测活状态）：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/interfaces.json`

## 文件说明

- `vod.txt` / `live.txt`：`名称,接口地址`，每行一个接口，首选地址是测活通过的镜像
- `interfaces.json`：每个接口的全部镜像地址、测活状态、来源站、备注

## 注意

- “未验证”是指本次抓取的机器连不上该地址（可能是网络限制），不等于死了；在你自己的网络或电视上可能能用，标出来是提醒你先试一下
- 全死的接口不会出现在 txt 里，只在 interfaces.json 里有记录
- 测活只看接口能不能打开、是不是有效的 TVBox 配置，不保证里面每个源都能播

## 本次状态

- B 站新追加的接口：{("、".join(new_from_b) if new_from_b else "无")}
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
