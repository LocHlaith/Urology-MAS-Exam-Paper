from __future__ import annotations

import csv
import hashlib
import json
import posixpath
import re
import shutil
import subprocess
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional preview dependency
    Image = None


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}


PREFERRED_SLUGS = {
    "Figure 统一参数.docx": "figure_unified_parameters",
    "PPT作图——3张.pptx": "ppt_three_figures",
    "作图-1.0.docx": "plot_requirements_v1_0",
    "浙江大学邵逸夫医院泌尿外科出科考考试蓝图.docx": "exam_blueprint",
    "试卷作答情况 - 2.xlsx": "exam_responses_2",
    "试卷作答情况.xlsx": "exam_responses",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def rel_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ascii_slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.replace("&", " and ")
    text = "".join(ch if ord(ch) < 128 else "_" for ch in text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return text or "source"


def source_slug(path: Path) -> str:
    return PREFERRED_SLUGS.get(path.name, ascii_slug(path.stem))


def unique_path(directory: Path, base: str, suffix: str, used: set[Path]) -> Path:
    candidate = directory / f"{base}{suffix}"
    i = 2
    while candidate in used:
        candidate = directory / f"{base}_{i}{suffix}"
        i += 1
    used.add(candidate)
    return candidate


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def package_text(el: ET.Element) -> str:
    parts: list[str] = []
    for node in el.iter():
        tag = local_name(node.tag)
        if tag == "t":
            parts.append(node.text or "")
        elif tag == "tab":
            parts.append("\t")
        elif tag in {"br", "cr"}:
            parts.append("\n")
    return "".join(parts)


def markdown_escape_cell(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", "<br>")


def markdown_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    header = "| " + " | ".join(markdown_escape_cell(v) for v in padded[0]) + " |"
    sep = "| " + " | ".join("---" for _ in range(width)) + " |"
    body = ["| " + " | ".join(markdown_escape_cell(v) for v in row) + " |" for row in padded[1:]]
    return "\n".join([header, sep, *body])


def source_preamble(
    source: Path,
    repo_root: Path,
    conversion: str,
    sha: str,
    *,
    include_original_extract: bool = True,
    agent_rule: str | None = None,
) -> str:
    source_rel = rel_path(source, repo_root)
    generated_at = datetime.now().isoformat(timespec="seconds")
    rule = agent_rule or (
        "treat the section named `Original Extract` as source material. "
        "Do not infer missing statistics, panel labels, sample sizes, or figure styles from this file."
    )
    text = (
        f"# Converted source: `{source_rel}`\n\n"
        "## Conversion metadata\n\n"
        f"- Source path: `{source_rel}`\n"
        f"- Source SHA256: `{sha}`\n"
        f"- Generated at: `{generated_at}`\n"
        f"- Conversion method: {conversion}\n"
        f"- Agent rule: {rule}\n\n"
    )
    if include_original_extract:
        text += "## Original Extract\n\n"
    return text


def docx_fallback_markdown(source: Path) -> str:
    blocks: list[str] = []
    with zipfile.ZipFile(source) as z:
        tree = ET.fromstring(z.read("word/document.xml"))
        body = tree.find("w:body", NS)
        if body is None:
            return ""
        for child in body:
            tag = local_name(child.tag)
            if tag == "p":
                text = package_text(child).strip()
                if text:
                    blocks.append(text)
            elif tag == "tbl":
                rows: list[list[str]] = []
                for tr in child.findall("w:tr", NS):
                    row = []
                    for tc in tr.findall("w:tc", NS):
                        cell_text = "\n".join(line.strip() for line in package_text(tc).splitlines() if line.strip())
                        row.append(cell_text)
                    rows.append(row)
                table = markdown_table(rows)
                if table:
                    blocks.append(table)
    return "\n\n".join(blocks) + "\n"


def convert_docx(source: Path, docs_dir: Path, repo_root: Path, seq: int, used: set[Path]) -> dict:
    sha = sha256_file(source)
    out_path = unique_path(docs_dir, f"{seq:02d}_{source_slug(source)}", ".md", used)
    conversion = "pandoc docx -> GitHub-Flavored Markdown (`--wrap=none`)"
    try:
        result = subprocess.run(
            [
                "pandoc",
                "--from=docx",
                "--to=gfm",
                "--wrap=none",
                "--markdown-headings=atx",
                str(source),
            ],
            check=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        body = result.stdout.strip() + "\n"
    except Exception as exc:
        conversion = f"Office XML fallback extraction because pandoc failed: {type(exc).__name__}: {exc}"
        body = docx_fallback_markdown(source)
    write_text(out_path, source_preamble(source, repo_root, conversion, sha) + body)
    return {
        "source_path": rel_path(source, repo_root),
        "source_type": "docx",
        "sha256": sha,
        "size_bytes": source.stat().st_size,
        "outputs": [rel_path(out_path, repo_root)],
        "conversion": conversion,
    }


def parse_relationships(z: zipfile.ZipFile, rels_part: str) -> dict[str, dict[str, str]]:
    if rels_part not in z.namelist():
        return {}
    tree = ET.fromstring(z.read(rels_part))
    rels = {}
    for rel in tree:
        if local_name(rel.tag) == "Relationship":
            rels[rel.attrib["Id"]] = {
                "target": rel.attrib.get("Target", ""),
                "type": rel.attrib.get("Type", ""),
                "mode": rel.attrib.get("TargetMode", "Internal"),
            }
    return rels


def resolve_package_target(part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(part), target))


def ppt_shape_texts(tree: ET.Element) -> list[dict[str, object]]:
    shapes: list[dict[str, object]] = []
    for sp in tree.findall(".//p:sp", NS):
        tx_body = sp.find("p:txBody", NS)
        if tx_body is None:
            continue
        cnv = sp.find("p:nvSpPr/p:cNvPr", NS)
        paras = [package_text(p).strip("\n") for p in tx_body.findall("a:p", NS)]
        paras = [p for p in paras if p.strip()]
        if not paras:
            continue
        shapes.append(
            {
                "shape_id": cnv.attrib.get("id", "") if cnv is not None else "",
                "shape_name": cnv.attrib.get("name", "") if cnv is not None else "",
                "paragraphs": paras,
            }
        )
    return shapes


def ppt_tables(tree: ET.Element) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    for tbl in tree.findall(".//a:tbl", NS):
        rows: list[list[str]] = []
        for tr in tbl.findall("a:tr", NS):
            row = []
            for tc in tr.findall("a:tc", NS):
                row.append(package_text(tc).strip())
            rows.append(row)
        if rows:
            tables.append(rows)
    return tables


def convert_pptx(source: Path, docs_dir: Path, assets_dir: Path, repo_root: Path, seq: int, used: set[Path]) -> dict:
    sha = sha256_file(source)
    slug = source_slug(source)
    out_path = unique_path(docs_dir, f"{seq:02d}_{slug}", ".md", used)
    media_dir = assets_dir / "ppt_media" / slug
    media_dir.mkdir(parents=True, exist_ok=True)
    outputs = [out_path]

    with zipfile.ZipFile(source) as z:
        all_media_parts = sorted(
            [name for name in z.namelist() if name.startswith("ppt/media/") and not name.endswith("/")]
        )
        slide_parts = sorted(
            [name for name in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)],
            key=lambda name: int(re.search(r"slide(\d+)\.xml$", name).group(1)),
        )
        sections: list[str] = []
        copied_media: set[str] = set()
        if all_media_parts:
            sections.append("## Package media inventory\n")
            sections.append("| Package part | Extracted asset |")
            sections.append("| --- | --- |")
            for media_part in all_media_parts:
                asset_path = media_dir / posixpath.basename(media_part)
                asset_path.write_bytes(z.read(media_part))
                outputs.append(asset_path)
                copied_media.add(media_part)
                sections.append(f"| `{media_part}` | `{rel_path(asset_path, repo_root)}` |")
            sections.append("")

        for slide_index, slide_part in enumerate(slide_parts, start=1):
            tree = ET.fromstring(z.read(slide_part))
            rels_part = f"{posixpath.dirname(slide_part)}/_rels/{posixpath.basename(slide_part)}.rels"
            rels = parse_relationships(z, rels_part)
            image_targets: list[tuple[str, str]] = []
            for blip in tree.findall(".//a:blip", NS):
                rid = blip.attrib.get(f"{{{NS['r']}}}embed") or blip.attrib.get(f"{{{NS['r']}}}link")
                if not rid or rid not in rels or rels[rid]["mode"] == "External":
                    continue
                target = resolve_package_target(slide_part, rels[rid]["target"])
                image_targets.append((rid, target))
                if target in z.namelist() and target not in copied_media:
                    asset_path = media_dir / posixpath.basename(target)
                    asset_path.write_bytes(z.read(target))
                    outputs.append(asset_path)
                    copied_media.add(target)

            raw_runs = [node.text if node.text is not None else "" for node in tree.findall(".//a:t", NS)]
            shapes = ppt_shape_texts(tree)
            tables = ppt_tables(tree)

            sections.append(f"## Slide {slide_index}\n\n- Slide XML part: `{slide_part}`\n")
            if image_targets:
                sections.append("\n### Referenced media\n\n| rId | Package part | Extracted asset |\n| --- | --- | --- |")
                for rid, target in image_targets:
                    asset_path = media_dir / posixpath.basename(target)
                    extracted = rel_path(asset_path, repo_root) if asset_path.exists() else ""
                    sections.append(f"| `{rid}` | `{target}` | `{extracted}` |")
                sections.append("")

            if shapes:
                sections.append("\n### Text boxes, paragraph-level extraction\n")
                for i, shape in enumerate(shapes, start=1):
                    sections.append(f"\n#### Text box {i}\n")
                    sections.append(f"- Shape id: `{shape['shape_id']}`")
                    sections.append(f"- Shape name: `{shape['shape_name']}`\n")
                    sections.append("```text")
                    sections.extend(str(p) for p in shape["paragraphs"])
                    sections.append("```")
            else:
                sections.append("\n### Text boxes, paragraph-level extraction\n\nNo text boxes extracted.")

            if tables:
                sections.append("\n### Tables\n")
                for i, rows in enumerate(tables, start=1):
                    sections.append(f"\n#### Table {i}\n\n{markdown_table(rows)}")

            sections.append("\n### Raw `a:t` text-run sequence\n")
            sections.append("```json")
            sections.append(json.dumps(raw_runs, ensure_ascii=False, indent=2))
            sections.append("```")

    conversion = "direct PPTX Office XML extraction; media copied without interpretation"
    write_text(out_path, source_preamble(source, repo_root, conversion, sha) + "\n".join(sections).strip() + "\n")
    return {
        "source_path": rel_path(source, repo_root),
        "source_type": "pptx",
        "sha256": sha,
        "size_bytes": source.stat().st_size,
        "outputs": [rel_path(p, repo_root) for p in outputs],
        "conversion": conversion,
    }


def col_to_num(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + ord(ch.upper()) - 64
    return n


def num_to_col(n: int) -> str:
    out = ""
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


def cell_ref_to_rc(ref: str) -> tuple[int, int]:
    m = re.fullmatch(r"([A-Z]+)(\d+)", ref)
    if not m:
        return (0, 0)
    return int(m.group(2)), col_to_num(m.group(1))


def dimension_to_bounds(ref: str) -> tuple[int, int]:
    if not ref:
        return (0, 0)
    last = ref.split(":")[-1]
    row, col = cell_ref_to_rc(last)
    return row, col


def xlsx_shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return [package_text(si) for si in tree.findall("s:si", NS)]


def xlsx_sheets(z: zipfile.ZipFile) -> list[dict[str, str]]:
    workbook = ET.fromstring(z.read("xl/workbook.xml"))
    rels = parse_relationships(z, "xl/_rels/workbook.xml.rels")
    sheets = []
    for sheet in workbook.findall(".//s:sheet", NS):
        rid = sheet.attrib.get(f"{{{NS['r']}}}id", "")
        target = rels.get(rid, {}).get("target", "")
        if target:
            target = resolve_package_target("xl/workbook.xml", target)
        sheets.append(
            {
                "name": sheet.attrib.get("name", ""),
                "sheet_id": sheet.attrib.get("sheetId", ""),
                "state": sheet.attrib.get("state", "visible"),
                "part": target,
            }
        )
    return sheets


def xlsx_cell_value(c: ET.Element, shared_strings: list[str]) -> tuple[str, str | None]:
    cell_type = c.attrib.get("t")
    formula = c.find("s:f", NS)
    formula_text = formula.text if formula is not None else None
    v = c.find("s:v", NS)
    inline = c.find("s:is", NS)
    if cell_type == "s" and v is not None:
        try:
            return shared_strings[int(v.text or "0")], formula_text
        except Exception:
            return "", formula_text
    if cell_type == "inlineStr" and inline is not None:
        return package_text(inline), formula_text
    if v is not None:
        return v.text or "", formula_text
    if formula_text:
        return f"={formula_text}", formula_text
    return "", formula_text


def convert_xlsx(source: Path, data_dir: Path, docs_dir: Path, repo_root: Path, seq: int, used: set[Path]) -> dict:
    sha = sha256_file(source)
    slug = source_slug(source)
    workbook_data_dir = data_dir / slug
    workbook_data_dir.mkdir(parents=True, exist_ok=True)
    out_path = unique_path(docs_dir, f"{seq:02d}_{slug}_workbook", ".md", used)
    outputs = [out_path]
    sheet_summaries = []

    with zipfile.ZipFile(source) as z:
        shared_strings = xlsx_shared_strings(z)
        for sheet_index, sheet in enumerate(xlsx_sheets(z), start=1):
            part = sheet["part"]
            if part not in z.namelist():
                continue
            tree = ET.fromstring(z.read(part))
            dimension_el = tree.find("s:dimension", NS)
            dimension = dimension_el.attrib.get("ref", "") if dimension_el is not None else ""
            dim_rows, dim_cols = dimension_to_bounds(dimension)
            cells: dict[tuple[int, int], str] = {}
            formula_cells: list[str] = []
            max_row = dim_rows
            max_col = dim_cols
            for c in tree.findall(".//s:sheetData/s:row/s:c", NS):
                ref = c.attrib.get("r", "")
                row, col = cell_ref_to_rc(ref)
                if row == 0 or col == 0:
                    continue
                value, formula = xlsx_cell_value(c, shared_strings)
                cells[(row, col)] = value
                max_row = max(max_row, row)
                max_col = max(max_col, col)
                if formula is not None:
                    formula_cells.append(ref)

            merge_ranges = [mc.attrib.get("ref", "") for mc in tree.findall(".//s:mergeCells/s:mergeCell", NS)]
            csv_path = workbook_data_dir / f"{sheet_index:02d}_{ascii_slug(sheet['name'])}.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                for row in range(1, max_row + 1):
                    writer.writerow([cells.get((row, col), "") for col in range(1, max_col + 1)])
            outputs.append(csv_path)

            preview_rows = []
            for row in range(1, min(max_row, 8) + 1):
                preview_rows.append([cells.get((row, col), "") for col in range(1, min(max_col, 12) + 1)])
            nonempty = sum(1 for value in cells.values() if value != "")
            sheet_summaries.append(
                {
                    "index": sheet_index,
                    "name": sheet["name"],
                    "state": sheet["state"],
                    "part": part,
                    "dimension": dimension,
                    "rows_exported": max_row,
                    "columns_exported": max_col,
                    "last_column": num_to_col(max_col) if max_col else "",
                    "nonempty_cells": nonempty,
                    "formula_cells": formula_cells,
                    "merge_ranges": merge_ranges,
                    "csv_path": rel_path(csv_path, repo_root),
                    "preview_rows": preview_rows,
                }
            )

    lines = [
        source_preamble(
            source,
            repo_root,
            "direct XLSX Office XML extraction; cell cached/raw values exported as CSV",
            sha,
            include_original_extract=False,
            agent_rule=(
                "use the CSV files as raw worksheet exports and the sheet summaries as conversion metadata/previews. "
                "Do not infer variable meanings beyond explicit source text."
            ),
        )
    ]
    lines.append("## Worksheet export summary\n")
    lines.append(
        "The CSV files preserve worksheet cell values as raw/cached text in cell order. Formulas are not evaluated "
        "and spreadsheet display formatting is not applied here; if formula cells exist, their addresses are listed below.\n"
    )
    for sheet in sheet_summaries:
        lines.append(f"## Sheet {sheet['index']}: {sheet['name']}\n")
        lines.append(f"- State: `{sheet['state']}`")
        lines.append(f"- Worksheet XML part: `{sheet['part']}`")
        lines.append(f"- Original dimension ref: `{sheet['dimension']}`")
        lines.append(f"- Exported size: `{sheet['rows_exported']} rows x {sheet['columns_exported']} columns`")
        lines.append(f"- Non-empty cells: `{sheet['nonempty_cells']}`")
        lines.append(f"- CSV: `{sheet['csv_path']}`")
        lines.append(f"- Merged ranges: `{', '.join(sheet['merge_ranges']) if sheet['merge_ranges'] else 'none'}`")
        lines.append(f"- Formula cells: `{', '.join(sheet['formula_cells']) if sheet['formula_cells'] else 'none'}`\n")
        lines.append("### Preview only: first 8 rows x first 12 columns\n")
        lines.append(markdown_table(sheet["preview_rows"]))
        lines.append("")
    write_text(out_path, "\n".join(lines).strip() + "\n")
    return {
        "source_path": rel_path(source, repo_root),
        "source_type": "xlsx",
        "sha256": sha,
        "size_bytes": source.stat().st_size,
        "outputs": [rel_path(p, repo_root) for p in outputs],
        "conversion": "direct XLSX Office XML extraction; CSV values are raw/cached text",
        "sheets": [
            {k: v for k, v in sheet.items() if k != "preview_rows"}
            for sheet in sheet_summaries
        ],
    }


def convert_tif(source: Path, docs_dir: Path, assets_dir: Path, repo_root: Path) -> dict:
    sha = sha256_file(source)
    info: dict[str, object] = {}
    outputs: list[Path] = []
    if Image is not None:
        with Image.open(source) as im:
            info = {
                "width": im.size[0],
                "height": im.size[1],
                "mode": im.mode,
                "frames": getattr(im, "n_frames", 1),
            }
            preview_dir = assets_dir / "visual_reference_previews"
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview = im.copy()
            preview.thumbnail((1600, 1600))
            if preview.mode not in {"RGB", "RGBA"}:
                preview = preview.convert("RGB")
            preview_path = preview_dir / f"{source.stem}_preview.png"
            preview.save(preview_path)
            outputs.append(preview_path)
    return {
        "source_path": rel_path(source, repo_root),
        "source_type": "tif",
        "sha256": sha,
        "size_bytes": source.stat().st_size,
        "outputs": [rel_path(p, repo_root) for p in outputs],
        "conversion": "PIL metadata extraction and downscaled PNG preview; no OCR or interpretation",
        "image_info": info,
    }


def write_visual_references_doc(entries: list[dict], docs_dir: Path, repo_root: Path) -> Path | None:
    if not entries:
        return None
    out_path = docs_dir / "visual_references.md"
    lines = [
        "# Visual reference files\n",
        "These entries are image references only. The converter records dimensions and preview paths, "
        "but does not infer style rules or read figure content from the images.\n",
        "| Source | Dimensions | Mode | Original bytes | Preview |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for entry in entries:
        info = entry.get("image_info", {})
        dims = f"{info.get('width', '?')} x {info.get('height', '?')}"
        preview = entry["outputs"][0] if entry["outputs"] else ""
        lines.append(
            f"| `{entry['source_path']}` | `{dims}` | `{info.get('mode', '')}` | {entry['size_bytes']} | `{preview}` |"
        )
    lines.append("")
    for entry in entries:
        if entry["outputs"]:
            preview_rel_from_doc = Path("..") / Path(entry["outputs"][0]).relative_to("plot/agent_readable")
            lines.append(f"## `{entry['source_path']}`\n")
            lines.append(f"![preview]({preview_rel_from_doc.as_posix()})\n")
    write_text(out_path, "\n".join(lines).strip() + "\n")
    return out_path


def write_readme(out_root: Path, repo_root: Path, manifest: list[dict]) -> None:
    readme = out_root / "README.md"
    brief = out_root / "AGENT_BRIEF.md"
    generated_at = datetime.now().isoformat(timespec="seconds")
    source_rows = "\n".join(
        f"| `{entry['source_path']}` | `{entry['source_type']}` | {', '.join(f'`{o}`' for o in entry['outputs'][:3])}{' ...' if len(entry['outputs']) > 3 else ''} |"
        for entry in manifest
    )
    write_text(
        readme,
        f"""# Agent-readable plot source package

Generated at: `{generated_at}`

This folder is a mechanical conversion of `plot/` for downstream plotting/statistics agents. It separates source text, worksheet data, visual assets, and provenance metadata.

## Contents

- `AGENT_BRIEF.md`: strict usage rules for plotting agents.
- `docs/*.md`: converted Word/PPT source text and worksheet summaries. Word/PPT files have an `Original Extract` section; workbook files are export metadata plus previews.
- `data/**/*.csv`: worksheet cell values exported from `.xlsx` files.
- `assets/ppt_media/**`: media extracted from the PPTX package.
- `assets/visual_reference_previews/**`: downscaled previews of `.tif` style references.
- `manifest.json`: source paths, SHA256 hashes, conversion methods, and output paths.
- `tools/convert_plot_sources.py`: reproducible converter.

## Source map

| Source | Type | Main outputs |
| --- | --- | --- |
{source_rows}

## Regenerate

From the repository root:

```powershell
python plot\\agent_readable\\tools\\convert_plot_sources.py
```
""",
    )
    write_text(
        brief,
        """# Agent plotting brief

## Non-negotiable rules

1. Use source wording from Word/PPT files in `docs/*` as quoted requirements, not as paraphrased interpretation.
2. Use `manifest.json` to verify which converted file came from which original file.
3. Treat worksheet CSV files as raw/cached cell exports; formulas are not evaluated and display formatting is not applied. Do not invent variable meanings beyond the workbook summaries and source documents.
4. Treat TIF previews and PPT media as visual references only unless a source text explicitly assigns them a figure requirement.
5. If a panel label, sample size, statistical model, noninferiority margin, color, font, or data source is missing or contradictory, mark it as `UNKNOWN_OR_CONFLICTING` and ask for clarification.
6. Keep `Figure 统一参数.docx`/`docs/*figure_unified_parameters.md` as the global formatting source unless a figure-specific requirement explicitly overrides it.
7. Do not treat examples, placeholder `XXX`, or fictional protocol values as real locked data.

## Recommended plotting workflow

1. Read `manifest.json` and this brief first.
2. Read `docs/*figure_unified_parameters.md` for global visual settings.
3. Read `docs/*plot_requirements_v1_0.md`, then the statistical protocol documents, before designing panels.
4. Load CSV files from `data/` with explicit filenames and sheet names. Keep a record of source workbook and sheet for every derived statistic.
5. Before producing a figure, create a small panel-to-source table: panel, source file, quoted requirement, data file/sheet, unresolved assumptions.
6. In code comments or figure metadata, cite source paths rather than relying on memory.
""",
    )


def main() -> None:
    repo_root = Path.cwd()
    source_root = repo_root / "plot"
    out_root = source_root / "agent_readable"
    docs_dir = out_root / "docs"
    data_dir = out_root / "data"
    assets_dir = out_root / "assets"
    docs_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    sources = [
        p
        for p in source_root.rglob("*")
        if p.is_file()
        and out_root not in p.parents
        and not p.name.startswith("~$")
        and p.suffix.lower() in {".docx", ".pptx", ".xlsx", ".tif", ".tiff"}
    ]
    sources.sort(key=lambda p: rel_path(p, source_root).casefold())

    manifest: list[dict] = []
    used_docs: set[Path] = set()
    doc_seq = 1
    tif_entries: list[dict] = []
    for source in sources:
        suffix = source.suffix.lower()
        if suffix == ".docx":
            manifest.append(convert_docx(source, docs_dir, repo_root, doc_seq, used_docs))
            doc_seq += 1
        elif suffix == ".pptx":
            manifest.append(convert_pptx(source, docs_dir, assets_dir, repo_root, doc_seq, used_docs))
            doc_seq += 1
        elif suffix == ".xlsx":
            manifest.append(convert_xlsx(source, data_dir, docs_dir, repo_root, doc_seq, used_docs))
            doc_seq += 1
        elif suffix in {".tif", ".tiff"}:
            entry = convert_tif(source, docs_dir, assets_dir, repo_root)
            manifest.append(entry)
            tif_entries.append(entry)

    visual_doc = write_visual_references_doc(tif_entries, docs_dir, repo_root)
    if visual_doc is not None:
        for entry in tif_entries:
            entry["outputs"].append(rel_path(visual_doc, repo_root))

    manifest_path = out_root / "manifest.json"
    write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    write_readme(out_root, repo_root, manifest)
    print(f"Converted {len(manifest)} source files into {rel_path(out_root, repo_root)}")


if __name__ == "__main__":
    main()
