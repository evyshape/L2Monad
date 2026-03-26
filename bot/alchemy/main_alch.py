import asyncio
import numpy as np
import mss
import pygetwindow as gw
import cv2
import time
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from bot.clogger import log
from bot.alchemy.alch_cons import ALCH_SLOTS_FULL, ENCHANT_COORDS, ALCH_REZ_POSITIONS
from bot.methods.base import parseAlch

IMG_SIZE = 32
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CLASS_NAMES = ['1', '3', '5', '6', '7', '8', '9']
NUM_CLASSES = len(CLASS_NAMES)
MODEL_PATH = "bot/alchemy/L2Monad.pth"


class DigitCNN(nn.Module):
    def __init__(self, num_classes):
        super(DigitCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(256 * 4 * 4, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x


model = DigitCNN(NUM_CLASSES).to(DEVICE)
state_dict = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True)
model.load_state_dict(state_dict)
model.eval()

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])

def _slot(slot_img, var, slot_name, threshold=0.65):

    def _crop(slot_img, slot_name, size=64):
        slot_x1, slot_y1 = map(
            int,
            ALCH_SLOTS_FULL[var][slot_name][0].split(',')
        )
        digit_x1, digit_y1 = map(
            int,
            ENCHANT_COORDS[var][slot_name][0].split(',')
        )
        digit_x2, digit_y2 = map(
            int,
            ENCHANT_COORDS[var][slot_name][1].split(',')
        )

        rel_x1 = digit_x1 - slot_x1
        rel_y1 = digit_y1 - slot_y1
        rel_x2 = digit_x2 - slot_x1
        rel_y2 = digit_y2 - slot_y1

        digit_crop = slot_img[rel_y1:rel_y2, rel_x1:rel_x2]
        h_crop, w_crop = digit_crop.shape[:2]
        if h_crop == 0 or w_crop == 0:
            return np.zeros((size, size, 3), dtype=np.uint8)

        side = max(h_crop, w_crop)
        out = np.zeros((side, side, 3), dtype=np.uint8)
        y_off = (side - h_crop) // 2
        x_off = (side - w_crop) // 2
        out[y_off:y_off + h_crop, x_off:x_off + w_crop] = digit_crop
        out = cv2.resize(out, (size, size), interpolation=cv2.INTER_CUBIC)
        return out

    def _white(img_np, lower_thr=212):
        mask = (img_np[:, :, 0] >= lower_thr) & \
               (img_np[:, :, 1] >= lower_thr) & \
               (img_np[:, :, 2] >= lower_thr)

        exp = np.zeros_like(mask, dtype=bool)

        shifts = [(-1, -1), (-1, 0), (-1, 1),
                  (0, -1), (0, 0), (0, 1),
                  (1, -1), (1, 0), (1, 1)]

        for dy, dx in shifts:
            shifted = np.zeros_like(mask)
            if dy < 0:
                ys = slice(-dy, None)
                ys_src = slice(0, dy)
            elif dy > 0:
                ys = slice(0, -dy)
                ys_src = slice(dy, None)
            else:
                ys = slice(None)
                ys_src = slice(None)
            if dx < 0:
                xs = slice(-dx, None)
                xs_src = slice(0, dx)
            elif dx > 0:
                xs = slice(0, -dx)
                xs_src = slice(dx, None)
            else:
                xs = slice(None)
                xs_src = slice(None)
            shifted[ys, xs] = mask[ys_src, xs_src]
            exp |= shifted

        img_copy = img_np.copy()
        img_copy[exp] = [0, 0, 0]
        return img_copy

    def _check_enchant(img_np):
        img = Image.fromarray(cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB))
        if img.size == (32, 32):
            center, half = 16, 8
            img = img.crop((center - half, center - half, center + half, center + half))
        img = img.resize((32, 32))
        img_tensor = transform(img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            outputs = model(img_tensor)
            probs = torch.softmax(outputs, dim=1)
            conf, pred = torch.max(probs, 1)
            if conf.item() < threshold:
                return None, conf.item()
        return CLASS_NAMES[pred.item()], conf.item()

    def _check_red(slot_img, slot_name, trg=(113, 104, 235), thr=45):
        h, w, _ = slot_img.shape
        cy, cx = h // 2, w // 2

        left_x = 0
        top_y = max(0, cy - 2)

        x1 = left_x
        y1 = top_y
        x2 = min(x1 + 5, w)
        y2 = min(y1 + 5, h)

        square = slot_img[y1:y2, x1:x2, :3].astype(np.int16)
        trg_arr = np.array(trg, dtype=np.int16)
        mask = np.all(np.abs(square - trg_arr) <= thr, axis=2)
        found = np.any(mask)
        return found

    ench_img = _crop(slot_img, slot_name, size=64)
    ench_img = _white(ench_img)
    pred_class, conf = _check_enchant(ench_img)
    is_red = _check_red(slot_img, slot_name)

    return {"enchant": pred_class, "avg": float(conf), "red": bool(is_red)}

async def check_slots(profile, var, threshold=0.99):
    window_id, window = next(iter(profile.window_info.items()))
    results = {}
    try:
        win = gw.getWindowsWithTitle(window['Title'])[0]

        slots = ALCH_SLOTS_FULL.get(var)
        with mss.mss() as sct:
            for slot_name, coords in slots.items():
                x1, y1 = map(int, coords[0].split(','))
                x2, y2 = map(int, coords[1].split(','))
                bbox = {"top": win.top + y1, "left": win.left + x1,
                        "width": x2 - x1, "height": y2 - y1}
                sct_img = np.array(sct.grab(bbox))
                if sct_img.shape[2] == 4:
                    sct_img = cv2.cvtColor(sct_img, cv2.COLOR_BGRA2BGR)
                results[slot_name] = _slot(sct_img, var, slot_name, threshold)

        return results

    except Exception as e:
        log(f"Ошибка при check_slots: {e}", window_id)
        return {}

def match_slots(result: dict, bless: str, config: dict) -> bool:
    alw = {b.strip().lower() for b in config.get("BLESS", "").split(",")}
    if bless.lower() not in alw:
        return False

    for i in range(1, 6):
        slot_key = f"slot_{i}"
        slot_res = result.get(slot_key)
        if not slot_res:
            return False

        allowed_raw = config.get(f"SLOT_{i}", "").split(",")
        allowed = {v.strip().lower() for v in allowed_raw if v.strip()}

        if not allowed or "any" in allowed:
            continue

        enchant = slot_res.get("enchant")
        is_red = slot_res.get("red", False)

        ok = False
        for val in allowed:
            if val == "red" and is_red:
                ok = True

            elif val.startswith("red") and is_red and enchant == val.replace("red", ""):
                ok = True

            elif enchant == val:
                ok = True

        if not ok:
            return False

    return True

async def check_bless(profile, timeout=3, thr=55):
    window_id = next(iter(profile.window_info))
    targets = {
        "gold": parseAlch("gold"),
        "white": parseAlch("white"),
        "blue": parseAlch("blue"),
    }
    rects = [(xy[0], xy[1], 5, 5) for xy, _ in targets.values()]

    start = time.time()
    found = None

    while time.time() - start < timeout:
        images = await profile.capture_multy(rects)
        for (name, (xy, rgb)), img in zip(targets.items(), images):
            diff = np.abs(img.astype(np.int16) - np.array(rgb, dtype=np.int16))
            mask = np.all(diff <= thr, axis=-1)
            if np.any(mask):
                found = name
                break
        if found:
            break
        await asyncio.sleep(0.05)

    log(found, window_id)
    return found


async def pre_init(profile):
    window_id = next(iter(profile.window_info))

    xy, rgb = parseAlch("alch_zero_reroll")
    if await profile.check_pixel(xy, rgb, timeout=0.2, thr=4):
        log("Алхимка не заряжена либо невозможно кликнуть", window_id)
        return "zero"

    xy, rgb = parseAlch("alch_not_zero_start")
    if await profile.check_pixel(xy, rgb, timeout=0.2, thr=4, wsize="2x2"):
        log("Алхимка заряжена но еще не врубалась, жму", window_id)
        x, y = xy
        await profile.mouse.click(profile.window_info, x, y)

        xy, rgb = parseAlch("alch_first_reroll")
        if await profile.check_pixel(xy, rgb, timeout=5, thr=2):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            log("Крутнул алхимку впервые", window_id)
            return "first"

    xy, rgb = parseAlch("reroll")
    if await profile.check_pixel(xy, rgb, timeout=1, thr=2):
        log("Алхимка уже была заряжена и 1 раз рольнута", window_id)
        return "more"

    return None

async def roll(profile, step=2, kb=None):

    async def wait_and_click(tag, timeout=5, thr=2):
        xy, rgb = parseAlch(tag)
        if tag == "reroll_confirm":
            ww = "5x5"
            thr = 15
        else:
            ww = "2x2"

        if await profile.check_pixel(xy, rgb, timeout=timeout, thr=thr, wsize=ww):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            return True
        return False

    steps = {
        1: ["reroll"],
        2: ["reroll_confirm"],
        3: ["reroll_cancel"]
    }

    for tag in steps.get(step, []):
        if not await wait_and_click(tag):
            log(f"bahed | {tag}")
            return False

    return True

async def get_alch_var(profile):
    window_id = next(iter(profile.window_info))
    for var, value in ALCH_REZ_POSITIONS.items():
        xy = tuple(map(int, value[0].split(", ")))
        rgb = tuple(map(int, value[1].split(", ")))
        is_true = await profile.check_pixel(xy, rgb)
        log(f"{var}, {is_true}", window_id)
        if is_true:
            return var

    return None