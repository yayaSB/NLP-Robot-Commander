import xml.etree.ElementTree as ET
from collections import deque
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "src" / "nlp_robot_commander"
MAP_IMAGE = PACKAGE / "maps" / "apartment_map.png"
MAP_CONFIG = PACKAGE / "maps" / "apartment.yaml"
WORLD = PACKAGE / "worlds" / "apartment.world"
WAYPOINTS = PACKAGE / "config" / "waypoints.yaml"


def test_apartment_world_contains_rooms_walls_and_furniture():
    root = ET.parse(WORLD).getroot()
    names = {model.attrib["name"] for model in root.findall(".//model")}
    assert {
        "floor_salon",
        "floor_cuisine",
        "floor_chambre",
        "floor_bureau",
        "floor_couloir",
        "wall_between_living_kitchen",
        "wall_between_bed_office",
        "salon_canape",
        "cuisine_plan_travail",
        "chambre_lit",
        "bureau_table",
    }.issubset(names)


def test_apartment_map_and_waypoints_are_connected_with_robot_clearance():
    config = yaml.safe_load(MAP_CONFIG.read_text(encoding="utf-8"))
    waypoint_config = yaml.safe_load(WAYPOINTS.read_text(encoding="utf-8"))
    image = Image.open(MAP_IMAGE).convert("L")
    pixels = image.load()
    width, height = image.size
    resolution = float(config["resolution"])
    origin_x, origin_y, _ = config["origin"]
    clearance_pixels = 4

    safe = set()
    for row in range(clearance_pixels, height - clearance_pixels):
        for column in range(clearance_pixels, width - clearance_pixels):
            if all(
                pixels[column + dx, row + dy] >= 250
                for dx in range(-clearance_pixels, clearance_pixels + 1)
                for dy in range(-clearance_pixels, clearance_pixels + 1)
                if dx * dx + dy * dy <= clearance_pixels * clearance_pixels
            ):
                safe.add((column, row))

    def to_pixel(x: float, y: float) -> tuple[int, int]:
        column = round((x - origin_x) / resolution)
        row = height - 1 - round((y - origin_y) / resolution)
        return column, row

    start = to_pixel(-4.0, 0.0)
    queue = deque([start])
    visited = {start}
    while queue:
        column, row = queue.popleft()
        for neighbor in (
            (column - 1, row),
            (column + 1, row),
            (column, row - 1),
            (column, row + 1),
        ):
            if neighbor in safe and neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    assert start in safe
    for name, waypoint in waypoint_config["waypoints"].items():
        target = to_pixel(float(waypoint["x"]), float(waypoint["y"]))
        assert target in safe, f"Le waypoint {name} manque de dégagement."
        assert target in visited, f"Le waypoint {name} est séparé du couloir."
