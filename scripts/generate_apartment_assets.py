#!/usr/bin/env python3
"""Génère le monde Gazebo et la carte Nav2 du même appartement."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "nlp_robot_commander"
WORLD_PATH = PACKAGE / "worlds" / "apartment.world"
MAP_IMAGE_PATH = PACKAGE / "maps" / "apartment_map.png"
MAP_YAML_PATH = PACKAGE / "maps" / "apartment.yaml"

RESOLUTION = 0.05
ORIGIN_X = -5.5
ORIGIN_Y = -4.5
MAP_WIDTH = 220
MAP_HEIGHT = 180


@dataclass(frozen=True)
class Box:
    name: str
    x: float
    y: float
    size_x: float
    size_y: float
    size_z: float
    color: tuple[float, float, float, float]
    collision: bool = True


WALL_COLOR = (0.88, 0.88, 0.84, 1.0)
WALLS = (
    Box("wall_north", 0.0, 4.0, 10.15, 0.15, 2.5, WALL_COLOR),
    Box("wall_south", 0.0, -4.0, 10.15, 0.15, 2.5, WALL_COLOR),
    Box("wall_west", -5.0, 0.0, 0.15, 8.0, 2.5, WALL_COLOR),
    Box("wall_east", 5.0, 0.0, 0.15, 8.0, 2.5, WALL_COLOR),
    # Deux murs horizontaux, chacun interrompu par deux portes de 1,20 m.
    Box("wall_nw_hall", -4.0125, 0.75, 1.825, 0.15, 2.5, WALL_COLOR),
    Box("wall_n_center", 0.0, 0.75, 3.8, 0.15, 2.5, WALL_COLOR),
    Box("wall_ne_hall", 4.0125, 0.75, 1.825, 0.15, 2.5, WALL_COLOR),
    Box("wall_sw_hall", -4.0125, -0.75, 1.825, 0.15, 2.5, WALL_COLOR),
    Box("wall_s_center", 0.0, -0.75, 3.8, 0.15, 2.5, WALL_COLOR),
    Box("wall_se_hall", 4.0125, -0.75, 1.825, 0.15, 2.5, WALL_COLOR),
    Box("wall_between_living_kitchen", 0.0, 2.375, 0.15, 3.25, 2.5, WALL_COLOR),
    Box("wall_between_bed_office", 0.0, -2.375, 0.15, 3.25, 2.5, WALL_COLOR),
)

FLOORS = (
    Box("floor_salon", -2.5, 2.375, 4.85, 3.10, 0.01, (0.84, 0.67, 0.45, 1.0), False),
    Box("floor_cuisine", 2.5, 2.375, 4.85, 3.10, 0.01, (0.55, 0.76, 0.88, 1.0), False),
    Box("floor_chambre", -2.5, -2.375, 4.85, 3.10, 0.01, (0.72, 0.62, 0.82, 1.0), False),
    Box("floor_bureau", 2.5, -2.375, 4.85, 3.10, 0.01, (0.58, 0.78, 0.58, 1.0), False),
    Box("floor_couloir", 0.0, 0.0, 9.85, 1.35, 0.01, (0.72, 0.72, 0.68, 1.0), False),
    Box("floor_chargeur", -4.0, 0.0, 0.55, 0.55, 0.015, (0.15, 0.35, 0.85, 1.0), False),
)

FURNITURE = (
    Box("salon_canape", -4.05, 2.45, 0.70, 1.80, 0.65, (0.46, 0.25, 0.14, 1.0)),
    Box("salon_table", -2.65, 2.35, 1.10, 0.65, 0.35, (0.58, 0.38, 0.20, 1.0)),
    Box("cuisine_plan_travail", 2.50, 3.55, 3.80, 0.55, 0.90, (0.82, 0.82, 0.78, 1.0)),
    Box("cuisine_ilot", 2.70, 2.25, 1.20, 0.70, 0.90, (0.90, 0.90, 0.86, 1.0)),
    Box("chambre_lit", -3.30, -2.50, 2.30, 1.40, 0.55, (0.80, 0.72, 0.66, 1.0)),
    Box("chambre_armoire", -0.55, -2.60, 0.65, 1.80, 2.00, (0.42, 0.28, 0.18, 1.0)),
    Box("bureau_table", 3.45, -3.35, 2.20, 0.60, 0.75, (0.42, 0.30, 0.18, 1.0)),
    Box("bureau_bibliotheque", 4.45, -2.20, 0.55, 1.80, 1.80, (0.34, 0.24, 0.16, 1.0)),
)


def add_text(parent: ET.Element, name: str, value: object) -> ET.Element:
    element = ET.SubElement(parent, name)
    element.text = str(value)
    return element


def add_box_model(world: ET.Element, box: Box) -> None:
    model = ET.SubElement(world, "model", {"name": box.name})
    add_text(model, "static", "true")
    z = box.size_z / 2.0 if box.collision else 0.002
    add_text(model, "pose", f"{box.x} {box.y} {z} 0 0 0")
    link = ET.SubElement(model, "link", {"name": "link"})

    def add_geometry(parent: ET.Element) -> None:
        geometry = ET.SubElement(parent, "geometry")
        box_geometry = ET.SubElement(geometry, "box")
        add_text(box_geometry, "size", f"{box.size_x} {box.size_y} {box.size_z}")

    if box.collision:
        collision = ET.SubElement(link, "collision", {"name": "collision"})
        add_geometry(collision)
    visual = ET.SubElement(link, "visual", {"name": "visual"})
    add_geometry(visual)
    material = ET.SubElement(visual, "material")
    rgba = " ".join(str(component) for component in box.color)
    add_text(material, "ambient", rgba)
    add_text(material, "diffuse", rgba)


def generate_world() -> None:
    sdf = ET.Element("sdf", {"version": "1.6"})
    world = ET.SubElement(sdf, "world", {"name": "nlp_apartment"})
    for model_uri in ("model://ground_plane", "model://sun"):
        include = ET.SubElement(world, "include")
        add_text(include, "uri", model_uri)
    physics = ET.SubElement(world, "physics", {"name": "default_physics", "type": "ode"})
    add_text(physics, "max_step_size", "0.001")
    add_text(physics, "real_time_update_rate", "1000")
    scene = ET.SubElement(world, "scene")
    add_text(scene, "ambient", "0.55 0.55 0.55 1")
    add_text(scene, "background", "0.78 0.82 0.86 1")
    gui = ET.SubElement(world, "gui", {"fullscreen": "false"})
    camera = ET.SubElement(gui, "camera", {"name": "apartment_camera"})
    add_text(camera, "pose", "0 -11 10 0 0.65 1.57")
    add_text(camera, "view_controller", "orbit")
    for box in (*FLOORS, *WALLS, *FURNITURE):
        add_box_model(world, box)
    ET.indent(sdf, space="  ")
    WORLD_PATH.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(sdf).write(WORLD_PATH, encoding="utf-8", xml_declaration=True)


def world_to_pixel(x: float, y: float) -> tuple[int, int]:
    column = round((x - ORIGIN_X) / RESOLUTION)
    row = MAP_HEIGHT - 1 - round((y - ORIGIN_Y) / RESOLUTION)
    return column, row


def rectangle_pixels(box: Box) -> tuple[int, int, int, int]:
    left, bottom = world_to_pixel(box.x - box.size_x / 2, box.y - box.size_y / 2)
    right, top = world_to_pixel(box.x + box.size_x / 2, box.y + box.size_y / 2)
    return min(left, right), min(top, bottom), max(left, right), max(top, bottom)


def generate_map() -> None:
    image = Image.new("L", (MAP_WIDTH, MAP_HEIGHT), 205)
    draw = ImageDraw.Draw(image)
    interior = Box("interior", 0.0, 0.0, 9.85, 7.85, 0.0, (0, 0, 0, 1))
    draw.rectangle(rectangle_pixels(interior), fill=254)
    for obstacle in (*WALLS, *FURNITURE):
        draw.rectangle(rectangle_pixels(obstacle), fill=0)
    MAP_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(MAP_IMAGE_PATH, optimize=True)
    MAP_YAML_PATH.write_text(
        "\n".join(
            (
                "image: apartment_map.png",
                "mode: trinary",
                f"resolution: {RESOLUTION}",
                f"origin: [{ORIGIN_X}, {ORIGIN_Y}, 0.0]",
                "negate: 0",
                "occupied_thresh: 0.65",
                "free_thresh: 0.196",
                "",
            )
        ),
        encoding="utf-8",
    )


def main() -> None:
    generate_world()
    generate_map()
    print(f"Monde Gazebo généré: {WORLD_PATH}")
    print(f"Carte Nav2 générée: {MAP_YAML_PATH}")


if __name__ == "__main__":
    main()
