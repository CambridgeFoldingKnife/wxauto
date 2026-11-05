# -*- coding: utf-8 -*-
"""
健衡学园 · 素材库检索与解析
扫描素材库目录（docx / pdf / txt / md），按主题关键词打分排序，
输出候选清单（供流水线"自动从素材库选文"），支持提取单篇全文。

用法:
    python ingest-knowledge.py --topic "脑卒中 康复" [--limit 5]
    python ingest-knowledge.py --extract "D:/素材库/某篇.docx"
    python ingest-knowledge.py --list            # 只看素材库有多少文件
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

# Windows 控制台 UTF-8 适配（避免 GBK 编码报错）
if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

ROOT = Path(__file__).resolve().parents[4]          # wxAuto/
CONFIG_PATH = ROOT / "wx-auto-publish.config.json"
DEFAULT_MATERIAL_DIR = ROOT / "素材库"

EXTENSIONS = {".docx", ".pdf", ".txt", ".md", ".markdown"}
STOPWORDS = set("的了和与在是这那一就有对要也会被等要么为而或之其及些已并以于但可更很最把从向")

# ---------------- 文本提取 ----------------

def extract_docx(path: str) -> tuple[str, str]:
    """docx → (text, error)。zip 内 document.xml 逐段落提取 w:t，免第三方依赖。"""
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        paras = re.split(r"</w:p>", xml)
        lines = []
        for p in paras:
            text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)).strip()
            if text:
                lines.append(text)
        return "\n".join(lines), None
    except Exception as e:  # noqa: BLE001
        return "", f"docx 解析失败: {e}"


def extract_pdf(path: str) -> tuple[str, str]:
    """pdf → (text, error)。优先 pypdf；扫描件（无文字层）会提示用 pdf skill。"""
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader  # 兼容旧库名
    try:
        reader = PdfReader(path)
        pages = []
        for page in reader.pages[:50]:  # 防止超大 PDF 拖慢
            pages.append(page.extract_text() or "")
        text = "\n".join(pages)
        if len(text.strip()) < 20:
            return "", "PDF 无可提取文本（疑似扫描件），请改用 pdf skill 做 OCR"
        return text, None
    except ImportError:
        return "", "缺少 PDF 解析库，请先 pip install pypdf"
    except Exception as e:  # noqa: BLE001
        return "", f"pdf 解析失败: {e}"


def extract_text(path: str) -> tuple[str, str]:
    """按扩展名提取全文。返回 (text, error)。"""
    suffix = Path(path).suffix.lower()
    if suffix == ".docx":
        return extract_docx(path)
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix in {".txt", ".md", ".markdown"}:
        for enc in ("utf-8", "gbk", "gb18030"):
            try:
                return Path(path).read_text(encoding=enc), None
            except UnicodeDecodeError:
                continue
            except Exception as e:  # noqa: BLE001
                return "", f"读取失败: {e}"
        return "", "text 编码无法识别"
    return "", f"不支持的格式: {suffix}（支持 {sorted(EXTENSIONS)}）"


# ---------------- 检索排名 ----------------

def tokenize_topic(topic: str) -> list[str]:
    """把主题拆成检索词：保留整串作为短语，再按空白/逗号切分，过滤停用词。"""
    terms = []
    clean = topic.strip()
    if clean:
        terms.append(clean)                       # 整串短语（最高权重）
    for piece in re.split(r"[\s，,、;；]", clean):
        piece = piece.strip()
        if piece and len(piece) >= 2 and piece not in STOPWORDS and piece != clean:
            terms.append(piece)
    return terms


def score_doc(text: str, title: str, terms: list[str]) -> tuple[int, list[str]]:
    """简单词频打分：短语命中 ×3，单词命中 ×1，文件名命中额外 +3。"""
    score = 0
    matched = []
    for term in terms:
        c = text.count(term)
        weight = 3 if term == terms[0] and c >= 1 else 1
        if c > 0:
            score += c * weight
            matched.append(f"{term}×{c}")
        if term in title:
            score += 3
            matched.append(f"文件名+{term}")
    return score, matched


def excerpt(text: str, terms: list[str], limit: int = 200) -> str:
    """取首个命中词附近的片段作为摘要。"""
    pos = -1
    for term in terms:
        p = text.find(term)
        if p >= 0 and (pos < 0 or p < pos):
            pos = p
    if pos < 0:
        return text[:limit]
    start = max(0, pos - 40)
    return text[start:start + limit].replace("\n", " ")


def scan_material_dir(material_dir: Path) -> list[Path]:
    files = []
    for root, _dirs, names in os.walk(material_dir):
        for n in names:
            p = Path(root) / n
            if p.suffix.lower() in EXTENSIONS:
                files.append(p)
    return sorted(files)


# ---------------- 主逻辑 ----------------

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return cfg
        except Exception:  # noqa: BLE001
            pass
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="健衡学园素材库检索")
    parser.add_argument("--topic", help="主题关键词，如 '脑卒中 康复'")
    parser.add_argument("--extract", help="提取指定素材文件的全文")
    parser.add_argument("--limit", type=int, default=5, help="返回候选数（默认5）")
    parser.add_argument("--list", action="store_true", help="仅列出素材库文件")
    args = parser.parse_args()

    cfg = load_config()
    material_dir = Path(str(cfg.get("material_dir", ""))) if cfg.get("material_dir") and "路径" not in str(cfg.get("material_dir")) else DEFAULT_MATERIAL_DIR

    if args.extract:
        text, err = extract_text(args.extract)
        if err:
            print(json.dumps({"ok": False, "error": err}, ensure_ascii=False))
            sys.exit(1)
        print(json.dumps({"ok": True, "file": args.extract, "chars": len(text), "text": text}, ensure_ascii=False))
        sys.exit(0)

    if not material_dir.exists() or not material_dir.is_dir():
        print(json.dumps({"ok": False, "error": f"素材库目录不存在: {material_dir}。请在 wx-auto-publish.config.json 配置 material_dir。"}, ensure_ascii=False))
        sys.exit(1)

    files = scan_material_dir(material_dir)
    if args.list or not args.topic:
        print(json.dumps({"ok": True, "material_dir": str(material_dir), "total": len(files),
                          "files": [str(f) for f in files]}, ensure_ascii=False))
        sys.exit(0)

    terms = tokenize_topic(args.topic)
    results = []
    for f in files:
        text, err = extract_text(str(f))
        if err:
            results.append({"file": str(f), "name": f.name, "chars": 0, "score": 0,
                            "matches": [], "error": err, "excerpt": ""})
            continue
        score, matched = score_doc(text, f.name, terms)
        results.append({
            "file": str(f), "name": f.name, "chars": len(text),
            "score": score, "matches": matched,
            "excerpt": excerpt(text, terms),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    print(json.dumps({"ok": True, "topic": args.topic, "terms": terms,
                      "total_files": len(files), "results": results[: args.limit]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()