"""
BlackRoad Level Editor
Tile-based level editor with A* pathfinding, flood fill, and export.
"""

import heapq
import json
import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TileType(str, Enum):
    FLOOR = "floor"
    WALL = "wall"
    DOOR = "door"
    SPAWN = "spawn"
    EXIT = "exit"
    ITEM = "item"
    TRAP = "trap"
    WATER = "water"
    LAVA = "lava"
    VOID = "void"


TILE_GLYPHS = {
    TileType.FLOOR: ".",
    TileType.WALL:  "#",
    TileType.DOOR:  "+",
    TileType.SPAWN: "S",
    TileType.EXIT:  "E",
    TileType.ITEM:  "i",
    TileType.TRAP:  "^",
    TileType.WATER: "~",
    TileType.LAVA:  "L",
    TileType.VOID:  " ",
}

TILE_PASSABLE = {
    TileType.FLOOR: True,
    TileType.WALL:  False,
    TileType.DOOR:  True,
    TileType.SPAWN: True,
    TileType.EXIT:  True,
    TileType.ITEM:  True,
    TileType.TRAP:  True,
    TileType.WATER: False,
    TileType.LAVA:  False,
    TileType.VOID:  False,
}

TILE_COLORS = {
    TileType.FLOOR: "#cccccc",
    TileType.WALL:  "#333333",
    TileType.DOOR:  "#8B4513",
    TileType.SPAWN: "#00ff00",
    TileType.EXIT:  "#ff0000",
    TileType.ITEM:  "#ffff00",
    TileType.TRAP:  "#ff6600",
    TileType.WATER: "#0066ff",
    TileType.LAVA:  "#ff3300",
    TileType.VOID:  "#000000",
}


# ---------------------------------------------------------------------------
# Tile & Entity
# ---------------------------------------------------------------------------

@dataclass
class Tile:
    """A single map tile."""
    id: int
    type: TileType
    passable: bool = True
    glyph: str = "."
    color: str = "#cccccc"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_type(cls, tile_type: TileType, tile_id: int = 0) -> "Tile":
        return cls(
            id=tile_id,
            type=tile_type,
            passable=TILE_PASSABLE[tile_type],
            glyph=TILE_GLYPHS[tile_type],
            color=TILE_COLORS[tile_type],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "passable": self.passable,
            "glyph": self.glyph,
            "color": self.color,
        }


@dataclass
class Entity:
    """An entity placed on the level."""
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = "npc"
    x: int = 0
    y: int = 0
    name: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.entity_id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "name": self.name,
            "properties": self.properties,
        }


# ---------------------------------------------------------------------------
# Level
# ---------------------------------------------------------------------------

@dataclass
class Level:
    """2D tile map level."""
    level_id: str
    name: str
    width: int
    height: int
    tiles: List[List[Tile]] = field(default_factory=list)    # [y][x]
    entities: List[Entity] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def set_tile(self, x: int, y: int, tile: Tile) -> bool:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = tile
            return True
        return False

    def is_passable(self, x: int, y: int) -> bool:
        tile = self.get_tile(x, y)
        return tile is not None and tile.passable

    def find_tiles(self, tile_type: TileType) -> List[Tuple[int, int]]:
        positions = []
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x].type == tile_type:
                    positions.append((x, y))
        return positions

    def to_dict(self) -> dict:
        return {
            "level_id": self.level_id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "tiles": [[t.to_dict() for t in row] for row in self.tiles],
            "entities": [e.to_dict() for e in self.entities],
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Level Editor
# ---------------------------------------------------------------------------

class LevelEditor:
    """Main level editor with editing, pathfinding, and export."""

    def __init__(self):
        self._levels: Dict[str, Level] = {}
        self._tile_counter: int = 0

    # ------------------------------------------------------------------
    # Level management
    # ------------------------------------------------------------------

    def create_level(self, width: int, height: int, fill_tile: TileType = TileType.FLOOR, name: str = "") -> Level:
        """Create a new level filled with fill_tile."""
        level_id = str(uuid.uuid4())[:8]
        if not name:
            name = f"Level_{len(self._levels) + 1}"
        tiles: List[List[Tile]] = []
        for y in range(height):
            row = []
            for x in range(width):
                self._tile_counter += 1
                row.append(Tile.from_type(fill_tile, self._tile_counter))
            tiles.append(row)
        level = Level(level_id=level_id, name=name, width=width, height=height, tiles=tiles)
        self._levels[level_id] = level
        return level

    def get_level(self, level_id: str) -> Optional[Level]:
        return self._levels.get(level_id)

    def list_levels(self) -> List[dict]:
        return [
            {"id": lvl.level_id, "name": lvl.name, "size": f"{lvl.width}x{lvl.height}"}
            for lvl in self._levels.values()
        ]

    def delete_level(self, level_id: str) -> bool:
        if level_id in self._levels:
            del self._levels[level_id]
            return True
        return False

    def duplicate_level(self, level_id: str) -> Optional[Level]:
        """Create a deep copy of an existing level."""
        src = self.get_level(level_id)
        if not src:
            return None
        new_id = str(uuid.uuid4())[:8]
        import copy
        new_level = copy.deepcopy(src)
        new_level.level_id = new_id
        new_level.name = f"{src.name}_copy"
        self._levels[new_id] = new_level
        return new_level

    # ------------------------------------------------------------------
    # Tile editing
    # ------------------------------------------------------------------

    def place_tile(self, level_id: str, x: int, y: int, tile_type: TileType) -> bool:
        """Place a single tile at (x, y)."""
        level = self.get_level(level_id)
        if not level:
            return False
        self._tile_counter += 1
        return level.set_tile(x, y, Tile.from_type(tile_type, self._tile_counter))

    def place_rect(self, level_id: str, x1: int, y1: int, x2: int, y2: int, tile_type: TileType, outline_only: bool = False):
        """Place tiles in a rectangle."""
        level = self.get_level(level_id)
        if not level:
            return
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if outline_only:
                    if x in (x1, x2) or y in (y1, y2):
                        self.place_tile(level_id, x, y, tile_type)
                else:
                    self.place_tile(level_id, x, y, tile_type)

    def flood_fill(self, level_id: str, x: int, y: int, tile_type: TileType):
        """Flood-fill starting at (x, y) replacing tiles of the same type."""
        level = self.get_level(level_id)
        if not level:
            return
        start_tile = level.get_tile(x, y)
        if not start_tile:
            return
        target_type = start_tile.type
        if target_type == tile_type:
            return

        stack = [(x, y)]
        visited = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            tile = level.get_tile(cx, cy)
            if not tile or tile.type != target_type:
                continue
            visited.add((cx, cy))
            self.place_tile(level_id, cx, cy, tile_type)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in visited and level.get_tile(nx, ny):
                    stack.append((nx, ny))

    # ------------------------------------------------------------------
    # Room generation
    # ------------------------------------------------------------------

    def generate_dungeon(self, level_id: str, room_count: int = 5, min_room_size: int = 4, max_room_size: int = 10):
        """Generate random rooms connected by corridors."""
        import random
        level = self.get_level(level_id)
        if not level:
            return
        # Fill with walls
        for y in range(level.height):
            for x in range(level.width):
                self.place_tile(level_id, x, y, TileType.WALL)

        rooms = []
        for _ in range(room_count * 5):
            if len(rooms) >= room_count:
                break
            w = random.randint(min_room_size, max_room_size)
            h = random.randint(min_room_size, max_room_size)
            rx = random.randint(1, level.width - w - 1)
            ry = random.randint(1, level.height - h - 1)
            # Check overlap
            overlap = False
            for room in rooms:
                ox, oy, ow, oh = room
                if not (rx + w < ox or rx > ox + ow or ry + h < oy or ry > oy + oh):
                    overlap = True
                    break
            if not overlap:
                rooms.append((rx, ry, w, h))
                self.place_rect(level_id, rx, ry, rx + w - 1, ry + h - 1, TileType.FLOOR)

        # Connect rooms with corridors
        for i in range(1, len(rooms)):
            x1 = rooms[i - 1][0] + rooms[i - 1][2] // 2
            y1 = rooms[i - 1][1] + rooms[i - 1][3] // 2
            x2 = rooms[i][0] + rooms[i][2] // 2
            y2 = rooms[i][1] + rooms[i][3] // 2
            cx, cy = x1, y1
            while cx != x2:
                self.place_tile(level_id, cx, cy, TileType.FLOOR)
                cx += 1 if cx < x2 else -1
            while cy != y2:
                self.place_tile(level_id, cx, cy, TileType.FLOOR)
                cy += 1 if cy < y2 else -1

        # Place spawn in first room, exit in last
        if rooms:
            rx, ry, rw, rh = rooms[0]
            self.place_tile(level_id, rx + 1, ry + 1, TileType.SPAWN)
            rx2, ry2, rw2, rh2 = rooms[-1]
            self.place_tile(level_id, rx2 + rw2 - 2, ry2 + rh2 - 2, TileType.EXIT)

    # ------------------------------------------------------------------
    # A* Pathfinding
    # ------------------------------------------------------------------

    def pathfind(
        self,
        level_id: str,
        start: Tuple[int, int],
        end: Tuple[int, int],
        allow_diagonals: bool = False,
    ) -> Optional[List[Tuple[int, int]]]:
        """A* pathfinding. Returns list of (x, y) or None if no path."""
        level = self.get_level(level_id)
        if not level:
            return None
        if not level.is_passable(*start) or not level.is_passable(*end):
            return None

        def heuristic(a, b):
            if allow_diagonals:
                return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        if allow_diagonals:
            dirs += [(1, 1), (1, -1), (-1, 1), (-1, -1)]

        open_set = [(0, start)]
        came_from: Dict[Tuple, Optional[Tuple]] = {start: None}
        g_score: Dict[Tuple, float] = {start: 0}

        while open_set:
            _, current = heapq.heappop(open_set)
            if current == end:
                # Reconstruct path
                path = []
                node: Optional[Tuple[int, int]] = current
                while node is not None:
                    path.append(node)
                    node = came_from.get(node)
                return path[::-1]

            for dx, dy in dirs:
                nx, ny = current[0] + dx, current[1] + dy
                neighbor = (nx, ny)
                if not level.is_passable(nx, ny):
                    continue
                cost = math.sqrt(2) if (dx != 0 and dy != 0) else 1.0
                tentative_g = g_score[current] + cost
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + heuristic(neighbor, end)
                    heapq.heappush(open_set, (f, neighbor))

        return None   # No path found

    def all_pairs_reachable(self, level_id: str, positions: List[Tuple[int, int]]) -> bool:
        """Check if all positions are mutually reachable via BFS."""
        if len(positions) < 2:
            return True
        # BFS from first position
        level = self.get_level(level_id)
        if not level:
            return False
        start = positions[0]
        visited = {start}
        queue = [start]
        while queue:
            cx, cy = queue.pop(0)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in visited and level.is_passable(nx, ny):
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        return all(p in visited for p in positions[1:])

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, level_id: str) -> dict:
        """Validate a level for playability."""
        level = self.get_level(level_id)
        if not level:
            return {"valid": False, "errors": ["Level not found"]}

        errors = []
        warnings = []

        spawns = level.find_tiles(TileType.SPAWN)
        exits = level.find_tiles(TileType.EXIT)
        floors = level.find_tiles(TileType.FLOOR)

        if not spawns:
            errors.append("No spawn tile found")
        if len(spawns) > 1:
            warnings.append(f"Multiple spawn tiles found ({len(spawns)})")
        if not exits:
            errors.append("No exit tile found")

        # Check spawn → exit reachability
        if spawns and exits:
            path = self.pathfind(level_id, spawns[0], exits[0])
            if path is None:
                errors.append("Exit not reachable from spawn")
            else:
                pass

        # Check all floor tiles reachable from spawn
        if spawns and floors:
            reachable = self.all_pairs_reachable(level_id, spawns[:1] + floors[:5])
            if not reachable:
                warnings.append("Some floor tiles may be isolated")

        # Size checks
        if level.width < 5 or level.height < 5:
            warnings.append("Level is very small")
        if level.width > 200 or level.height > 200:
            warnings.append("Level is very large")

        # Walls ratio
        wall_count = sum(
            1 for y in range(level.height)
            for x in range(level.width)
            if level.tiles[y][x].type == TileType.WALL
        )
        total = level.width * level.height
        wall_ratio = wall_count / total
        if wall_ratio > 0.9:
            errors.append(f"Level is mostly walls ({wall_ratio:.0%})")
        elif wall_ratio > 0.7:
            warnings.append(f"Level is {wall_ratio:.0%} walls")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "spawns": len(spawns),
                "exits": len(exits),
                "floors": len(floors),
                "wall_ratio": round(wall_ratio, 3),
                "size": f"{level.width}x{level.height}",
            },
        }

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    def add_entity(self, level_id: str, entity: Entity) -> bool:
        level = self.get_level(level_id)
        if not level:
            return False
        level.entities.append(entity)
        return True

    def remove_entity(self, level_id: str, entity_id: str) -> bool:
        level = self.get_level(level_id)
        if not level:
            return False
        before = len(level.entities)
        level.entities = [e for e in level.entities if e.entity_id != entity_id]
        return len(level.entities) < before

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_json(self, level_id: str) -> str:
        level = self.get_level(level_id)
        if not level:
            return "{}"
        return json.dumps(level.to_dict(), indent=2)

    def export_ascii(self, level_id: str) -> str:
        """Export level as ASCII art."""
        level = self.get_level(level_id)
        if not level:
            return ""
        lines = []
        entity_pos = {(e.x, e.y): e for e in level.entities}
        for y in range(level.height):
            row_chars = []
            for x in range(level.width):
                if (x, y) in entity_pos:
                    row_chars.append("@")
                else:
                    tile = level.tiles[y][x]
                    row_chars.append(tile.glyph)
            lines.append("".join(row_chars))
        return "\n".join(lines)

    def import_json(self, data: str) -> Optional[Level]:
        """Import a level from JSON string."""
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            return None

        width = obj["width"]
        height = obj["height"]
        tiles: List[List[Tile]] = []
        for row_data in obj.get("tiles", []):
            row = []
            for t_data in row_data:
                tile = Tile(
                    id=t_data.get("id", 0),
                    type=TileType(t_data["type"]),
                    passable=t_data.get("passable", True),
                    glyph=t_data.get("glyph", "."),
                    color=t_data.get("color", "#cccccc"),
                )
                row.append(tile)
            tiles.append(row)

        entities = [
            Entity(
                entity_id=e["id"],
                type=e.get("type", "npc"),
                x=e["x"],
                y=e["y"],
                name=e.get("name", ""),
            )
            for e in obj.get("entities", [])
        ]

        level = Level(
            level_id=obj.get("level_id", str(uuid.uuid4())[:8]),
            name=obj.get("name", "Imported Level"),
            width=width,
            height=height,
            tiles=tiles,
            entities=entities,
            metadata=obj.get("metadata", {}),
        )
        self._levels[level.level_id] = level
        return level


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    print("=== BlackRoad Level Editor Demo ===")
    editor = LevelEditor()

    # Create and carve a simple level
    level = editor.create_level(30, 15, TileType.WALL, name="Demo Level")
    lid = level.level_id
    print(f"Created: {lid} ({level.width}x{level.height})")

    # Carve floor region
    editor.place_rect(lid, 1, 1, 28, 13, TileType.FLOOR)
    # Add walls in middle
    editor.place_rect(lid, 10, 3, 10, 10, TileType.WALL)
    editor.place_rect(lid, 20, 4, 20, 12, TileType.WALL)
    # Doors
    editor.place_tile(lid, 10, 6, TileType.DOOR)
    editor.place_tile(lid, 20, 8, TileType.DOOR)
    # Spawn & exit
    editor.place_tile(lid, 2, 2, TileType.SPAWN)
    editor.place_tile(lid, 27, 12, TileType.EXIT)
    # Traps & items
    editor.place_tile(lid, 5, 7, TileType.TRAP)
    editor.place_tile(lid, 15, 5, TileType.ITEM)

    print("\n[ASCII Level]")
    print(editor.export_ascii(lid))

    # Pathfind
    spawns = level.find_tiles(TileType.SPAWN)
    exits = level.find_tiles(TileType.EXIT)
    if spawns and exits:
        path = editor.pathfind(lid, spawns[0], exits[0])
        print(f"\nPath from spawn to exit: {len(path)} steps" if path else "\nNo path found")

    # Validation
    print(f"\nValidation: {editor.validate(lid)}")

    # Flood fill
    editor.flood_fill(lid, 14, 14, TileType.WATER)
    print("\n[After flood fill water at border]")
    print(editor.export_ascii(lid))

    # Dungeon generation
    print("\n[Generated dungeon 60x20]")
    dungeon = editor.create_level(60, 20, TileType.WALL, name="Dungeon")
    editor.generate_dungeon(dungeon.level_id, room_count=6)
    print(editor.export_ascii(dungeon.level_id))
    print(f"\nDungeon validation: {editor.validate(dungeon.level_id)}")

    # Export JSON
    json_str = editor.export_json(dungeon.level_id)
    print(f"\nJSON export size: {len(json_str)} bytes")

    # Import JSON round-trip
    imported = editor.import_json(json_str)
    if imported:
        print(f"Re-imported level: {imported.name} ({imported.width}x{imported.height})")

    print(f"\nAll levels: {editor.list_levels()}")


if __name__ == "__main__":
    demo()
