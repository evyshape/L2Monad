import asyncio
import numpy as np
import mss
import pygetwindow as gw
import cv2
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from bot.clogger import log
from bot.alchemy.alch_cons import ALCH_POSITIONS_ENCHANT, ALCH_SLOTS_FULL
from bot.methods.base import parseAlch


IMG_SIZE = 32
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CLASS_NAMES = ['1', '3', '5', '6', '7', '8', '9']
NUM_CLASSES = len(CLASS_NAMES)
MODEL_PATH = "bot/alchemy/model_main.pth"

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

def _slot(slot_img, slot_name, threshold=0.65):
    
    def _crop(slot_img, slot_coords, enchant_coords, size=32):
        slot_x1, slot_y1 = map(int, slot_coords[0].split(','))
        ench_x1, ench_y1 = map(int, enchant_coords[0].split(','))
        ench_x2, ench_y2 = map(int, enchant_coords[1].split(','))
        lx1, ly1 = ench_x1 - slot_x1, ench_y1 - slot_y1
        lx2, ly2 = ench_x2 - slot_x1, ench_y2 - slot_y1
        h, w, _ = slot_img.shape
        crop = slot_img[max(0, ly1):min(h, ly2), max(0, lx1):min(w, lx2)]
        out = np.zeros((ly2 - ly1, lx2 - lx1, 3), dtype=np.uint8)
        y_off, x_off = max(0, -ly1), max(0, -lx1)
        out[y_off:y_off + crop.shape[0], x_off:x_off + crop.shape[1]] = crop
        return cv2.resize(out, (size, size), interpolation=cv2.INTER_CUBIC)

    def _white(img_np, lower_thr=235):
        mask = np.all(img_np >= lower_thr, axis=2)
        img_np[mask] = [0, 0, 0]
        return img_np

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

    def _check_red(slot_img, trg=(143, 134, 255), thr=45):
        h, w, _ = slot_img.shape
        y_center, x_start = h // 2, 1
        region = slot_img[max(0, y_center - 1):min(h, y_center + 2),
                          max(0, x_start):min(w, x_start + 3), :3]
        diff = np.abs(region.astype(np.int16) - np.array(trg, dtype=np.int16))
        return bool(np.any(np.all(diff <= thr, axis=2)))

    ench_img = _crop(slot_img, ALCH_SLOTS_FULL[slot_name], ALCH_POSITIONS_ENCHANT[slot_name])
    ench_img = _white(ench_img, lower_thr=230)

    pred_class, conf = _check_enchant(ench_img)
    is_red = _check_red(slot_img)

    return {"enchant": pred_class, "avg": float(conf), "red": bool(is_red)}

async def check_slots(profile, threshold=0.99):
    window_id, window = next(iter(profile.window_info.items()))
    results = {}
    try:
        win = gw.getWindowsWithTitle(window['Title'])[0]

        with mss.mss() as sct:
            for slot_name, coords in ALCH_SLOTS_FULL.items():
                x1, y1 = map(int, coords[0].split(','))
                x2, y2 = map(int, coords[1].split(','))
                bbox = {"top": win.top + y1, "left": win.left + x1,
                        "width": x2 - x1, "height": y2 - y1}
                sct_img = np.array(sct.grab(bbox))
                if sct_img.shape[2] == 4:
                    sct_img = cv2.cvtColor(sct_img, cv2.COLOR_BGRA2BGR)
                results[slot_name] = _slot(sct_img, slot_name, threshold)

        return results

    except Exception as e:
        log(f"Ошибка при check_slots: {e}", window_id)
        return {}

def match_slots(result: dict, bless: str, config: dict) -> bool:
    alw = {b.strip() for b in config["BLESS"].split(",")}
    if bless not in alw:
        return False

    for i in range(1, 6):
        slot_key = f"slot_{i}"
        slot_res = result.get(slot_key)
        if not slot_res:
            return False

        allowed = {v.strip() for v in config[f"SLOT_{i}"].split(",")}
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

async def check_bless(profile):
    window_id = next(iter(profile.window_info))
    targets = {
        "gold": parseAlch("gold"),
        "white": parseAlch("white"),
        "blue": parseAlch("blue"),
    }
    tasks = {
        name: asyncio.create_task(
            profile.check_pixel(xy, rgb, timeout=3, thr=55, wsize="5x5")
        ) for name, (xy, rgb) in targets.items()
    }
    done, pending = await asyncio.wait(tasks.values(), return_when=asyncio.FIRST_COMPLETED)
    found = None
    for name, task in tasks.items():
        if task in done and task.result() is True:
            found = name
            break
    for p in pending:
        p.cancel()
    log(found, window_id)
    return found

async def pre_init(profile):
    await asyncio.sleep(2)
    window_id = next(iter(profile.window_info))

    xy, rgb = parseAlch("alch_zero_reroll")
    if await profile.check_pixel(xy, rgb, timeout=2, thr=4):
        log("Алхимка не заряжена либо невозможно кликнуть", window_id)
        return "zero"

    xy, rgb = parseAlch("alch_not_zero_start")
    if await profile.check_pixel(xy, rgb, timeout=2, thr=4, wsize="2x2"):
        log("Алхимка заряжена но еще не врубалась, жму", window_id)
        x, y = xy
        await profile.mouse.click(profile.window_info, x, y)
        await asyncio.sleep(0.2)
        xy, rgb = parseAlch("alch_first_reroll")
        if await profile.check_pixel(xy, rgb, timeout=5, thr=2):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            await asyncio.sleep(0.2)
            log("Крутнул алхимку впервые", window_id)
            return "first"

    xy, rgb = parseAlch("reroll")
    if await profile.check_pixel(xy, rgb, timeout=1, thr=2):
        log("Алхимка уже была заряжена и 1 раз рольнута", window_id)
        return "more"

    return None

async def roll(profile, step=2):

    async def wait_and_click(tag, timeout=5, thr=2):
        xy, rgb = parseAlch(tag)
        if await profile.check_pixel(xy, rgb, timeout=timeout, thr=thr, wsize="2x2"):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            return True
        return False

    steps = {
        1: ["reroll"],
        2: ["reroll_confirm"],
        3: ["reroll_cancel"],
    }

    for tag in steps.get(step, []):
        if not await wait_and_click(tag):
            return False

    return True