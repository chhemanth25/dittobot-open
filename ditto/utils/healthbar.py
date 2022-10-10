from PIL import Image, ImageDraw, ImageFont


class HealthBar:
    def __init__(self):
        self.radius = 30

    def round_corner(self, radius, fill):
        """Draw a round corner."""
        corner = Image.new("RGBA", (radius, radius), (0, 0, 0, 0))
        draw = ImageDraw.Draw(corner)
        draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=fill)
        return corner

    def curve_edges(self, base_bar, radius, fill):
        corner = self.round_corner(radius, fill)
        base_bar.paste(corner, (0, 0))
        base_bar.paste(corner.rotate(90), (0, base_bar.height - radius))
        base_bar.paste(
            corner.rotate(180), (base_bar.width - radius, base_bar.height - radius)
        )
        base_bar.paste(corner.rotate(270), (base_bar.width - radius, 0))
        return base_bar

    def make_base_bar(self):
        base_bar = Image.new("RGBA", (483, 69), color="white")
        return self.curve_edges(base_bar, self.radius, "white")

    def make_health_bar(self, per):
        if per > 0.6:
            color = (153, 223, 178, 255)
        elif per > 0.3:
            color = (255, 241, 87, 255)
        else:
            color = "red"
        health_bar = Image.new("RGBA", (max(1, round(473 * per)), 60), color=color)
        return self.curve_edges(health_bar, round(self.radius // 1.2), color)

    def bar(self, current_health, max_health):
        diff = current_health / max_health
        base_bar = self.make_base_bar()
        health_bar = self.make_health_bar(diff)
        base_bar.paste(health_bar, (5, 4), mask=health_bar)
        draw = ImageDraw.Draw(base_bar)
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/JMH-ava/JMH Ava bold.otf", 48
        )
        draw.text(
            (140, 19), f"{current_health}/{max_health}", fill=(0, 0, 0, 255), font=font
        )
        return base_bar
