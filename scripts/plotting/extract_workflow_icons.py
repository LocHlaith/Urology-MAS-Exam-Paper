#!/usr/bin/env python3
"""Extract text-free icon screenshots from the five GPT concept PNGs.

The crops are intentionally kept as small rectangular PNG snippets, matching
the user's requested tracing method.  They are source assets for
``make_workflow_panels.py`` and are never used for labels or flow connectors.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "assets" / "workflow_icons"
TRANSPARENT_PAD = 3

# name: (source, (left, top, right, bottom)) in original-image pixels.
CROPS = {
    # Figure 1A: source-specific construction and sampling icons.
    "document_human": ("1A.png", (61, 216, 145, 319)),
    "database_human": ("1A.png", (479, 226, 558, 319)),
    "database_guideline_mas": ("1A.png", (28, 532, 141, 644)),
    "funnel_teal": ("1A.png", (830, 428, 898, 506)),
    "group_gray": ("1A.png", (1368, 477, 1465, 545)),
    "lock_human": ("1A.png", (1360, 177, 1412, 241)),
    "lock_mas": ("1A.png", (1552, 182, 1601, 242)),
    "shuffle_gray": ("1A.png", (1355, 327, 1415, 382)),
    "analysis_bars_purple": ("1A.png", (1653, 579, 1735, 642)),
    "database_mas": ("1A.png", (495, 559, 561, 647)),
    "clipboard_mas": ("1A.png", (87, 555, 137, 642)),
    "document_check_mas": ("1A.png", (188, 578, 240, 654)),
    "check_mas": ("1A.png", (277, 574, 346, 660)),
    "reconstruction_mas": ("1A.png", (382, 575, 438, 654)),
    "lock_gray": ("1A.png", (968, 613, 1002, 664)),
    # Figure 1B: review, safety, and adjudication icons.
    "document_blue_tall": ("1B.png", (35, 110, 114, 231)),
    "document_red_tall": ("1B.png", (35, 362, 114, 484)),
    "machine_ochre": ("1B.png", (640, 158, 720, 230)),
    "doctor_ochre": ("1B.png", (844, 154, 932, 235)),
    "shield_teal": ("1B.png", (1305, 128, 1372, 225)),
    "shield_ochre": ("1B.png", (1108, 452, 1172, 535)),
    "gavel_teal": ("1B.png", (1430, 457, 1496, 535)),
    "clipboard_purple": ("1B.png", (42, 645, 123, 756)),
    "validation_bars_purple": ("1B.png", (416, 600, 480, 671)),
    "machine_person_teal": ("1B.png", (843, 646, 1003, 752)),
    "person_teal": ("1B.png", (940, 650, 1008, 750)),
    "clock_purple": ("1B.png", (1258, 725, 1340, 795)),
    "document_gray": ("1B.png", (1641, 268, 1708, 346)),
    # Figure 2A: blinded item set, experts, tags, and locked analysis.
    "document_human_clean": ("2A.png", (52, 184, 121, 289)),
    "document_mas_clean": ("2A.png", (52, 460, 121, 552)),
    "database_gray_locked": ("2A.png", (225, 588, 310, 670)),
    "doctor_gray": ("2A.png", (684, 178, 761, 250)),
    "clipboard_purple_clean": ("2A.png", (766, 318, 824, 373)),
    "shield_ochre_clean": ("2A.png", (764, 452, 827, 504)),
    "question_gray": ("2A.png", (768, 518, 827, 567)),
    "tag_gray": ("2A.png", (722, 622, 773, 680)),
    "cognitive_gray": ("2A.png", (970, 619, 1054, 684)),
    "database_teal_locked": ("2A.png", (1588, 151, 1686, 235)),
    "lock_teal_open": ("2A.png", (1592, 291, 1680, 379)),
    # Figure 3A: participant, examination, and analysis icons.
    "group_teal": ("3A.png", (48, 286, 166, 364)),
    "document_teal_check": ("3A.png", (1055, 322, 1108, 383)),
    "bars_teal": ("3A.png", (1048, 414, 1110, 475)),
    "target_teal": ("3A.png", (1051, 512, 1114, 568)),
    "clock_teal": ("3A.png", (1051, 602, 1115, 660)),
    "examinee_teal": ("3A.png", (1110, 184, 1226, 295)),
    "ci_purple": ("3A.png", (1480, 185, 1567, 257)),
    "bars_purple": ("3A.png", (1478, 307, 1572, 386)),
    "interaction_purple": ("3A.png", (1478, 418, 1575, 499)),
    "curve_purple": ("3A.png", (1480, 623, 1564, 686)),
    "dots_purple": ("3A.png", (1473, 719, 1557, 802)),
    "clock_gray": ("3A.png", (642, 441, 709, 511)),
    # Figure 4A: clean blinding and judgment icons.
    "tag_teal": ("4A.png", (468, 137, 520, 190)),
    "shuffle_teal": ("4A.png", (465, 222, 523, 267)),
    "lock_teal": ("4A.png", (472, 293, 514, 343)),
    "stack_gray": ("4A.png", (914, 190, 1009, 290)),
    "group_students_gray": ("4A.png", (835, 486, 1010, 575)),
}


def transparent_background(crop: Image.Image) -> Image.Image:
    """Remove the sampled card background while preserving antialiased icons."""
    rgb = np.asarray(crop.convert("RGB"), dtype=np.float32)
    border = np.concatenate(
        [rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]], axis=0
    )
    pale_border = border[np.mean(border, axis=1) > 175.0]
    if len(pale_border) == 0:
        pale_border = border
    sample_indices = np.linspace(0, len(pale_border) - 1, min(96, len(pale_border))).astype(int)
    background_palette = pale_border[sample_indices]
    pixels = rgb.reshape(-1, 3)
    distance = np.sqrt(
        np.min(
            np.sum((pixels[:, None, :] - background_palette[None, :, :]) ** 2, axis=2),
            axis=1,
        )
    ).reshape(rgb.shape[:2])
    # GPT concepts use white or pale card fills with slight spatial gradients.
    # Matching a palette sampled around the full crop boundary removes those
    # gradients while the soft matte retains antialiased icon strokes.
    alpha = np.clip((distance - 10.0) / (40.0 - 10.0), 0.0, 1.0)
    alpha[alpha < 0.08] = 0.0
    rgba = np.dstack([rgb, alpha[:, :, None] * 255.0]).astype(np.uint8)
    result = Image.fromarray(rgba, mode="RGBA")
    alpha_image = result.getchannel("A")
    bbox = alpha_image.point(lambda value: 255 if value > 5 else 0).getbbox()
    if bbox is None:
        return result
    left, top, right, bottom = bbox
    left = max(0, left - 2)
    top = max(0, top - 2)
    right = min(result.width, right + 2)
    bottom = min(result.height, bottom + 2)
    trimmed = result.crop((left, top, right, bottom))
    return ImageOps.expand(trimmed, border=TRANSPARENT_PAD, fill=(0, 0, 0, 0))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    opened: dict[str, Image.Image] = {}
    try:
        for name, (source_name, bbox) in CROPS.items():
            if source_name not in opened:
                opened[source_name] = Image.open(REPO_ROOT / source_name).convert("RGB")
            crop = transparent_background(opened[source_name].crop(bbox))
            crop.save(OUT / f"{name}.png", format="PNG", optimize=True)
            print(f"Wrote {(OUT / f'{name}.png').relative_to(REPO_ROOT)} {crop.size[0]}x{crop.size[1]}")
    finally:
        for image in opened.values():
            image.close()


if __name__ == "__main__":
    main()
