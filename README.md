# blackroad-level-editor

> Tile-based level editor with export

Part of the [BlackRoad OS](https://blackroad.io) ecosystem — [BlackRoad-Interactive](https://github.com/BlackRoad-Interactive)

---

# BlackRoad Level Editor

Tile-based level editor with A* pathfinding, flood fill, procedural dungeon generation, and JSON/ASCII export.

## Features

- **Tile Types**: Floor, wall, door, spawn, exit, item, trap, water, lava, void
- **Editing**: Place tiles, rectangle fill, outline-only, flood fill
- **A\* Pathfinding**: 4/8-directional with diagonal cost support
- **Validation**: Checks spawn/exit presence, reachability, wall ratio
- **Dungeon Generator**: Random room placement with corridor connections
- **Entities**: NPC/object placement system
- **Export**: JSON and ASCII art formats

## Usage

```bash
python level_editor.py
```

## License

Proprietary — BlackRoad OS, Inc. All rights reserved.
