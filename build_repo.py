#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Sileo 越狱源（flat repo）的索引与元数据。

用法:
    python build_repo.py https://your-domain.com

改完域名重跑即可，Packages / Release / Depiction 里的 URL 会全部跟着更新。
"""

import bz2
import gzip
import hashlib
import io
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEB = "com.codex.autoflow_0.1.0_iphoneos-arm64.deb"

REPO_NAME = "AutoFlow"
REPO_DESC = "AutoFlow 私有测试源"


def read_control(deb_path: Path) -> dict:
    """从 .deb (ar 归档) 里读出 control 字段。"""
    data = deb_path.read_bytes()
    if data[:8] != b"!<arch>\n":
        raise SystemExit(f"{deb_path.name} 不是合法的 ar 归档")

    off = 8
    while off < len(data) - 1:
        hdr = data[off:off + 60]
        if len(hdr) < 60:
            break
        name = hdr[0:16].decode(errors="replace").strip()
        size = int(hdr[48:58].decode().strip())
        body = data[off + 60:off + 60 + size]
        off += 60 + size + (size % 2)

        if name.startswith("control.tar"):
            tf = tarfile.open(fileobj=io.BytesIO(body))
            for m in tf.getmembers():
                if Path(m.name).name == "control":
                    txt = tf.extractfile(m).read().decode("utf-8", "replace")
                    fields = {}
                    key = None
                    for line in txt.splitlines():
                        if line[:1] in (" ", "\t") and key:
                            fields[key] += "\n" + line
                        elif ":" in line:
                            key, _, val = line.partition(":")
                            key = key.strip()
                            fields[key] = val.strip()
                    return fields
    raise SystemExit("没找到 control 文件")


def hashes(data: bytes) -> dict:
    return {
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def build_packages(root: Path, base: str) -> list:
    """扫描目录下所有 .deb，生成 Packages 索引文本 + 文件名列表。"""
    debs = sorted(root.glob("*.deb"))
    if not debs:
        raise SystemExit(f"{root} 下没有 .deb 文件")

    stanzas = []
    for deb in debs:
        raw = deb.read_bytes()
        ctl = read_control(deb)
        h = hashes(raw)

        order = [
            "Package", "Name", "Version", "Architecture", "Description",
            "Section", "Maintainer", "Author", "Depends", "Installed-Size",
        ]
        lines = []
        for k in order:
            if k in ctl:
                lines.append(f"{k}: {ctl[k]}")
        for k, v in ctl.items():          # 保留 control 里的其他自定义字段
            if k not in order:
                lines.append(f"{k}: {v}")

        pkg = ctl["Package"]

        lines += [
            f"Filename: ./{deb.name}",
            f"Size: {len(raw)}",
            f"MD5sum: {h['md5']}",
            f"SHA1: {h['sha1']}",
            f"SHA256: {h['sha256']}",
            f"Depiction: {base}/depictions/{pkg}.html",
            f"SileoDepiction: {base}/depictions/{pkg}.html",
            f"Homepage: {base}/",
        ]
        stanzas.append("\n".join(lines))

    return stanzas


def build_release(base: str, files: dict) -> str:
    """生成 Release 文件；files = {文件名: bytes}。"""
    out = [
        f"Origin: {REPO_NAME}",
        f"Label: {REPO_NAME}",
        f"Suite: stable",
        f"Version: 1.0",
        f"Codename: ios",
        f"Architectures: iphoneos-arm64",
        f"Components: main",
        f"Description: {REPO_DESC}",
    ]
    for algo, label in (("md5", "MD5Sum"), ("sha1", "SHA1"), ("sha256", "SHA256")):
        out.append(f"{label}:")
        for name, blob in files.items():
            out.append(f" {hashlib.new(algo, blob).hexdigest()} {len(blob)} {name}")
    return "\n".join(out) + "\n"


DEPICTION = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>AutoFlow</title>
<style>
  :root {
    --bg:#000; --card:#1c1c1e; --line:#2c2c2e;
    --fg:#f2f2f7; --dim:#8e8e93; --accent:#0a84ff;
  }
  @media (prefers-color-scheme: light) {
    :root { --bg:#f2f2f7; --card:#fff; --line:#e5e5ea; --fg:#1c1c1e; --dim:#6c6c70; }
  }
  * { box-sizing:border-box; }
  body {
    margin:0; padding:24px 20px 48px;
    background:var(--bg); color:var(--fg);
    font:16px/1.55 -apple-system,"SF Pro Text","PingFang SC",system-ui,sans-serif;
  }
  .wrap { max-width:640px; margin:0 auto; }
  header { text-align:center; padding:16px 0 28px; }
  .icon {
    width:88px; height:88px; margin:0 auto 14px; border-radius:20px;
    background:linear-gradient(160deg,#0a84ff,#0040a0);
    display:flex; align-items:center; justify-content:center;
    font-size:34px; font-weight:700; color:#fff; letter-spacing:-1px;
    box-shadow:0 8px 24px rgba(10,132,255,.35);
  }
  h1 { margin:0 0 4px; font-size:26px; letter-spacing:-.4px; }
  .sub { color:var(--dim); font-size:14px; margin:0; }
  .card {
    background:var(--card); border:1px solid var(--line);
    border-radius:14px; padding:16px 18px; margin-bottom:14px;
  }
  .card h2 {
    margin:0 0 10px; font-size:13px; font-weight:600;
    text-transform:uppercase; letter-spacing:.6px; color:var(--dim);
  }
  .row {
    display:flex; justify-content:space-between; gap:16px;
    padding:7px 0; border-bottom:1px solid var(--line); font-size:15px;
  }
  .row:last-child { border-bottom:0; }
  .row .k { color:var(--dim); flex:0 0 auto; }
  .row .v { text-align:right; word-break:break-all; }
  code {
    font:13px/1.5 ui-monospace,"SF Mono",Menlo,monospace;
    background:rgba(127,127,127,.16); padding:2px 6px; border-radius:5px;
  }
  pre {
    background:rgba(127,127,127,.12); border-radius:10px;
    padding:12px 14px; overflow-x:auto; margin:10px 0 0;
    font:13px/1.6 ui-monospace,"SF Mono",Menlo,monospace;
  }
  pre code { background:none; padding:0; }
  .note {
    border-left:3px solid var(--accent); padding:10px 0 10px 14px;
    color:var(--dim); font-size:14px; margin:0;
  }
  ol,ul { margin:0; padding-left:22px; }
  li { margin-bottom:7px; }
  a { color:var(--accent); }
  footer { text-align:center; color:var(--dim); font-size:12px; margin-top:28px; }
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="icon">AF</div>
    <h1>AutoFlow</h1>
    <p class="sub">本地手势录制与宏回放 &middot; Dopamine rootless</p>
  </header>

  <div class="card">
    <h2>软件包信息</h2>
    <div class="row"><span class="k">标识</span><span class="v"><code>com.codex.autoflow</code></span></div>
    <div class="row"><span class="k">版本</span><span class="v">0.1.0</span></div>
    <div class="row"><span class="k">架构</span><span class="v">iphoneos-arm64</span></div>
    <div class="row"><span class="k">分区</span><span class="v">Tweaks</span></div>
    <div class="row"><span class="k">适用</span><span class="v">iOS 15.0+ / 无根越狱</span></div>
  </div>

  <div class="card">
    <h2>依赖</h2>
    <ul>
      <li><code>ElleKit</code> &mdash; 请先在 Sileo 中安装并更新</li>
      <li><code>RocketBootstrap</code> &mdash; 标识 <code>com.rpetrich.rocketbootstrap</code></li>
    </ul>
  </div>

  <div class="card">
    <h2>安装</h2>
    <ol>
      <li>安装上面的两个依赖</li>
      <li>在本页安装 AutoFlow</li>
      <li>安装完成后执行 <code>sbreload</code>（或重启用户空间）</li>
    </ol>
    <p class="note" style="margin-top:12px">安装过程中请不要打开银行、支付或密码管理类 App。</p>
  </div>

  <div class="card">
    <h2>紧急停止</h2>
    <p style="margin:0">任何时候在 1.25 秒内连续按三次<b>音量加</b>，立即中止回放。</p>
  </div>

  <div class="card">
    <h2>卸载</h2>
    <pre><code>sudo dpkg -r com.codex.autoflow
sbreload</code></pre>
  </div>

  <footer>
    AutoFlow 0.1.0 &middot; 私有测试源，未公开分发<br>
    SHA-256 <code>{{SHA256_SHORT}}</code>
  </footer>

</div>
</body>
</html>
"""


def main() -> None:
    if len(sys.argv) > 1:
        base = sys.argv[1].rstrip("/")
    else:
        base = "https://REPLACE-WITH-YOUR-DOMAIN"
        print(f"!! 未指定域名，使用占位符：{base}", file=sys.stderr)

    debs = sorted(HERE.glob("*.deb"))
    stanzas = build_packages(HERE, base)

    # Packages / Packages.bz2 / Packages.gz
    plain = ("\n".join(stanzas) + "\n").encode("utf-8")
    bz = bz2.compress(plain, 9)
    gz = gzip.compress(plain, 9, mtime=0)

    (HERE / "Packages").write_bytes(plain)
    (HERE / "Packages.bz2").write_bytes(bz)
    (HERE / "Packages.gz").write_bytes(gz)

    (HERE / "Release").write_text(
        build_release(base, {"Packages": plain, "Packages.bz2": bz, "Packages.gz": gz}),
        encoding="utf-8",
    )

    # Depiction
    deps = HERE / "depictions"
    deps.mkdir(exist_ok=True)
    sha = hashes(debs[0].read_bytes())["sha256"]
    (deps / "com.codex.autoflow.html").write_text(
        DEPICTION.replace("{{SHA256_SHORT}}", sha[:16] + "…"), encoding="utf-8"
    )

    print(f"域名      : {base}")
    print(f"包数量    : {len(debs)}")
    for d in debs:
        print(f"  - {d.name}  ({d.stat().st_size} bytes)")
    print(f"Packages  : {len(plain)} bytes")
    print(f"Packages.bz2: {len(bz)} bytes")
    print(f"Packages.gz : {len(gz)} bytes")
    print("\n生成的源根目录:")
    for f in sorted(HERE.rglob("*")):
        if f.is_file() and f.name != Path(__file__).name:
            print(f"  {f.relative_to(HERE)}")
    print(f"\nSileo 里添加的源地址: {base}/")


if __name__ == "__main__":
    main()
