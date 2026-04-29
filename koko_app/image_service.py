import io
import os

from .config import U2NET_MODEL_PATH


def get_rembg_state():
    try:
        import importlib.util

        rembg_installed = importlib.util.find_spec("rembg") is not None
    except Exception:
        rembg_installed = False

    if not rembg_installed:
        return "no_rembg"
    if not os.path.exists(U2NET_MODEL_PATH):
        return "no_model"
    return "ready"


def enhance_passport_image(img_bytes):
    try:
        from PIL import Image as _PIL, ImageEnhance, ImageFilter

        img = _PIL.open(io.BytesIO(img_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img = ImageEnhance.Contrast(img).enhance(1.8)
        img = ImageEnhance.Sharpness(img).enhance(2.5)
        img = ImageEnhance.Brightness(img).enhance(1.1)
        img = img.filter(ImageFilter.SHARPEN)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        buf.seek(0)
        return buf.read()
    except Exception:
        return img_bytes


def make_white_background(img_bytes):
    try:
        import numpy as _np0
        from PIL import Image as _PIL0

        _img0 = _PIL0.open(io.BytesIO(img_bytes)).convert("RGB")
        _arr0 = _np0.array(_img0, dtype=_np0.int32)
        _edge0 = _np0.concatenate([
            _arr0[:15, :].reshape(-1, 3), _arr0[-15:, :].reshape(-1, 3),
            _arr0[:, :15].reshape(-1, 3), _arr0[:, -15:].reshape(-1, 3),
        ])
        _bg0 = _np0.median(_edge0, axis=0)
        if _bg0.mean() > 245 and (_bg0.max() - _bg0.min()) < 8:
            return img_bytes
    except Exception:
        pass

    try:
        if os.path.exists(U2NET_MODEL_PATH):
            from rembg import remove as _rembg_remove
            from PIL import Image as _PIL

            result_bytes = _rembg_remove(img_bytes)
            fg = _PIL.open(io.BytesIO(result_bytes)).convert("RGBA")
            white = _PIL.new("RGBA", fg.size, (255, 255, 255, 255))
            white.paste(fg, mask=fg.split()[3])
            buf = io.BytesIO()
            white.convert("RGB").save(buf, format="JPEG", quality=92)
            buf.seek(0)
            return buf.read()
    except Exception:
        pass

    try:
        import numpy as _np
        from PIL import Image as _PIL, ImageFilter as _IF

        img = _PIL.open(io.BytesIO(img_bytes)).convert("RGB")
        arr = _np.array(img, dtype=_np.float32)
        h, w = arr.shape[:2]
        arr_int = arr.astype(_np.int32)

        edge_px = _np.concatenate([
            arr_int[:20, :].reshape(-1, 3), arr_int[-20:, :].reshape(-1, 3),
            arr_int[:, :20].reshape(-1, 3), arr_int[:, -20:].reshape(-1, 3),
        ])
        bg = _np.median(edge_px, axis=0).astype(_np.int32)
        bg_brightness = float(bg.mean())
        tol = 100 if bg_brightness > 180 else 75

        try:
            from scipy import ndimage as _ndi

            diff = _np.abs(arr_int - bg).sum(axis=2)
            brightness = arr_int.mean(axis=2)
            saturation = arr_int.max(axis=2) - arr_int.min(axis=2)
            light_unsat = (brightness > 160) & (saturation < 40)
            bg_region = (diff < tol) | light_unsat
            seed = _np.zeros((h, w), dtype=bool)
            seed[:10, :] = seed[-10:, :] = seed[:, :10] = seed[:, -10:] = True
            flooded = _ndi.binary_propagation(seed, mask=bg_region)
            flooded2 = _ndi.binary_dilation(flooded, iterations=6)
            flooded_dilated = _ndi.binary_dilation(flooded | flooded2, iterations=10)
            bg_sim = _np.clip(1.0 - diff / (tol * 2.0), 0, 1)
            extra = light_unsat.astype(float) * 0.7
            bg_sim = _np.maximum(bg_sim, extra * flooded_dilated)
            bg_sim_smooth = _ndi.gaussian_filter(bg_sim * flooded_dilated, sigma=4)
            is_fg = diff > tol * 1.5
            margin = min(h, w) // 7
            c_seed = _np.zeros((h, w), dtype=bool)
            c_seed[margin:-margin, margin:-margin] = True
            fg_core = _ndi.binary_propagation(c_seed & is_fg & ~flooded_dilated, mask=is_fg)
            fg_core = _ndi.binary_fill_holes(fg_core)
            fg_core = _ndi.binary_erosion(fg_core, iterations=2)
            bg_sim_smooth[fg_core] = 0
            alpha = _np.clip(bg_sim_smooth, 0, 1)[:, :, _np.newaxis]
            white_arr = _np.ones_like(arr) * 255
            result_arr = _np.clip(arr * (1 - alpha) + white_arr * alpha, 0, 255).astype(_np.uint8)
            result = _PIL.fromarray(result_arr)
        except Exception:
            diff = _np.abs(arr_int - bg).sum(axis=2)
            fg = (diff >= tol).astype(_np.uint8) * 255
            mask_img = _PIL.fromarray(fg, "L")
            mask_img = mask_img.filter(_IF.MaxFilter(9))
            mask_img = mask_img.filter(_IF.MinFilter(5))
            mask_img = mask_img.filter(_IF.GaussianBlur(2))
            white = _PIL.new("RGB", (w, h), (255, 255, 255))
            result = _PIL.composite(img, white, mask_img)

        buf = io.BytesIO()
        result.save(buf, format="JPEG", quality=92)
        buf.seek(0)
        return buf.read()
    except Exception:
        return img_bytes


def auto_crop_passport(img):
    import numpy as np

    try:
        gray = img.convert("L")
        w, h = img.size
        pixels = np.array(gray)

        corners = [pixels[0, 0], pixels[0, -1], pixels[-1, 0], pixels[-1, -1]]
        bg_val = int(sum(corners) / len(corners))

        if bg_val < 100:
            mask = pixels > 40
        else:
            mask = pixels < 240

        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)

        if not rows.any() or not cols.any():
            return img

        top = int(np.argmax(rows))
        bottom = int(len(rows) - np.argmax(rows[::-1]) - 1)
        left = int(np.argmax(cols))
        right = int(len(cols) - np.argmax(cols[::-1]) - 1)

        pad_x = max(20, int((right - left) * 0.05))
        pad_y = max(20, int((bottom - top) * 0.05))
        top = max(0, top - pad_y)
        bottom = min(h, bottom + pad_y)
        left = max(0, left - pad_x)
        right = min(w, right + pad_x)

        crop_w = right - left
        crop_h = bottom - top

        if crop_w < w * 0.3 or crop_h < h * 0.3:
            return img
        if crop_w < w * 0.95 or crop_h < h * 0.95:
            return img.crop((left, top, right, bottom))
        return img
    except Exception:
        return img


def pdf_to_image_bytes(pdf_path, max_kb=900):
    from PIL import Image as PILImage

    raw_buf = None

    try:
        import fitz

        doc = fitz.open(pdf_path)
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        raw_buf = io.BytesIO(pix.tobytes("jpeg"))
    except ImportError:
        pass

    if raw_buf is None:
        try:
            from pdf2image import convert_from_path

            images = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=1)
            raw_buf = io.BytesIO()
            images[0].save(raw_buf, format="JPEG", quality=85)
            raw_buf.seek(0)
        except Exception:
            pass

    if raw_buf is None:
        return None, None

    img = PILImage.open(raw_buf)
    if img.mode != "RGB":
        img = img.convert("RGB")

    img = auto_crop_passport(img)

    quality = 85
    while quality >= 30:
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=quality)
        if out.tell() / 1024 <= max_kb:
            out.seek(0)
            return out, "passport.jpg"
        quality -= 10

    w, h = img.size
    scale = 0.75
    out = io.BytesIO()
    while w > 400:
        w2, h2 = int(w * scale), int(h * scale)
        resized = img.resize((w2, h2), PILImage.LANCZOS)
        out = io.BytesIO()
        resized.save(out, format="JPEG", quality=60)
        if out.tell() / 1024 <= max_kb:
            out.seek(0)
            return out, "passport.jpg"
        w, h = w2, h2

    out.seek(0)
    return out, "passport.jpg"
