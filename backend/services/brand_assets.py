"""Brand asset generator for email and server-rendered surfaces.

We render the ThirdEye eye-mark to a crisp PNG at runtime so the logo
embedded in email matches the interactive SVG used in the web UI. Email
clients are famously hostile to inline SVG (Gmail web strips it), so we
ship raster PNG bytes and reference them via `cid:` attachments.

The geometry here mirrors ``frontend/src/components/ThirdEyeLogo.tsx``:
  - viewBox 0 0 110 82
  - almond-shaped eye via cubic Bézier
  - iris rings at r=20 and r=13 centered (55,45)
  - pupil r=8 with a specular highlight top-right
  - orbiting "scanner" dot at 12 o'clock of the iris ring
  - eyebrow arc above the eye
  - faint corner tick marks

We draw at 4× the target size with anti-aliasing and downsample with
``LANCZOS`` for smooth edges, then cache the bytes so repeated email
sends don't re-render.
"""
from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from typing import Tuple

from PIL import Image, ImageDraw


# Palette — kept in lockstep with the warm cream theme in index.css.
_INK = (26, 23, 20)            # #1A1714 — warm near-black
_BG  = (250, 249, 247)         # #FAF9F7 — warm cream (page bg)
_SCLERA = (242, 239, 233)      # #F2EFE9 — subtle sclera fill


def _with_alpha(rgb: Tuple[int, int, int], alpha: float) -> Tuple[int, int, int, int]:
    return (rgb[0], rgb[1], rgb[2], max(0, min(255, int(round(alpha * 255)))))


@lru_cache(maxsize=8)
def render_thirdeye_logo_png(
    width: int = 180,
    height: int = 134,
    bg_rgb: Tuple[int, int, int] = _BG,
) -> bytes:
    """Render the ThirdEye eye mark as PNG bytes.

    Args:
        width / height: output dimensions in CSS pixels. The image is
            actually drawn at 4× these dimensions and scaled down for
            anti-aliasing, so the result is retina-crisp at the display
            size.
        bg_rgb: background color to composite against. Pass the email
            body background so the eyelid mask blends seamlessly. The
            default matches the cream email shell.

    Returns:
        PNG bytes, ready to attach as a CID image.
    """
    scale = 4
    W = width * scale
    H = height * scale

    img = Image.new("RGB", (W, H), bg_rgb)
    draw = ImageDraw.Draw(img, "RGBA")

    # Map 110×82 viewBox → pixel space, preserving aspect ratio and
    # centering the mark. We letterbox instead of stretching.
    vb_w, vb_h = 110.0, 82.0
    fit = min(W / vb_w, H / vb_h)
    ox = (W - vb_w * fit) / 2
    oy = (H - vb_h * fit) / 2

    def px(x: float, y: float) -> Tuple[float, float]:
        return (ox + x * fit, oy + y * fit)

    def pxp(pt: Tuple[float, float]) -> Tuple[float, float]:
        return (ox + pt[0] * fit, oy + pt[1] * fit)

    # ── 1. Eyebrow arc ─────────────────────────────────────────────────
    # Approximate the SVG path "M20 10 C42 2 68 2 90 10" as a quadratic
    # curve we sample and stroke with a thick line.
    eyebrow_pts = []
    steps = 40
    p0 = (20, 10)
    p1 = (42, 2)
    p2 = (68, 2)
    p3 = (90, 10)
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        # Cubic Bézier
        bx = (u ** 3) * p0[0] + 3 * (u ** 2) * t * p1[0] + 3 * u * (t ** 2) * p2[0] + (t ** 3) * p3[0]
        by = (u ** 3) * p0[1] + 3 * (u ** 2) * t * p1[1] + 3 * u * (t ** 2) * p2[1] + (t ** 3) * p3[1]
        eyebrow_pts.append(px(bx, by))
    draw.line(eyebrow_pts, fill=_with_alpha(_INK, 0.5), width=max(2, int(2.4 * fit)))

    # ── 2. Almond eye outline ──────────────────────────────────────────
    # Sample the two cubic halves "M3 45 C24 16 86 16 107 45" (top lid)
    # and "C86 74 24 74 3 45" (bottom lid) and stitch into a closed path.
    def sample_cubic(p0, p1, p2, p3, steps=60):
        out = []
        for i in range(steps + 1):
            t = i / steps
            u = 1 - t
            bx = (u ** 3) * p0[0] + 3 * (u ** 2) * t * p1[0] + 3 * u * (t ** 2) * p2[0] + (t ** 3) * p3[0]
            by = (u ** 3) * p0[1] + 3 * (u ** 2) * t * p1[1] + 3 * u * (t ** 2) * p2[1] + (t ** 3) * p3[1]
            out.append((bx, by))
        return out

    top_half = sample_cubic((3, 45), (24, 16), (86, 16), (107, 45))
    bot_half = sample_cubic((107, 45), (86, 74), (24, 74), (3, 45))
    eye_outline = top_half + bot_half[1:]

    # Fill the sclera interior first so overlays draw on top of it.
    draw.polygon([pxp(p) for p in eye_outline], fill=_SCLERA)

    # ── 3. Iris rings (r=20 and r=13) ──────────────────────────────────
    cx, cy = 55, 45

    def ellipse_at(cx_vb, cy_vb, r, outline, width, fill=None):
        bbox = (
            *px(cx_vb - r, cy_vb - r),
            *px(cx_vb + r, cy_vb + r),
        )
        draw.ellipse(bbox, outline=outline, width=width, fill=fill)

    ellipse_at(cx, cy, 20, outline=_with_alpha(_INK, 0.5), width=max(1, int(1.0 * fit)),
               fill=_with_alpha(_INK, 0.05))
    ellipse_at(cx, cy, 13, outline=_with_alpha(_INK, 0.2), width=max(1, int(0.8 * fit)))

    # ── 4. Subtle circuit traces around the iris ──────────────────────
    # A restrained subset of the SVG traces — enough to keep the "circuit
    # eye" identity without looking busy at small sizes.
    trace_alpha = 0.22
    trace_color = _with_alpha(_INK, trace_alpha)
    lw = max(1, int(0.7 * fit))

    def vbline(ax, ay, bx, by):
        draw.line([pxp((ax, ay)), pxp((bx, by))], fill=trace_color, width=lw)

    # Left sclera traces
    vbline(4, 45, 35, 45)
    vbline(11, 40, 36, 40)
    # Right sclera traces
    vbline(75, 45, 106, 45)
    vbline(74, 40, 99, 40)
    # Top / bottom
    vbline(48, 18, 48, 27); vbline(48, 27, 52, 27)
    vbline(62, 18, 62, 27); vbline(62, 27, 58, 27)

    # Junction dots
    def vbdot(x, y, r, alpha=0.6):
        bbox = (*px(x - r, y - r), *px(x + r, y + r))
        draw.ellipse(bbox, fill=_with_alpha(_INK, alpha))

    vbdot(21, 45, 1.4)
    vbdot(89, 45, 1.4)
    vbdot(20, 40, 1.1, alpha=0.45)
    vbdot(90, 40, 1.1, alpha=0.45)
    vbdot(52, 27, 1.1, alpha=0.45)
    vbdot(58, 27, 1.1, alpha=0.45)

    # ── 5. Orbiting scanner dot at 12 o'clock of the iris ──────────────
    # In the UI this spins; for a still asset we freeze it at a pleasing
    # slightly-past-noon angle.
    scanner_x, scanner_y = 55, 25
    # Soft trailing glow
    for r, alpha in [(2.6, 0.25), (3.6, 0.15), (4.8, 0.08)]:
        vbdot(scanner_x, scanner_y, r, alpha=alpha)
    vbdot(scanner_x, scanner_y, 2.6, alpha=0.95)

    # ── 6. Pupil with specular highlight ──────────────────────────────
    # Pupil
    bbox = (*px(cx - 8, cy - 8), *px(cx + 8, cy + 8))
    draw.ellipse(bbox, fill=_INK)
    # Highlight (offset to top-right like in the SVG)
    hx, hy, hr = 58.5, 41.5, 2.4
    bbox = (*px(hx - hr, hy - hr), *px(hx + hr, hy + hr))
    draw.ellipse(bbox, fill=_with_alpha((255, 255, 255), 0.85))

    # ── 7. Eye outline stroke (drawn last so it sits on top) ──────────
    draw.line(
        [pxp(p) for p in eye_outline] + [pxp(eye_outline[0])],
        fill=_INK,
        width=max(2, int(1.6 * fit)),
        joint="curve",
    )

    # Lower-lid crease (faint)
    crease = sample_cubic((18, 54), (38, 63), (72, 63), (92, 54))
    draw.line([pxp(p) for p in crease], fill=_with_alpha(_INK, 0.13), width=max(1, int(0.8 * fit)))

    # Corner tick marks
    draw.line([px(3, 45), px(0, 45)], fill=_with_alpha(_INK, 0.25), width=max(1, int(1.2 * fit)))
    draw.line([px(107, 45), px(110, 45)], fill=_with_alpha(_INK, 0.25), width=max(1, int(1.2 * fit)))

    # ── Finalize: downsample for smooth edges ──────────────────────────
    final = img.resize((width, height), resample=Image.LANCZOS)

    buf = BytesIO()
    final.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_test_frame_png(width: int = 640, height: int = 360) -> bytes:
    """Render a simple placeholder 'frame' to use in test emails.

    Returns a PNG (encoded as-if it were the camera frame). The email
    pipeline accepts any base64-encoded image, so PNG works — the
    Content-Type header ends up as image/jpeg either way but clients
    sniff the bytes and render it correctly.
    """
    img = Image.new("RGB", (width, height), (38, 35, 33))
    draw = ImageDraw.Draw(img)

    # Subtle grid to make it look like a camera feed
    grid_alpha_color = (64, 59, 55)
    step = 40
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill=grid_alpha_color, width=1)
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill=grid_alpha_color, width=1)

    # Centered logo
    logo_w, logo_h = 220, 164
    logo_bytes = render_thirdeye_logo_png(logo_w, logo_h, bg_rgb=(38, 35, 33))
    logo_img = Image.open(BytesIO(logo_bytes))
    img.paste(logo_img, ((width - logo_w) // 2, (height - logo_h) // 2 - 20))

    # Caption
    try:
        caption = "TEST FRAME — ThirdEye email preview"
        # Draw without a specific font — Pillow falls back to its default bitmap
        # font which is perfectly legible at this size.
        draw.text(
            (width // 2 - 150, height - 40),
            caption,
            fill=(200, 195, 188),
        )
    except Exception:
        pass

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
