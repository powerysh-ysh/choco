"""새 여행카드 배경 4장 생성 (야경 / 드론쇼 / 해변 산책 / 일출).

기존 카드(images/card-*.jpg)와 같은 640x800 레이아웃:
상단 타이틀, 가운데 광안대교, 문구 상자(83~560, 495~672, 닉네임 포함), 하단 로고.
실행: python tools/make_cards.py  ->  images/card-{night,drone,beach,sunrise}.jpg
"""
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path('C:/Windows/Fonts')
S = 2                      # 슈퍼샘플링 배율
W, H = 640 * S, 800 * S
HORIZON = 392


def p(v):
    return int(round(v * S))


def lerp_colors(stops, n):
    """stops: [(pos 0~1, (r,g,b)), ...] -> (n,3) 배열"""
    xs = np.linspace(0, 1, n)
    out = np.zeros((n, 3))
    for c in range(3):
        out[:, c] = np.interp(xs, [s[0] for s in stops], [s[1][c] for s in stops])
    return out


def vgradient(top, bottom, stops):
    col = lerp_colors(stops, p(bottom) - p(top))
    return np.repeat(col[:, None, :], W, axis=1)


def glow_layer():
    return Image.new('RGBA', (W, H), (0, 0, 0, 0))


def add_glow(base, layer, radius, strength=1.0):
    blurred = layer.filter(ImageFilter.GaussianBlur(p(radius)))
    arr = np.asarray(base).astype(np.float32)
    g = np.asarray(blurred).astype(np.float32)
    a = g[..., 3:4] / 255.0 * strength
    arr[..., :3] = arr[..., :3] + g[..., :3] * a  # screen-ish additive
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def composite(base, layer):
    return Image.alpha_composite(base.convert('RGBA'), layer).convert('RGB')


# ---------------------------------------------------------------- 공통 요소
def sky_and_sea(sky_stops, sea_stops, sea_bottom=800):
    img = np.zeros((H, W, 3))
    img[:p(HORIZON)] = vgradient(0, HORIZON, sky_stops)
    img[p(HORIZON):p(sea_bottom)] = vgradient(HORIZON, sea_bottom, sea_stops)
    return Image.fromarray(img.astype(np.uint8))


def water_texture(img, top, bottom, light, dark, density=900, seed=1):
    rnd = random.Random(seed)
    layer = glow_layer()
    d = ImageDraw.Draw(layer)
    for _ in range(density):
        y = rnd.uniform(top, bottom)
        t = (y - top) / (bottom - top)
        length = 6 + 40 * t * rnd.random()
        x = rnd.uniform(-20, 660)
        col = light if rnd.random() < 0.5 else dark
        d.line([(p(x), p(y)), (p(x + length), p(y))], fill=col, width=max(1, p(0.6 + 1.4 * t)))
    return composite(img, layer.filter(ImageFilter.GaussianBlur(S * 0.6)))


def skyline(d, color, lit=None, seed=3):
    """왼쪽 해운대·마린시티 방향 고층 빌딩 실루엣"""
    rnd = random.Random(seed)
    x = -4
    while x < 200:
        w = rnd.uniform(9, 17)
        fall = max(0.0, (x - 40) / 160)
        top = HORIZON - rnd.uniform(40, 125) * (1 - 0.8 * fall) - 8
        d.rectangle([p(x), p(top), p(x + w), p(HORIZON)], fill=color)
        if rnd.random() < 0.3:
            d.polygon([(p(x), p(top)), (p(x + w), p(top)), (p(x + w / 2), p(top - rnd.uniform(6, 14)))], fill=color)
        if lit:
            for wy in np.arange(top + 5, HORIZON - 4, 5.5):
                for wx in np.arange(x + 2, x + w - 2, 3.6):
                    if rnd.random() < 0.3:
                        d.rectangle([p(wx), p(wy), p(wx + 1.4), p(wy + 2)], fill=rnd.choice(lit))
        x += w + rnd.uniform(-3, 2)


TOWERS = (252, 520)
TOP_Y, DECK_Y = 300, 368


def cable_y(x):
    a, b = TOWERS
    if a <= x <= b:
        m = (a + b) / 2
        return DECK_Y - 4 - (DECK_Y - 4 - TOP_Y) * ((x - m) / (m - a)) ** 2
    if x < a:
        return TOP_Y + (DECK_Y - 2 - TOP_Y) * ((a - x) / (a - 118)) ** 1.3
    return TOP_Y + (DECK_Y - 2 - TOP_Y) * ((x - b) / (660 - b)) ** 1.3


def bridge(img, color, hanger_alpha=110, lights=None, light_glow=None, deck_light=None):
    layer = glow_layer()
    d = ImageDraw.Draw(layer)
    # 교각
    for x in range(140, 660, 58):
        d.rectangle([p(x - 2), p(DECK_Y + 8), p(x + 2), p(HORIZON + 2)], fill=color)
    # 상판(2층)
    d.polygon([(p(60), p(DECK_Y + 10)), (p(120), p(DECK_Y)), (p(660), p(DECK_Y)), (p(660), p(DECK_Y + 5)),
               (p(122), p(DECK_Y + 5)), (p(64), p(DECK_Y + 13))], fill=color)
    d.rectangle([p(120), p(DECK_Y + 8), p(660), p(DECK_Y + 11)], fill=color)
    # 행어
    hc = color[:3] + (hanger_alpha,)
    for x in range(124, 660, 7):
        if abs(x - TOWERS[0]) < 5 or abs(x - TOWERS[1]) < 5:
            continue
        d.line([(p(x), p(cable_y(x))), (p(x), p(DECK_Y))], fill=hc, width=max(1, S // 2))
    # 주케이블
    pts = [(p(x), p(cable_y(x))) for x in np.arange(118, 661, 2)]
    d.line(pts, fill=color, width=p(1.6))
    # 주탑 (양 기둥 + 가로보)
    for tx in TOWERS:
        for off in (-4, 4):
            d.rectangle([p(tx + off - 2), p(TOP_Y - 4), p(tx + off + 2), p(HORIZON + 2)], fill=color)
        for by in (TOP_Y, TOP_Y + 26, DECK_Y - 16):
            d.rectangle([p(tx - 6), p(by), p(tx + 6), p(by + 3)], fill=color)
    img = composite(img, layer)

    if lights:
        gl = glow_layer()
        gd = ImageDraw.Draw(gl)
        for i, x in enumerate(np.arange(122, 660, 6)):
            c = lights[i % len(lights)]
            y = cable_y(x)
            r = 1.3
            gd.ellipse([p(x - r), p(y - r), p(x + r), p(y + r)], fill=c + (255,))
        for tx in TOWERS:
            for yy in range(TOP_Y, HORIZON, 5):
                gd.ellipse([p(tx - 5), p(yy), p(tx - 3), p(yy + 2)], fill=lights[0] + (255,))
                gd.ellipse([p(tx + 3), p(yy), p(tx + 5), p(yy + 2)], fill=lights[0] + (255,))
        if deck_light:
            gd.line([(p(120), p(DECK_Y + 2)), (p(660), p(DECK_Y + 2))], fill=deck_light + (255,), width=p(1.4))
            gd.line([(p(120), p(DECK_Y + 9)), (p(660), p(DECK_Y + 9))], fill=deck_light + (200,), width=p(1))
        img = composite(img, gl)
        img = add_glow(img, gl, 3, light_glow or 1.2)
        img = add_glow(img, gl, 10, (light_glow or 1.2) * 0.6)
    return img


def reflections(img, colors, top=HORIZON + 4, bottom=480, seed=7, count=260):
    rnd = random.Random(seed)
    layer = glow_layer()
    d = ImageDraw.Draw(layer)
    for _ in range(count):
        x = rnd.uniform(120, 660)
        y = rnd.uniform(top, bottom)
        t = (y - top) / (bottom - top)
        c = rnd.choice(colors)
        a = int(200 * (1 - t) * rnd.uniform(0.4, 1))
        w = rnd.uniform(2, 7)
        d.line([(p(x - w), p(y)), (p(x + w), p(y))], fill=c + (a,), width=S)
    img = composite(img, layer)
    return add_glow(img, layer, 2, 0.8)


def stars(img, n, seed=5, bottom=300):
    rnd = random.Random(seed)
    layer = glow_layer()
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        x, y = rnd.uniform(0, 640), rnd.uniform(0, bottom)
        r = rnd.choice([0.5, 0.6, 0.8, 1.1])
        a = int(rnd.uniform(90, 255) * (1 - y / bottom * 0.6))
        d.ellipse([p(x - r), p(y - r), p(x + r), p(y + r)], fill=(255, 255, 255, a))
    return add_glow(composite(img, layer), layer, 1.5, 0.8)


def shore(img, sand_stops, foam=(255, 255, 255), wet=None, top=455, seed=11):
    """앞쪽 모래사장 + 파도 거품"""
    arr = np.asarray(img).astype(np.float32)
    rnd = random.Random(seed)
    xs = np.arange(W)
    edge = p(top) + (p(10) * np.sin(xs / p(90) + 1.2) + p(6) * np.sin(xs / p(37))).astype(int)
    sand = vgradient(top - 12, 800, sand_stops)
    for x in range(W):
        e = max(edge[x], p(top - 12))
        arr[e:, x, :] = sand[e - p(top - 12):, x, :]
    img = Image.fromarray(arr.astype(np.uint8))
    layer = glow_layer()
    d = ImageDraw.Draw(layer)
    if wet:
        pts = [(x, edge[x] - p(2)) for x in range(0, W, 4)]
        pts2 = [(x, edge[x] + p(26) + int(p(5) * math.sin(x / p(60)))) for x in range(W - 1, -1, -4)]
        d.polygon(pts + pts2, fill=wet)
    for k, off in enumerate((0, 6, 14)):
        pts = [(x, edge[x] + p(off) + int(p(2) * math.sin(x / p(23) + k))) for x in range(0, W, 3)]
        d.line(pts, fill=foam + (220 - k * 60,), width=p(2.2 - k * 0.5))
    for _ in range(140):
        x = rnd.uniform(0, 640)
        yy = edge[min(W - 1, p(x))] / S + rnd.uniform(-3, 16)
        d.ellipse([p(x), p(yy), p(x + rnd.uniform(3, 12)), p(yy + 1.4)], fill=foam + (rnd.randint(80, 180),))
    return composite(img, layer.filter(ImageFilter.GaussianBlur(S * 0.7)))


# ---------------------------------------------------------------- 타이틀 / 문구 상자 / 로고
def overlay(img, quote_color=(138, 90, 58), shadow=0.35, bottom_shade=0.35):
    arr = np.asarray(img).astype(np.float32)
    ys = np.clip((np.arange(H) / S - 650) / 150, 0, 1)[:, None, None]
    arr *= 1 - bottom_shade * ys
    img = Image.fromarray(arr.astype(np.uint8))
    layer = glow_layer()
    d = ImageDraw.Draw(layer)
    marcellus = str(FONTS / 'MarcellusSC-Regular.ttf')
    small = ImageFont.truetype(str(FONTS / 'NotoSans-Regular.ttf'), p(10.5))
    kr = ImageFont.truetype(str(FONTS / 'NotoSansKR-Bold.ttf'), p(21))

    def spaced(text, y, font, spacing, fill):
        widths = [d.textlength(ch, font=font) for ch in text]
        total = sum(widths) + spacing * S * (len(text) - 1)
        x = W / 2 - total / 2
        for ch, w in zip(text, widths):
            d.text((x, p(y)), ch, font=font, fill=fill, anchor='lm')
            x += w + spacing * S

    spaced('GWANGANRI · BUSAN', 33, small, 5, (255, 255, 255, 225))
    for text, y, size in (('MY', 88, 34), ('GWANGANRI', 142, 54), ('MOMENT', 190, 38)):
        f = ImageFont.truetype(marcellus, p(size))
        d.text((W / 2, p(y)), text, font=f, fill=(255, 255, 255, 250), anchor='mm')
    # 물결 장식선
    pts = [(p(270 + t), p(236 - 3 * math.sin((t / 100) * math.pi * 2) * (1 - abs(t - 50) / 50))) for t in range(0, 101)]
    d.line(pts, fill=(255, 255, 255, 230), width=p(1.6))

    # 하단 로고: 작은 현수교 라인 + 한글
    lx, ly, lw = 320, 712, 86
    d.line([(p(lx - lw), p(ly + 8)), (p(lx + lw), p(ly + 8))], fill=(255, 255, 255, 240), width=p(1.6))
    for tx in (lx - 36, lx + 36):
        d.rectangle([p(tx - 1.5), p(ly - 14), p(tx + 1.5), p(ly + 12)], fill=(255, 255, 255, 240))
    cable = [(p(x), p(ly - 13 + 17 * (1 - ((x - lx) / 36) ** 2))) for x in np.arange(lx - 36, lx + 36.5, 1)]
    d.line(cable, fill=(255, 255, 255, 240), width=p(1.2))
    for side in (-1, 1):
        d.line([(p(lx + side * 36), p(ly - 13)), (p(lx + side * lw), p(ly + 6))], fill=(255, 255, 255, 240), width=p(1.2))
    for x in range(lx - 80, lx + 81, 6):
        if abs(abs(x - lx) - 36) < 2:
            continue
        y0 = ly - 13 + 17 * (1 - ((x - lx) / 36) ** 2) if abs(x - lx) < 36 else ly - 13 + 19 * (abs(x - lx) - 36) / (lw - 36)
        d.line([(p(x), p(y0)), (p(x), p(ly + 8))], fill=(255, 255, 255, 170), width=max(1, S // 2))
    d.text((W / 2, p(752)), '광안대교 초콜릿', font=kr, fill=(255, 255, 255, 250), anchor='mm')

    # 글씨 그림자
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sh.putalpha(layer.getchannel('A').point(lambda v: int(v * shadow)))
    sh = sh.filter(ImageFilter.GaussianBlur(p(3)))
    img = Image.alpha_composite(img.convert('RGBA'), sh)
    img = Image.alpha_composite(img, layer)

    # 문구 상자 (반투명 흰 유리)
    box = (83, 495, 560, 672)
    blur = img.filter(ImageFilter.GaussianBlur(p(8)))
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([p(box[0]), p(box[1]), p(box[2]), p(box[3])], radius=p(14), fill=255)
    img = Image.composite(blur, img, mask)
    white = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    wd = ImageDraw.Draw(white)
    wd.rounded_rectangle([p(box[0]), p(box[1]), p(box[2]), p(box[3])], radius=p(14), fill=(255, 255, 255, 228),
                         outline=(255, 255, 255, 255), width=p(1.5))
    img = Image.alpha_composite(img, white)
    # 따옴표
    q = ImageFont.truetype(str(FONTS / 'georgia.ttf'), p(64))
    qd = ImageDraw.Draw(img)
    qd.text((p(118), p(500)), '\u201c', font=q, fill=quote_color + (255,), anchor='mm')
    qd.text((p(548), p(690)), '\u201d', font=q, fill=quote_color + (255,), anchor='mm')
    return img.convert('RGB')


def finish(img, name):
    out = img.resize((640, 800), Image.LANCZOS)
    path = ROOT / 'images' / f'card-{name}.jpg'
    out.save(path, quality=86, optimize=True, progressive=True)
    print(path.name, path.stat().st_size)


# ---------------------------------------------------------------- 장면
def night():
    img = sky_and_sea(
        [(0, (8, 12, 40)), (0.55, (22, 34, 86)), (0.85, (58, 52, 120)), (1, (96, 70, 140))],
        [(0, (30, 30, 80)), (0.3, (14, 20, 56)), (1, (6, 10, 30))])
    img = stars(img, 160)
    d = ImageDraw.Draw(img)
    skyline(d, (14, 16, 40), lit=[(255, 214, 140), (255, 240, 200), (140, 200, 255)])
    img = water_texture(img, HORIZON, 800, (60, 80, 150, 90), (0, 0, 20, 90))
    img = reflections(img, [(120, 160, 255), (200, 120, 255), (90, 230, 255), (255, 210, 140)], bottom=640, count=620)
    img = bridge(img, (20, 22, 52, 255), 90,
                 lights=[(110, 170, 255), (180, 120, 255), (90, 230, 255)], light_glow=1.6, deck_light=(255, 214, 150))
    img = shore(img, [(0, (40, 38, 62)), (1, (22, 20, 36))], foam=(190, 205, 255), wet=(30, 34, 70, 140), top=655)
    return overlay(img, quote_color=(92, 88, 170))


def drone():
    img = sky_and_sea(
        [(0, (4, 6, 24)), (0.6, (12, 20, 58)), (1, (40, 40, 96))],
        [(0, (22, 24, 66)), (0.35, (8, 12, 38)), (1, (4, 6, 22))])
    img = stars(img, 60, seed=9)
    d = ImageDraw.Draw(img)
    skyline(d, (10, 12, 30), lit=[(255, 214, 140), (170, 210, 255)], seed=4)
    img = water_texture(img, HORIZON, 800, (50, 70, 140, 80), (0, 0, 10, 90), seed=3)

    # 드론 편대: 하트 + 초콜릿 한 조각 + 흩어진 빛
    gl = glow_layer()
    gd = ImageDraw.Draw(gl)
    rnd = random.Random(21)
    cx, cy, sc = 470, 282, 3.1
    for t in np.linspace(0, 2 * math.pi, 120, endpoint=False):
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        px, py = cx + x * sc, cy - y * sc
        gd.ellipse([p(px - 1.3), p(py - 1.3), p(px + 1.3), p(py + 1.3)], fill=(255, 120, 190, 255))
    for t in np.linspace(0, 2 * math.pi, 70, endpoint=False):
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        px, py = cx + x * sc * 0.6, cy - y * sc * 0.6
        gd.ellipse([p(px - 1.1), p(py - 1.1), p(px + 1.1), p(py + 1.1)], fill=(255, 220, 240, 255))
    # 왼쪽: 초콜릿 바(격자) 모양
    bx, by = 150, 250
    for i in range(4):
        for j in range(3):
            for k in range(5):
                gd.ellipse([p(bx + i * 20 + k * 3.6 - 1), p(by + j * 16 - 1), p(bx + i * 20 + k * 3.6 + 1), p(by + j * 16 + 1)], fill=(255, 196, 120, 255))
                gd.ellipse([p(bx + i * 20 - 1), p(by + j * 16 + k * 3 - 1), p(bx + i * 20 + 1), p(by + j * 16 + k * 3 + 1)], fill=(255, 196, 120, 255))
    for k in range(22):
        gd.ellipse([p(bx + k * 3.7 - 1), p(by + 48 - 1), p(bx + k * 3.7 + 1), p(by + 48 + 1)], fill=(255, 196, 120, 255))
    for k in range(17):
        gd.ellipse([p(bx + 80 - 1), p(by + k * 3 - 1), p(bx + 80 + 1), p(by + k * 3 + 1)], fill=(255, 196, 120, 255))
    for _ in range(90):
        x, y = rnd.uniform(20, 620), rnd.uniform(250, 340)
        c = rnd.choice([(120, 200, 255), (255, 255, 255), (190, 140, 255)])
        gd.ellipse([p(x - 0.9), p(y - 0.9), p(x + 0.9), p(y + 0.9)], fill=c + (rnd.randint(120, 255),))
    img = composite(img, gl)
    img = add_glow(img, gl, 2.5, 1.4)
    img = add_glow(img, gl, 9, 0.9)
    img = reflections(img, [(255, 120, 190), (255, 196, 120), (120, 200, 255)], bottom=640, count=480, seed=8)
    img = bridge(img, (16, 18, 44, 255), 80, lights=[(120, 190, 255), (255, 255, 255)], light_glow=1.1, deck_light=(255, 214, 150))
    img = shore(img, [(0, (34, 32, 54)), (1, (16, 14, 28))], foam=(180, 200, 255), wet=(24, 28, 60, 140), top=655, seed=12)
    return overlay(img, quote_color=(176, 70, 130))


def beach():
    img = sky_and_sea(
        [(0, (38, 110, 200)), (0.6, (110, 175, 235)), (1, (200, 228, 248))],
        [(0, (70, 150, 200)), (0.25, (40, 150, 190)), (1, (30, 170, 180))])
    # 구름
    cl = glow_layer()
    cd = ImageDraw.Draw(cl)
    rnd = random.Random(31)
    for cx, cy, n in ((110, 270, 9), (330, 250, 7), (560, 285, 10), (470, 60, 6), (60, 90, 5)):
        for _ in range(n):
            x, y = cx + rnd.uniform(-50, 50), cy + rnd.uniform(-10, 10)
            r = rnd.uniform(14, 30)
            cd.ellipse([p(x - r * 1.6), p(y - r), p(x + r * 1.6), p(y + r)], fill=(255, 255, 255, 110))
    img = composite(img, cl.filter(ImageFilter.GaussianBlur(p(7))))
    d = ImageDraw.Draw(img)
    skyline(d, (150, 175, 200), seed=6)
    img = water_texture(img, HORIZON, 800, (255, 255, 255, 70), (20, 90, 140, 60), density=1100, seed=5)
    img = bridge(img, (120, 140, 165, 255), 120)
    img = shore(img, [(0, (236, 214, 176)), (0.4, (226, 200, 158)), (1, (206, 176, 132))],
                foam=(255, 255, 255), wet=(196, 170, 130, 150), top=458, seed=13)
    # 발자국
    fp = glow_layer()
    fd = ImageDraw.Draw(fp)
    for i in range(9):
        t = i / 8
        x = 360 + 180 * t + (7 if i % 2 else -7)
        y = 800 - 330 * t
        s = 1 - 0.55 * t
        fd.ellipse([p(x - 4 * s), p(y - 7 * s), p(x + 4 * s), p(y + 7 * s)], fill=(160, 128, 90, 150))
    img = composite(img, fp.filter(ImageFilter.GaussianBlur(S * 0.8)))
    # 햇살
    sun = glow_layer()
    ImageDraw.Draw(sun).ellipse([p(560), p(-40), p(700), p(100)], fill=(255, 250, 220, 200))
    img = add_glow(img, sun, 30, 0.9)
    return overlay(img, quote_color=(40, 120, 170), shadow=0.55, bottom_shade=0.45)


def sunrise():
    img = sky_and_sea(
        [(0, (40, 44, 104)), (0.35, (120, 90, 160)), (0.65, (232, 140, 150)), (0.88, (255, 186, 130)), (1, (255, 214, 150))],
        [(0, (240, 170, 140)), (0.2, (150, 110, 150)), (1, (50, 50, 96))])
    # 해
    sx, sy = 386, HORIZON + 2
    sun = glow_layer()
    ImageDraw.Draw(sun).ellipse([p(sx - 22), p(sy - 22), p(sx + 22), p(sy + 22)], fill=(255, 236, 190, 255))
    sun_top = sun.crop((0, 0, W, p(HORIZON)))
    full = glow_layer()
    full.paste(sun_top, (0, 0))
    img = composite(img, full)
    img = add_glow(img, full, 18, 1.2)
    img = add_glow(img, full, 60, 0.7)
    # 얇은 구름
    cl = glow_layer()
    cd = ImageDraw.Draw(cl)
    rnd = random.Random(41)
    for _ in range(18):
        x, y = rnd.uniform(-40, 680), rnd.uniform(250, 360)
        cd.ellipse([p(x - 70), p(y - 4), p(x + 70), p(y + 4)], fill=(255, 190, 170, 90))
    img = composite(img, cl.filter(ImageFilter.GaussianBlur(p(3))))
    d = ImageDraw.Draw(img)
    skyline(d, (70, 56, 100), seed=7)
    img = water_texture(img, HORIZON, 800, (255, 200, 170, 80), (40, 30, 80, 70), seed=6)
    # 해 기둥 반사
    col = glow_layer()
    cd = ImageDraw.Draw(col)
    for i in range(320):
        y = HORIZON + 3 + i * 0.8
        w = 12 + i * 0.25 + rnd.uniform(-6, 6)
        cd.line([(p(sx - w), p(y)), (p(sx + w), p(y))], fill=(255, 220, 170, int(200 * (1 - i / 320))), width=S)
    img = composite(img, col)
    img = add_glow(img, col, 4, 0.5)
    img = bridge(img, (58, 44, 86, 255), 110)
    img = shore(img, [(0, (170, 120, 130)), (1, (90, 66, 96))], foam=(255, 230, 220), wet=(150, 110, 130, 140), top=650, seed=14)
    return overlay(img, quote_color=(190, 100, 90))


if __name__ == '__main__':
    for name, fn in (('night', night), ('drone', drone), ('beach', beach), ('sunrise', sunrise)):
        finish(fn(), name)
