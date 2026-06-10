"""Generate the 8 title frames for the Neuron Vision V5 demo video.

Frames are rendered at 2400x1350 (16:9) so the ffmpeg zoompan in
make_video.py can push in without losing sharpness at 1920x1080.

Usage:
    python video/make_frames.py            # writes video/frames/v5_0*.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 2400, 1350
OUT = Path(__file__).parent / "frames"

# Palette
BG_TOP = (7, 11, 22)
BG_BOT = (16, 24, 48)
INK = (232, 237, 247)
DIM = (139, 150, 173)
CYAN = (56, 225, 255)
GREEN = (61, 220, 151)
AMBER = (255, 200, 87)
RED = (255, 93, 115)
PURPLE = (167, 139, 250)
CARD = (17, 24, 43)
CARD_EDGE = (44, 56, 86)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def font(size: int, *, bold: bool = True, mono: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        name = "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"
    else:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


def bg(glow_xy: tuple[int, int], glow_rgb: tuple[int, int, int]) -> Image.Image:
    """Vertical navy gradient + colored radial glow + dot grid + vignette."""
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        row = tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOT, strict=True))
        for x in range(W):
            px[x, y] = row

    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gx, gy, r = *glow_xy, 620
    gd.ellipse([gx - r, gy - r, gx + r, gy + r], fill=tuple(c // 5 for c in glow_rgb))
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    img = ImageChops.add(img, glow)

    d = ImageDraw.Draw(img)
    for x in range(80, W, 96):
        for y in range(80, H, 96):
            d.ellipse([x, y, x + 3, y + 3], fill=(255, 255, 255, 12))
    # vignette
    vmask = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vmask)
    vd.rectangle([0, 0, W, H], fill=70)
    vd.rounded_rectangle([120, 90, W - 120, H - 90], radius=200, fill=0)
    vmask = vmask.filter(ImageFilter.GaussianBlur(160))
    img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, vmask)
    return img


def glow_text(
    img: Image.Image,
    xy: tuple[int, int],
    text: str,
    f: ImageFont.FreeTypeFont,
    fill,
    glow_rgb,
    *,
    anchor="la",
) -> None:
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text(xy, text, font=f, fill=tuple(c // 2 for c in glow_rgb), anchor=anchor)
    layer = layer.filter(ImageFilter.GaussianBlur(26))
    img.paste(ImageChops.add(img, layer), (0, 0))
    ImageDraw.Draw(img).text(xy, text, font=f, fill=fill, anchor=anchor)


def kicker(d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color) -> None:
    x, y = xy
    f = font(34)
    for ch in text.upper():
        d.text((x, y), ch, font=f, fill=color)
        x += d.textlength(ch, font=f) + 12


def footer(d: ImageDraw.ImageDraw, tag: str) -> None:
    d.text((140, H - 96), "NEURON VISION · RoboQC", font=font(30), fill=DIM)
    d.text((W - 140, H - 96), tag, font=font(30, mono=True), fill=DIM, anchor="ra")


def card(d: ImageDraw.ImageDraw, box, *, radius=28, fill=CARD, edge=CARD_EDGE) -> None:
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=edge, width=3)


def arrow(d: ImageDraw.ImageDraw, x0, y0, x1, y1, color=DIM, w=6) -> None:
    d.line([x0, y0, x1, y1], fill=color, width=w)
    import math

    ang = math.atan2(y1 - y0, x1 - x0)
    for s in (-1, 1):
        d.line(
            [x1, y1, x1 - 26 * math.cos(ang + s * 0.45), y1 - 26 * math.sin(ang + s * 0.45)],
            fill=color,
            width=w,
        )


# ────────────────────────────────────────────────────────────────────────────
def frame_01_cost_stat() -> Image.Image:
    img = bg((W // 2, 480), RED)
    d = ImageDraw.Draw(img)
    kicker(d, (140, 170), "PCB quality control today", RED)
    glow_text(img, (W // 2, 530), "$500K – $1M", font(290), INK, RED, anchor="mm")
    d = ImageDraw.Draw(img)
    d.text(
        (W // 2, 760),
        "the price of ONE automated optical inspection machine",
        font=font(56, bold=False),
        fill=DIM,
        anchor="mm",
    )
    d.line([W // 2 - 420, 850, W // 2 + 420, 850], fill=CARD_EDGE, width=3)
    d.text(
        (W // 2, 960),
        "Most small electronics shops never buy one.",
        font=font(58),
        fill=INK,
        anchor="mm",
    )
    d.text(
        (W // 2, 1050),
        "They inspect by eye — and defects ship.",
        font=font(58),
        fill=AMBER,
        anchor="mm",
    )
    footer(d, "01 / 08")
    return img


def frame_02_pipeline() -> Image.Image:
    img = bg((W // 2, 300), CYAN)
    d = ImageDraw.Draw(img)
    kicker(d, (140, 150), "Architecture", CYAN)
    d.text((140, 220), "Five agents. One verdict.", font=font(96), fill=INK)

    boxes = {
        "triage": (170, 620, 560, 800),
        "solder": (820, 430, 1330, 580),
        "comp": (820, 640, 1330, 790),
        "mark": (820, 850, 1330, 1000),
        "chief": (1590, 620, 2010, 800),
    }
    labels = {
        "triage": ("TriageAgent", "what needs attention"),
        "solder": ("SolderInspector", "bridges · cold joints"),
        "comp": ("ComponentInspector", "placement · polarity"),
        "mark": ("MarkingInspector", "silkscreen · part codes"),
        "chief": ("ChiefInspector", "final verdict + evidence"),
    }
    accents = {"triage": AMBER, "solder": CYAN, "comp": CYAN, "mark": CYAN, "chief": GREEN}
    for k, b in boxes.items():
        card(d, b, edge=accents[k])
        cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
        d.text((cx, cy - 26), labels[k][0], font=font(46), fill=INK, anchor="mm")
        d.text((cx, cy + 34), labels[k][1], font=font(32, bold=False), fill=DIM, anchor="mm")

    for k in ("solder", "comp", "mark"):
        b = boxes[k]
        arrow(d, 560, 710, b[0] - 14, (b[1] + b[3]) // 2)
        arrow(d, b[2] + 6, (b[1] + b[3]) // 2, 1590 - 14, 710)

    brace = (820, 360, 1330, 1040)
    d.rounded_rectangle(brace, radius=34, outline=PURPLE, width=4)
    d.text(
        ((brace[0] + brace[2]) // 2, 1085),
        "asyncio.gather() — stage 2 runs in parallel",
        font=font(40, mono=True),
        fill=PURPLE,
        anchor="ma",
    )
    d.text(
        (W // 2, 1165),
        "Vertex AI · Gemini 2.5 Pro · us-central1",
        font=font(34, mono=True),
        fill=DIM,
        anchor="ma",
    )
    footer(d, "02 / 08")
    return img


def frame_03_demo() -> Image.Image:
    img = bg((1700, 700), GREEN)
    d = ImageDraw.Draw(img)
    kicker(d, (140, 150), "Not a slide deck", GREEN)
    d.text((140, 220), "It's live on Cloud Run.", font=font(96), fill=INK)

    # mock verdict card
    card(d, (140, 430, 1150, 1130), radius=36)
    d.rounded_rectangle([190, 490, 620, 880], radius=20, fill=(8, 40, 24), outline=GREEN, width=3)
    # PCB doodle
    for y in range(540, 860, 44):
        d.line([220, y, 590, y], fill=(28, 110, 64), width=6)
    for x in range(260, 600, 80):
        d.rectangle([x, 600, x + 36, 650], fill=(20, 70, 45), outline=(40, 150, 90))
    d.ellipse([470, 690, 540, 760], outline=RED, width=8)
    d.rounded_rectangle([660, 500, 1100, 590], radius=16, fill=(70, 18, 30), outline=RED, width=3)
    d.text((880, 545), "REJECT", font=font(54), fill=RED, anchor="mm")
    d.text((660, 640), "solder_bridge @ R12", font=font(40, mono=True), fill=INK)
    d.text((660, 710), "confidence 0.93", font=font(40, mono=True), fill=DIM)
    d.text((660, 800), "5 agents · 1 photo", font=font(40, bold=False), fill=DIM)
    d.text((660, 860), "verdict in seconds", font=font(40, bold=False), fill=DIM)

    d.text((1290, 560), "Try to break it, judges:", font=font(52), fill=INK)
    card(d, (1290, 650, 2260, 760), fill=(10, 30, 36), edge=CYAN)
    d.text(
        (1320, 705),
        "neuron-vision-display-z3mwyxcila-uc.a.run.app",
        font=font(33, mono=True),
        fill=CYAN,
        anchor="lm",
    )
    d.text((1290, 820), "Upload a board photo.", font=font(44, bold=False), fill=DIM)
    d.text((1290, 890), "Get a located, named defect.", font=font(44, bold=False), fill=DIM)
    footer(d, "03 / 08")
    return img


def frame_04_speed_compare() -> Image.Image:
    img = bg((1900, 400), CYAN)
    d = ImageDraw.Draw(img)
    kicker(d, (140, 150), "Same model · same prompts", CYAN)
    d.text((140, 220), "Parallel beats sequential.", font=font(96), fill=INK)

    x0, xmax = 460, 1950
    full = xmax - x0  # 14.1 s scale

    for sec in range(0, 15, 2):
        gx = x0 + int(full * sec / 14.1)
        d.line([gx, 520, gx, 880], fill=(50, 60, 86), width=2)
        d.text((gx, 900), f"{sec}", font=font(30, mono=True), fill=DIM, anchor="ma")

    def bar(y, sec, color, label):
        wpx = int(full * sec / 14.1)
        d.text((140, y + 42), label, font=font(44), fill=INK, anchor="lm")
        d.rounded_rectangle([x0, y, x0 + wpx, y + 84], radius=18, fill=color)
        # speed streaks
        for i in range(3):
            sx = x0 + wpx - 60 - i * 46
            if sx > x0:
                d.line(
                    [sx, y + 18 + i * 24, sx - 30, y + 18 + i * 24], fill=(255, 255, 255), width=5
                )
        d.text(
            (x0 + wpx + 36, y + 42), f"{sec} s", font=font(58, mono=True), fill=color, anchor="lm"
        )

    bar(560, 14.1, (120, 130, 155), "sequential")
    bar(740, 4.7, CYAN, "parallel")
    d.text((140, 850), "asyncio.gather()", font=font(34, mono=True), fill=PURPLE)

    glow_text(img, (2020, 1080), "3×", font(230), INK, CYAN, anchor="mm")
    d = ImageDraw.Draw(img)
    d.text(
        (1760, 1080),
        "the bottleneck was the\narchitecture, not the model",
        font=font(44, bold=False),
        fill=DIM,
        anchor="rm",
        align="right",
    )
    footer(d, "04 / 08")
    return img


def frame_05_impact() -> Image.Image:
    img = bg((W // 2, 350), GREEN)
    d = ImageDraw.Draw(img)
    kicker(d, (140, 150), "Impact", GREEN)
    d.text((140, 220), "What it replaces.", font=font(96), fill=INK)

    table = (140, 430, 2260, 1140)
    card(d, table, radius=36)
    col2, col3 = 1080, 1690
    rows = [
        ("", "AOI machine", "Neuron Vision"),
        ("Capex", "$500K – $1M", "$0 infrastructure"),
        ("Per inspection", "amortized $$", "API cents"),
        ("New board design", "weeks of reprogramming", "edit a prompt"),
        ("Where it runs", "one factory line", "any Cloud Run region"),
    ]
    rh = (table[3] - table[1]) // len(rows)
    for i, (a, b, c) in enumerate(rows):
        y = table[1] + i * rh
        if i == 0:
            d.rounded_rectangle([table[0], y, table[2], y + rh], radius=36, fill=(24, 33, 58))
            d.rectangle([table[0], y + rh // 2, table[2], y + rh], fill=(24, 33, 58))
        elif i % 2 == 0:
            d.rectangle([table[0] + 4, y, table[2] - 4, y + rh], fill=(20, 28, 50))
        cy = y + rh // 2
        d.text((table[0] + 60, cy), a, font=font(46), fill=DIM, anchor="lm")
        bcol = INK if i == 0 else (200, 140, 150)
        ccol = INK if i == 0 else GREEN
        d.text((col2, cy), b, font=font(46, bold=(i == 0)), fill=bcol, anchor="lm")
        d.text(
            (col3, cy),
            ("" if i == 0 else "✓ ") + c,
            font=font(46, bold=(i == 0)),
            fill=ccol,
            anchor="lm",
        )
        if i:
            d.line([table[0] + 30, y, table[2] - 30, y], fill=CARD_EDGE, width=2)

    d.text(
        (W // 2, 1210),
        "QC that scales down to a ten-person shop — not just up to a gigafactory.",
        font=font(46),
        fill=AMBER,
        anchor="mm",
    )
    footer(d, "05 / 08")
    return img


def frame_06_observability() -> Image.Image:
    img = bg((W // 2, 1000), PURPLE)
    d = ImageDraw.Draw(img)
    kicker(d, (140, 150), "Arize Phoenix · OpenInference", PURPLE)
    d.text((140, 220), "Every verdict is traceable.", font=font(96), fill=INK)

    stats = [
        ("142", "traces captured", CYAN),
        ("98.6%", "pipeline success", GREEN),
        ("6.2 s", "P95 latency", AMBER),
    ]
    bw = 640
    for i, (big, small, color) in enumerate(stats):
        x = 150 + i * (bw + 70)
        card(d, (x, 480, x + bw, 920), radius=36, edge=color)
        glow_text(img, (x + bw // 2, 660), big, font(150), INK, color, anchor="mm")
        d = ImageDraw.Draw(img)
        d.text((x + bw // 2, 820), small, font=font(46, bold=False), fill=DIM, anchor="mm")

    d.text(
        (W // 2, 1050),
        "When an agent disagrees with a human inspector,",
        font=font(46, bold=False),
        fill=DIM,
        anchor="mm",
    )
    d.text(
        (W // 2, 1120),
        "we replay exactly what it saw — and what it said.",
        font=font(46),
        fill=INK,
        anchor="mm",
    )
    footer(d, "06 / 08")
    return img


def frame_07_tech_code() -> Image.Image:
    img = bg((400, 300), PURPLE)
    d = ImageDraw.Draw(img)
    kicker(d, (140, 130), "200 lines you can actually read", PURPLE)

    # editor window
    win = (140, 250, 2260, 1180)
    d.rounded_rectangle(win, radius=24, fill=(13, 17, 28), outline=(50, 58, 80), width=3)
    d.rectangle([win[0], 250 + 70, win[2], 250 + 74], fill=(30, 36, 54))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([win[0] + 36 + i * 52, 274, win[0] + 66 + i * 52, 304], fill=c)
    d.rounded_rectangle([win[0] + 220, 262, win[0] + 880, 316], radius=10, fill=(24, 30, 46))
    d.text(
        (win[0] + 250, 289),
        "src/neuron_vision/pipeline.py",
        font=font(32, mono=True),
        fill=(170, 180, 200),
        anchor="lm",
    )

    KW, FN, STR, COM, VAR, PUN = (
        (199, 146, 234),
        (130, 170, 255),
        (195, 232, 141),
        (99, 109, 131),
        (236, 239, 244),
        (137, 221, 255),
    )
    code: list[list[tuple[str, tuple]]] = [
        [("# Stage 2 — three specialists, one photo, in parallel", COM)],
        [
            ("solder_fut", VAR),
            ("     = ", PUN),
            ("run_in_executor", FN),
            ("(", PUN),
            ("loop", VAR),
            (", ", PUN),
            ("self", KW),
            ("._solder.run", VAR),
            (")", PUN),
        ],
        [
            ("components_fut", VAR),
            (" = ", PUN),
            ("run_in_executor", FN),
            ("(", PUN),
            ("loop", VAR),
            (", ", PUN),
            ("self", KW),
            ("._components.run", VAR),
            (")", PUN),
        ],
        [
            ("markings_fut", VAR),
            ("   = ", PUN),
            ("run_in_executor", FN),
            ("(", PUN),
            ("loop", VAR),
            (", ", PUN),
            ("self", KW),
            ("._markings.run", VAR),
            (")", PUN),
        ],
        [],
        [
            ("reports", VAR),
            (" = ", PUN),
            ("await", KW),
            (" asyncio.", VAR),
            ("gather", FN),
            ("(", PUN),
        ],
        [("    solder_fut, components_fut, markings_fut,", VAR)],
        [
            ("    return_exceptions", VAR),
            ("=", PUN),
            ("True", KW),
            (",", PUN),
            ("          # 14.1 s -> 4.7 s", COM),
        ],
        [(")", PUN)],
        [],
        [("# Every agent: structured output, no string parsing", COM)],
        [("config", VAR), (" = ", PUN), ("GenerationConfig", FN), ("(", PUN)],
        [("    response_mime_type", VAR), ("=", PUN), ('"application/json"', STR), (",", PUN)],
        [
            ("    response_schema", VAR),
            ("=", PUN),
            ("vertex_schema", FN),
            ("(", PUN),
            ("SolderReport", FN),
            ("),", PUN),
            ("  # Pydantic v2", COM),
        ],
        [(")", PUN)],
    ]
    f = font(40, mono=True, bold=False)
    y = 380
    for n, line in enumerate(code, start=1):
        d.text((win[0] + 50, y), f"{n:>2}", font=f, fill=(70, 80, 100))
        x = win[0] + 160
        for text, color in line:
            d.text((x, y), text, font=f, fill=color)
            x += d.textlength(text, font=f)
        y += 52

    d.text(
        (W // 2, 1208),
        "Vertex AI SDK · Pydantic v2 · ~200-line orchestrator",
        font=font(38, mono=True),
        fill=DIM,
        anchor="ma",
    )
    footer(d, "07 / 08")
    return img


def frame_08_cta() -> Image.Image:
    img = bg((W // 2, 560), CYAN)
    d = ImageDraw.Draw(img)
    glow_text(img, (W // 2, 420), "NEURON VISION", font(170), INK, CYAN, anchor="mm")
    d = ImageDraw.Draw(img)
    d.text(
        (W // 2, 580),
        "Factory-grade inspection. No factory budget.",
        font=font(58),
        fill=INK,
        anchor="mm",
    )

    card(d, (430, 700, 1970, 810), fill=(10, 30, 36), edge=CYAN)
    d.text(
        (W // 2, 755),
        "neuron-vision-display-z3mwyxcila-uc.a.run.app",
        font=font(46, mono=True),
        fill=CYAN,
        anchor="mm",
    )
    card(d, (430, 850, 1970, 960), fill=(13, 20, 36), edge=CARD_EDGE)
    d.text(
        (W // 2, 905),
        "github.com/aleksandrlyubarev-blip/roboqc-agent-challenge",
        font=font(44, mono=True),
        fill=INK,
        anchor="mm",
    )

    d.text(
        (W // 2, 1060),
        "Vertex AI Gemini 2.5 Pro  ·  Cloud Run  ·  Arize Phoenix",
        font=font(40, mono=True),
        fill=DIM,
        anchor="mm",
    )
    d.text(
        (W // 2, 1140),
        "Google Cloud Rapid Agent Hackathon 2026 — Arize partner track",
        font=font(36, bold=False),
        fill=DIM,
        anchor="mm",
    )
    footer(d, "08 / 08")
    return img


FRAMES = {
    "v5_01_cost_stat.png": frame_01_cost_stat,
    "v5_02_pipeline.png": frame_02_pipeline,
    "v5_03_demo.png": frame_03_demo,
    "v5_04_speed_compare.png": frame_04_speed_compare,
    "v5_05_impact.png": frame_05_impact,
    "v5_06_observability.png": frame_06_observability,
    "v5_07_tech_code.png": frame_07_tech_code,
    "v5_08_cta.png": frame_08_cta,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in FRAMES.items():
        fn().save(OUT / name)
        print(f"wrote {OUT / name}")


if __name__ == "__main__":
    main()
