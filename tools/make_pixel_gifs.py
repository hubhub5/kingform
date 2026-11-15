"""킹율 도트 GIF/아이콘 생성기.

사용: python3 tools/make_pixel_gifs.py
입력: src/*.png (킹율 사진)  출력: assets/*.gif, assets/*.png (원본 해상도, CSS에서 pixelated 확대)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "src", ROOT / "assets"
OUT.mkdir(exist_ok=True)

INK = (43, 22, 84)          # 외곽선 진보라
PINK = (255, 79, 163)
YELLOW = (255, 214, 64)
WHITE = (255, 255, 255)


# ---------------------------------------------------------------- 공통 유틸
def pixelate(img: Image.Image, size: int, colors: int) -> Image.Image:
    """RGBA 이미지를 size 정사각형 도트로 축소하고 팔레트를 줄인다(알파는 0/255로)."""
    small = img.resize((size, size), Image.LANCZOS)
    alpha = small.getchannel("A").point(lambda a: 255 if a > 140 else 0)
    rgb = small.convert("RGB")
    rgb = ImageEnhance.Contrast(rgb).enhance(1.15)
    rgb = ImageEnhance.Color(rgb).enhance(1.1)
    q = rgb.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")
    out = q.convert("RGBA")
    out.putalpha(alpha)
    return out


def outline(img: Image.Image, color=INK) -> Image.Image:
    """알파 경계 바깥쪽 1px 외곽선."""
    w, h = img.size
    a = img.getchannel("A")
    out = img.copy()
    px, ap = out.load(), a.load()
    for y in range(h):
        for x in range(w):
            if ap[x, y]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and ap[nx, ny]:
                    px[x, y] = color + (255,)
                    break
    return out


def save_gif(frames, path, durations):
    """RGBA 프레임들을 투명 GIF로 저장 (투명 인덱스 0)."""
    # 모든 프레임을 하나의 공용 팔레트(254색)로 양자화하고, 인덱스 255를 투명으로 예약
    strip = Image.new("RGB", (frames[0].width * len(frames), frames[0].height), (0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f.convert("RGB"), (i * f.width, 0), mask=f.getchannel("A"))
    master = strip.quantize(colors=254, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = master.getpalette()[: 254 * 3]
    pal += [0] * (254 * 3 - len(pal)) + [255, 0, 255, 1, 2, 3]
    pal_frames = []
    for f in frames:
        p = f.convert("RGB").quantize(palette=master, dither=Image.NONE)
        p.putpalette(pal)
        a, px = f.getchannel("A").load(), p.load()
        for y in range(f.height):
            for x in range(f.width):
                if a[x, y] < 128:
                    px[x, y] = 255
        pal_frames.append(p)
    pal_frames[0].save(
        path, save_all=True, append_images=pal_frames[1:], duration=durations,
        loop=0, disposal=2, transparency=255, optimize=False,
    )


def canvas(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def draw_map(rows, palette):
    """문자열 도트맵 -> RGBA. '.'은 투명."""
    h, w = len(rows), max(len(r) for r in rows)
    im = canvas(w, h)
    px = im.load()
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c != "." and c in palette:
                px[x, y] = palette[c] + (255,)
    return im


HEART = [
    ".pp.pp.",
    "pwppppp",
    "ppppppp",
    ".ppppp.",
    "..ppp..",
    "...p...",
]
HEART_PAL = {"p": PINK, "w": WHITE}

SPARK = [
    "..y..",
    "..y..",
    "yyWyy",
    "..y..",
    "..y..",
]
SPARK_PAL = {"y": YELLOW, "W": WHITE}

ANGER = [
    ".r...r.",
    "rr...rr",
    ".......",
    ".......",
    "rr...rr",
    ".r...r.",
]
ANGER_PAL = {"r": (232, 36, 60)}


# ---------------------------------------------------------------- 메인 마스코트 (스튜디오 사진)
def studio_sprite(size=72):
    im = Image.open(SRC / "yul-studio.png").convert("RGB")
    # 라벤더 배경 키잉: 파랑이 초록보다 확연히 크고 밝은 픽셀 = 배경
    mask = Image.new("L", im.size, 255)
    src, mp = im.load(), mask.load()
    W, H = im.size
    for y in range(H):
        for x in range(W):
            r, g, b = src[x, y]
            if b - g > 22 and b > 170 and r > 150:
                mp[x, y] = 0
    mask = mask.filter(ImageFilter.MedianFilter(7))
    rgba = im.convert("RGBA")
    rgba.putalpha(mask)
    return outline(pixelate(rgba, size, 14))


def eyes_closed(sprite, eyes, fur):
    """눈 위치에 감은 눈(가로 선)을 그린다."""
    f = sprite.copy()
    d = ImageDraw.Draw(f)
    for (cx, cy) in eyes:
        d.rectangle([cx - 2, cy - 2, cx + 2, cy + 2], fill=fur + (255,))
        d.line([cx - 2, cy, cx + 2, cy], fill=INK + (255,))
        d.point([(cx - 3, cy - 1), (cx + 3, cy - 1)], fill=INK + (255,))
    return f


def make_main():
    s = studio_sprite(72)
    s.save(OUT / "yul-sprite.png")
    eyes = [(29, 21), (47, 21)]
    fur = s.getpixel((38, 16))[:3]
    closed = eyes_closed(s, eyes, fur)
    heart, spark = draw_map(HEART, HEART_PAL), draw_map(SPARK, SPARK_PAL)
    W, H = 96, 88
    frames, durs = [], []
    bounce = [0, -1, -2, -3, -2, -1, 0, 0, 0, 0, 0, 0]
    for i, dy in enumerate(bounce):
        c = canvas(W, H)
        body = closed if i in (8, 9) else s
        c.alpha_composite(body, (12, 12 + dy))
        # 하트가 오른쪽 위로 떠오름
        hy = 30 - i * 2
        if i < 10:
            c.alpha_composite(heart, (82, max(0, hy)))
        if i % 4 < 2:
            c.alpha_composite(spark, (4, 8))
        else:
            c.alpha_composite(spark, (86, 60))
        frames.append(c)
        durs.append(140 if i not in (8, 9) else 90)
    save_gif(frames, OUT / "yul-main.gif", durs)


def make_angry():
    """이스터에그: '나가 살아!' 듣고 킹받은 킹율."""
    s = studio_sprite(72)
    anger = draw_map(ANGER, ANGER_PAL).resize((14, 12), Image.NEAREST)
    W, H = 96, 88
    frames = []
    offs = [(-4, 0), (4, -2), (-3, -3), (5, 0), (-5, -1), (3, -3)]
    for i, (dx, dy) in enumerate(offs):
        c = canvas(W, H)
        body = s.rotate(8 if i % 2 else -8, resample=Image.NEAREST, expand=False)
        # 붉은 기운
        r, g, b, a = body.split()
        tinted = Image.merge("RGBA", (r.point(lambda v: min(255, v + 60)), g.point(lambda v: int(v * .75)), b.point(lambda v: int(v * .85)), a))
        c.alpha_composite(tinted if i % 2 else body, (12 + dx, 12 + dy))
        c.alpha_composite(anger, (74 if i % 2 else 6, 4))
        d = ImageDraw.Draw(c)
        # 스피드 라인
        for k in range(3):
            y = 30 + k * 12 + (i % 2) * 4
            d.line([(0, y), (6, y)], fill=INK + (255,))
            d.line([(W - 7, y + 3), (W - 1, y + 3)], fill=INK + (255,))
        frames.append(c)
    save_gif(frames, OUT / "yul-angry.gif", [60] * len(frames))


# ---------------------------------------------------------------- 완료 화면 (클로즈업 사진)
def make_done():
    im = Image.open(SRC / "yul-closeup.png").convert("RGBA")
    # 얼굴 중심 원형 크롭
    box = (60, 40, 1080, 1060)
    face = im.crop(box)
    n = face.size[0]
    m = Image.new("L", face.size, 0)
    ImageDraw.Draw(m).ellipse([0, 0, n - 1, n - 1], fill=255)
    face.putalpha(m)
    s = outline(pixelate(face, 64, 16))
    s.save(OUT / "yul-face.png")
    heart, spark = draw_map(HEART, HEART_PAL), draw_map(SPARK, SPARK_PAL)
    W, H = 84, 80
    frames = []
    for i in range(8):
        c = canvas(W, H)
        dy = [0, -1, -2, -1, 0, 0, -1, 0][i]
        c.alpha_composite(s, (10, 10 + dy))
        pos = [(2, 4), (74, 10), (76, 60), (0, 56)]
        c.alpha_composite(spark, pos[i % 4])
        c.alpha_composite(heart, (70 - (i % 2), 0 + (i % 2)))
        frames.append(c)
    save_gif(frames, OUT / "yul-done.gif", [130] * 8)


def make_icon():
    """작은 얼굴 아이콘(파비콘·진행바 러너 머리)."""
    im = Image.open(SRC / "yul-window.png").convert("RGBA")
    face = im.crop((205, 60, 525, 380))
    m = Image.new("L", face.size, 0)
    ImageDraw.Draw(m).ellipse([0, 0, face.size[0] - 1, face.size[1] - 1], fill=255)
    face.putalpha(m)
    ic = outline(pixelate(face, 30, 12))
    c = canvas(32, 32)
    c.alpha_composite(ic, (1, 1))
    c.save(OUT / "yul-icon.png")
    c.resize((128, 128), Image.NEAREST).save(OUT / "favicon.png")


# ---------------------------------------------------------------- 달리는 미니 킹율 (손도트)
RUN_PAL = {"k": INK, "g": (120, 124, 140), "G": (160, 164, 178), "w": WHITE, "p": (240, 150, 180), "e": (20, 10, 30)}
RUN_A = [
    "..........................",
    "...................kk.....",
    "..................kgpk....",
    "................kkgggkk...",
    "...............kggegggwk..",
    "..............kgggggggkk..",
    ".kk...........kgwwgkkk....",
    "k.gk.kkkkkkkkkkgwwgk......",
    "...kkgGGGGGGGGGgwwk.......",
    "....kgGGGGGGGGGgwk........",
    "....kgggggggggggwk........",
    ".....kgggkkkkkkgk.........",
    "....kgk.k.....kgk.........",
    "...kgk...k...kgk..........",
    "..kk......k.kk............",
    "...........kk.............",
]
RUN_B = [
    "..........................",
    "...................kk.....",
    "..................kgpk....",
    "................kkgggkk...",
    "...............kggegggwk..",
    ".kk...........kgggggggkk..",
    "k.gk..........kgwwgkkk....",
    "...kkkkkkkkkkkkgwwgk......",
    "....kgGGGGGGGGGgwwk.......",
    "....kgGGGGGGGGGgwk........",
    "....kgggggggggggwk........",
    ".....kgkkkkkkkkgk.........",
    "......kgk...kgk...........",
    ".......kgk.kgk............",
    "........kk.kk.............",
    "..........................",
]


def make_runner():
    a, b = draw_map(RUN_A, RUN_PAL), draw_map(RUN_B, RUN_PAL)
    frames = []
    for i, f in enumerate([a, b, a, b]):
        c = canvas(28, 18)
        c.alpha_composite(f, (1, 1 if i % 2 else 2))
        frames.append(c)
    save_gif(frames, OUT / "yul-run.gif", [110] * 4)


# ---------------------------------------------------------------- 소품 아이콘 (16x16 손도트)
P = {
    "k": INK, "w": WHITE, "p": PINK, "y": YELLOW, "Y": (255, 170, 30), "r": (232, 36, 60),
    "b": (92, 140, 255), "B": (40, 80, 200), "g": (90, 200, 120), "G": (40, 140, 80),
    "c": (250, 236, 210), "o": (190, 120, 60), "l": (180, 160, 240), "s": (170, 175, 190),
    "a": (120, 220, 240), "f": (255, 190, 210),
}
ICONS = {
    "bone": [
        "................",
        "................",
        ".kk..........kk.",
        "kwwk........kwwk",
        "kwwwkkkkkkkkwwwk",
        ".kwwwwwwwwwwwwk.",
        ".kwwwwwwwwwwwwk.",
        "kwwwkkkkkkkkwwwk",
        "kwwk........kwwk",
        ".kk..........kk.",
    ],
    "heart": [
        ".kkk...kkk.",
        "kpwpk.kpppk",
        "kpwppkppppk",
        "kpppppppppk",
        ".kpppppppk.",
        "..kpppppk..",
        "...kpppk...",
        "....kpk....",
        ".....k.....",
    ],
    "coin": [
        "...kkkkk...",
        "..kyyyyyk..",
        ".kyywyyyYk.",
        "kyywykkyyYk",
        "kyywyykyyYk",
        "kyyyyykyyYk",
        "kyyyykkkyYk",
        ".kyyyyyyYk.",
        "..kYYYYYk..",
        "...kkkkk...",
    ],
    "star": [
        ".....k.....",
        "....kyk....",
        "....kyk....",
        "kkkkkyykkkk",
        "kyyyywyyyyk",
        ".kyyyyyyyk.",
        "..kyyyyyk..",
        ".kyyykyyyk.",
        ".kyyk.kyyk.",
        "kkk.....kkk",
    ],
    "floppy": [
        "kkkkkkkkkkkk.",
        "kbbkwwwwkbbbk",
        "kbbkwwwwkbbbk",
        "kbbkkkkkkbbbk",
        "kbbbbbbbbbbbk",
        "kbwwwwwwwwwbk",
        "kbwkkkkkkkwbk",
        "kbwwwwwwwwwbk",
        "kbwkkkkkwwwbk",
        "kbwwwwwwwwwbk",
        "kkkkkkkkkkkkk",
    ],
    "soju": [
        ".kkkkkkk.",
        ".kaaaaak.",
        ".kwwwwwk.",
        ".kyyyyyk.",
        ".kyyyyyk.",
        ".kyywyyk.",
        ".kyywyyk.",
        ".kyyyyyk.",
        "..kyyyk..",
        "..kkkkk..",
    ],
    "cake": [
        "....r.r.r....",
        "....y.y.y....",
        "....k.k.k....",
        "..kkkkkkkkk..",
        "..kfpfpfpfk..",
        "..kcccccccck.",
        ".kkkkkkkkkkk.",
        ".kfffffffffk.",
        ".kpwpwpwpwpk.",
        ".kccccccccck.",
        "kkkkkkkkkkkkk",
    ],
    # 관심 주제 아이템
    "shield": [
        "kkkkkkkkkkk",
        "kbbbbwbbbbk",
        "kbbbkwkbbbk",
        "kbbkwwwkbbk",
        "kbbbkwkbbbk",
        "kbbbbbbbbbk",
        ".kbbbbbbbk.",
        ".kBbbbbbBk.",
        "..kBbbbBk..",
        "...kBBBk...",
        "....kkk....",
    ],
    "whistle": [
        "....kkkkkkkk",
        "...kyyyyyyyk",
        "kkkyyyyykkkk",
        "kyyykyyk....",
        "kyykkkyk....",
        "kyyykyyk....",
        ".kyyyyk.....",
        "..kkkk......",
    ],
    "aid": [
        "...kkkkk...",
        "..k.....k..",
        "kkkkkkkkkkk",
        "kwwwwrwwwwk",
        "kwwwwrwwwwk",
        "kwwrrrrrwwk",
        "kwwwwrwwwwk",
        "kwwwwrwwwwk",
        "kkkkkkkkkkk",
    ],
    "food": [
        "..kkkkkkk..",
        ".kcccccccck",
        "kkkkkkkkkkk",
        "kooooooooook",
        "koowwwwwook",
        "koowpkpwook",
        "koowwwwwook",
        "kooooooooook",
        "kkkkkkkkkkk",
    ],
    "scissors": [
        "k.......k..",
        "kk.....kk..",
        ".kk...kk...",
        "..kk.kk....",
        "...kwk.....",
        "..kk.kk....",
        ".kpk.kpk...",
        "kp.pkp.pk..",
        "kp.pkp.pk..",
        ".kkk..kkk..",
    ],
    "bag": [
        "...kkkkk...",
        "...k...k...",
        "kkkkkkkkkkk",
        "kllllllllk.",
        "kllkllkllk.",
        "kllllllllk.",
        "kllkllkllk.",
        "kllllllllk.",
        "kkkkkkkkkkk",
        ".k.......k.",
    ],
    "ball": [
        "...kkkkk...",
        "..kgggggk..",
        ".kgwgggggk.",
        "kgwgkkkgggk",
        "kgggkgkgggk",
        "kgggkkkgggk",
        "kGggggggGGk",
        ".kGGgggGGk.",
        "..kGGGGGk..",
        "...kkkkk...",
    ],
    "angel": [
        "..kkkkkkk..",
        ".ky.....yk.",
        "..kkkkkkk..",
        "...........",
        "....kkk....",
        "...kwwwk...",
        "kk.kwwwk.kk",
        "kwkkwwwkkwk",
        ".kwwwwwwwk.",
        "..kkwwwkk..",
        "....kkk....",
    ],
    "pin": [
        "..kkkkk..",
        ".kpppppk.",
        "kppwwwppk",
        "kppwkwppk",
        "kppwwwppk",
        ".kpppppk.",
        "..kpppk..",
        "...kpk...",
        "....k....",
    ],
    "dog": [
        "..kk.....kk..",
        ".kgk.....kgk.",
        ".kgpkkkkkpgk.",
        ".kggggggggggk",
        "kgggeggggeggk",
        "kgggggwgggggk",
        ".kggwwwwwggk.",
        "..kgwwkwwgk..",
        "...kwwwwwk...",
        "....kkkkk....",
    ],
    "cat": [
        "kk.......kk",
        "kyk.....kyk",
        "kyykkkkkyyk",
        "kyyyyyyyyyk",
        "kyeyyyyyeyk",
        "kyyyypyyyyk",
        "kywyyyyywyk",
        ".kyyyyyyyk.",
        "..kkkkkkk..",
    ],
    "egg": [
        "...kkkk...",
        "..kwwwwk..",
        ".kwwwwwwk.",
        ".kwpwwpwk.",
        "kwwwwwwwwk",
        "kkwkwkwkkk",
        "kwkwkwkwwk",
        "kwwwwwwwwk",
        ".kwwwwwwk.",
        "..kkkkkk..",
    ],
    "paw": [
        ".kk...kk.",
        "kppk.kppk",
        ".kk...kk.",
        "kk.kkk.kk",
        "kpkpppkpk",
        ".kpppppk.",
        ".kpppppk.",
        "..kkkkk..",
    ],
    "stamp": [
        "...kkkkk...",
        "...kpppk...",
        "...kpppk...",
        "..kkkkkkk..",
        ".kpppppppk.",
        "kkkkkkkkkkk",
        "krrrrrrrrrk",
        "kkkkkkkkkkk",
    ],
}
P["e"] = (20, 10, 30)


def make_icons():
    for name, rows in ICONS.items():
        draw_map(rows, P).save(OUT / f"i-{name}.png")


# 선물상자: 닫힘 흔들림 -> 열림
GIFT_CLOSED = [
    "....kk..kk....",
    "...kyyk kyyk..",
    "....kkyykk....",
    "kkkkkkyykkkkkk",
    "kppppkyykppppk",
    "kkkkkkyykkkkkk",
    ".kpppkyykpppk.",
    ".kpwpkyykpppk.",
    ".kpppkyykpppk.",
    ".kpppkyykpppk.",
    ".kpppkyykpppk.",
    ".kkkkkkkkkkkk.",
]
GIFT_OPEN = [
    "kkkkkkkkkkkkkk",
    "kppppkyykppppk",
    "kkkkkkkkkkkkkk",
    "..............",
    "..............",
    ".kkkkkkkkkkkk.",
    ".kpppkyykpppk.",
    ".kpwpkyykpppk.",
    ".kpppkyykpppk.",
    ".kpppkyykpppk.",
    ".kpppkyykpppk.",
    ".kkkkkkkkkkkk.",
]


def make_gift():
    closed = draw_map([r.replace(" ", ".") for r in GIFT_CLOSED], P)
    opened = draw_map(GIFT_OPEN, P)
    spark = draw_map(SPARK, SPARK_PAL)
    # 흔들리는 상자
    frames = []
    for dx, rot in [(0, 0), (-1, 8), (1, -8), (-1, 10), (1, -10), (0, 0)]:
        c = canvas(24, 20)
        b = closed.rotate(rot, resample=Image.NEAREST, expand=True)
        c.alpha_composite(b, (12 - b.size[0] // 2 + dx, 19 - b.size[1]))
        frames.append(c)
    save_gif(frames, OUT / "gift-shake.gif", [90] * len(frames))
    # 열린 상자 + 반짝
    frames = []
    for i in range(6):
        c = canvas(24, 22)
        lid_y = 2 - (i % 2)
        c.alpha_composite(opened.crop((0, 0, 14, 3)), (5, lid_y))
        c.alpha_composite(opened.crop((0, 5, 14, 12)), (5, 15))
        c.alpha_composite(spark, [(0, 4), (19, 6), (9, 6)][i % 3])
        c.alpha_composite(spark, [(18, 12), (2, 12), (14, 2)][i % 3])
        frames.append(c)
    save_gif(frames, OUT / "gift-open.gif", [120] * 6)


def make_coin_spin():
    coin = draw_map(ICONS["coin"], P)
    frames = []
    for wscale in [11, 8, 4, 2, 4, 8]:
        c = canvas(11, 10)
        f = coin.resize((wscale, 10), Image.NEAREST)
        c.alpha_composite(f, ((11 - wscale) // 2, 0))
        frames.append(c)
    save_gif(frames, OUT / "coin.gif", [90] * 6)


if __name__ == "__main__":
    make_main()
    make_angry()
    make_done()
    make_icon()
    make_runner()
    make_icons()
    make_gift()
    make_coin_spin()
    for p in sorted(OUT.iterdir()):
        print(f"{p.name:22s} {p.stat().st_size/1024:6.1f} KB")
