import io
import math
from pathlib import Path

import orjson
from fastapi import FastAPI
from PIL import Image, ImageDraw, ImageFont
from starlette.responses import StreamingResponse

from helpers import HealthBar, sresize

app = FastAPI()
DIR = Path(__file__).parent / "res"
PRELOADED = {
    "trick_room": Image.open(str(DIR / "trick_room.png")).convert("RGBA"),
    "rain": Image.open(str(DIR / "rain.png")).convert("RGBA"),
    "hail": Image.open(str(DIR / "hail.png")).convert("RGBA"),
    "sun": Image.open(str(DIR / "sun.png")).convert("RGBA"),
    "sandstorm": Image.open(str(DIR / "sandstorm.png")).convert("RGBA"),
    "sub": sresize(Image.open(str(DIR / "sub.png"))).convert("RGBA"),
}

font = ImageFont.truetype(str(DIR / "futur.ttf"), 16, encoding="unic")


def draw_rectangle(width, height, color):
    """
    Draw a rectangle.
    """
    return Image.new("RGBA", (width, height), color)


def draw_pixel_pokemon_card(path, level, gender="-m"):
    """Parameters
    path: str
        Path to image
    """
    base_card_width, base_card_height = 272, 75

    base_card = draw_rectangle(base_card_width, base_card_height, "#f5f5f5").convert(
        "RGBA"
    )
    pokemon_sprite = Image.open(DIR / path).convert("RGBA")
    base_card.paste(pokemon_sprite, (5, -10), mask=pokemon_sprite)

    draw = ImageDraw.Draw(base_card)
    draw.text(
        (140, 40), f"Lv.{level}", anchor="mm", fill="black", align="center", font=font
    )
    return base_card


def draw_player_headers(background, names):
    top = 200
    rect_w, rect_h = 282, 37
    rects = draw_rectangle(rect_w, rect_h, "#0000FF"), draw_rectangle(
        rect_w, rect_h, "#FF0000"
    )
    draws = [ImageDraw.Draw(rect) for rect in rects]
    for index, name in enumerate(names):
        draws[index].text(
            (
                (rect_w / 2),
                (rect_h / 2),
            ),
            name,
            anchor="mm",
            fill="white",
            align="center",
            font=font,
        )
        background.paste(rects[index], (top, 38))
        top += 600


def draw_player_teams(background, p1pokes, p2pokes):
    # Draw First Player Team
    left = 125
    for pokemon, level in p1pokes:
        base_card = draw_pixel_pokemon_card(pokemon, level)
        background.paste(base_card, (205, left - 45), mask=base_card)
        left += 80

    # Draw Second Player Team
    left = 125
    for pokemon, level in p2pokes:
        base_card = draw_pixel_pokemon_card(pokemon, level)
        background.paste(base_card, (804, left - 45), mask=base_card)
        left += 80


@app.post("/build_team_preview")
def build_team_preview(player1_data: str, player2_data: str):
    """Paramater payload will be like the following
    player1_data: dictionary
        Contains the JSON serializable information for Player 1 containing name & list of (pokemon_sprite_path, level)
    player2_data: dictionary
        Contains the JSON serializable information for Player 2 containing name & list of (pokemon_sprite_path, level)
    """
    player1_data, player2_data = orjson.loads(player1_data), orjson.loads(player2_data)
    player1_pokes = player1_data["pokemon_info"]
    player2_pokes = player2_data["pokemon_info"]

    bg = Image.open(str(DIR / "team_preview.jpg")).convert("RGBA")
    draw_player_headers(bg, [player1_data["name"], player2_data["name"]])
    draw_player_teams(bg, player1_pokes, player2_pokes)

    fp = io.BytesIO()
    bg.save(fp, format="PNG")
    fp.seek(0)
    return StreamingResponse(fp, media_type="image/png")


@app.get("/ping")
def ping():
    return {"message": "ping"}


@app.post("/build")
def build_image(
    poke1_image_url: str,
    poke2_image_url: str,
    poke1: str,
    poke2: str,
    background_number: int,
    weather: str,
    trick_room: int,
):
    """Paramater payload will be like the following

    poke1_image_url: str
        URL to poke1 image
    poke2_image_url: str
        URL to poke2 image
    poke1: dictionary
        Contains the JSON serializable information for Pokemon 1
    poke2: dictionary
        Contains the JSON serializable information for Pokemon 2
    background_number: int
        The number of background to use
    weather: str
        The current weather
    trick_room: bool/int
        If a trick room is active
    """
    args = {
        "poke1_image_url": poke1_image_url,
        "poke2_image_url": poke2_image_url,
        "poke1": poke1,
        "poke2": poke2,
        "background_number": background_number,
        "weather": weather,
        "trick_room": trick_room,
    }
    poke1 = orjson.loads(args["poke1"])
    poke2 = orjson.loads(args["poke2"])

    bg = Image.open(str(DIR / f"bg{args['background_number']}.png"))

    if int(args["trick_room"]):
        trick_room = PRELOADED["trick_room"].resize(bg.size)
        trick_room.putalpha(128)
        bg.paste(trick_room)

    if args["weather"]:
        w = args["weather"]
        if w in ("rain", "h-rain"):
            layer = PRELOADED["rain"].resize(bg.size)
            bg.paste(layer, mask=layer)
        elif w == "hail":
            layer = PRELOADED["hail"].resize(bg.size)
            bg.paste(layer, mask=layer)
        elif w in ("sun", "h-sun"):
            layer = PRELOADED["sun"].resize(bg.size)
            bg.paste(layer, mask=layer)
        elif w == "sandstorm":
            layer = PRELOADED["sandstorm"].resize(bg.size)
            bg.paste(layer, mask=layer)
        # TODO: wind

    if bg.size != (1280, 640):
        bg = bg.resize((1280, 640), Image.ANTIALIAS)

    try:
        p1 = Image.open(DIR / args["poke1_image_url"]).convert("RGBA")
    except FileNotFoundError:
        print(f"{args['poke1_image_url']} does not exist in duel resources!")
        p1 = Image.open(DIR / "sprites" / "ERROR.png").convert("RGBA")

    try:
        p2 = Image.open(DIR / args["poke2_image_url"]).convert("RGBA")
    except FileNotFoundError:
        print(f"{args['poke2_image_url']} does not exist in duel resources!")
        p2 = Image.open(DIR / "sprites" / "ERROR.png").convert("RGBA")

    p1 = sresize(p1)
    p2 = sresize(p2)

    area = (630, 50)
    bg.paste(p2, area, p2)
    if poke2["substitute"] > 0:
        bg.paste(PRELOADED["sub"], area, mask=PRELOADED["sub"])

    area = (70, 50)
    bg.paste(p1, area, p1)
    if poke1["substitute"] > 0:
        bg.paste(PRELOADED["sub"], area, mask=PRELOADED["sub"])

    hb = HealthBar()
    bar1 = hb.bar(math.ceil(poke1["hp"]), poke1["starting_hp"])
    bar2 = hb.bar(math.ceil(poke2["hp"]), poke2["starting_hp"])
    bg.paste(bar1, (86, 44), mask=bar1)
    bg.paste(bar2, (707, 44), mask=bar2)

    fp = io.BytesIO()
    bg.save(fp, "PNG")
    fp.seek(0)

    return StreamingResponse(fp, media_type="image/png")
