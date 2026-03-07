# Beginner-Friendly 2D Traffic Management Game in Godot (Low-End PC)

This guide helps you build a complete **top-down 2D traffic simulation** in **Godot (latest stable)** using **GDScript**.

Goal: the player places roads/intersections on a small grid and improves traffic flow.

---

## 1) Project setup (step-by-step)

### 1.1 Install Godot
1. Go to the official Godot website: **https://godotengine.org/download**.
2. Download the latest stable Godot version for your OS.
3. For beginners on low-end PCs, use the standard editor build (not C# build).
4. Extract and run Godot (portable app).

### 1.2 Create a new project
1. Open Godot → **New Project**.
2. Name it: `TrafficFixer2D`.
3. Choose a folder location.
4. Renderer: pick **Compatibility** (best for older GPUs).
5. Click **Create & Edit**.

### 1.3 Suggested folder structure
Create folders in the FileSystem panel:

```
res://
  scenes/
    Main.tscn
    Map.tscn
    Car.tscn
    UI.tscn
  scripts/
    main.gd
    map.gd
    car.gd
    road_builder.gd
    traffic_manager.gd
    ui_controller.gd
  assets/
    tiles/
    cars/
    ui/
```

---

## 2) Map system with TileMap

Use a `TileMap` node for the city grid.

### 2.1 Create tile types
In one TileSet, define these tiles:
- `GRASS`
- `ROAD_STRAIGHT`
- `ROAD_CURVE`
- `ROAD_T`
- `ROAD_CROSS`

### 2.2 Main map scene
`Map.tscn`:
- Root: `Node2D` (`Map`)
- Child: `TileMap` (`Ground`)
- Child: `TileMap` (`Roads`) (optional split for clean layering)

Set tile size to something small (e.g., 32x32).

### 2.3 Grid constants (example)

```gdscript
# scripts/map.gd
extends Node2D

const GRID_WIDTH := 30
const GRID_HEIGHT := 20
const TILE_GRASS := 0
const TILE_ROAD_STRAIGHT := 1
const TILE_ROAD_CURVE := 2
const TILE_ROAD_T := 3
const TILE_ROAD_CROSS := 4

@onready var roads: TileMap = $Roads

func _ready() -> void:
    # Optional: fill with grass if using one tilemap layer for all tiles.
    pass
```

---

## 3) Road placement system (click + type + place)

### 3.1 Build mode idea
Track selected road type in script:
- `"straight"`
- `"curve"`
- `"t"`
- `"cross"`

### 3.2 Road placement script (beginner version)

```gdscript
# scripts/road_builder.gd
extends Node

@export var map_node: NodePath

var selected_tile_id := 1 # default straight road

@onready var map_ref := get_node(map_node)
@onready var roads: TileMap = map_ref.get_node("Roads")

func set_build_type(type_name: String) -> void:
    match type_name:
        "straight":
            selected_tile_id = 1
        "curve":
            selected_tile_id = 2
        "t":
            selected_tile_id = 3
        "cross":
            selected_tile_id = 4

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
        var world_pos := roads.get_global_mouse_position()
        var cell := roads.local_to_map(roads.to_local(world_pos))
        roads.set_cell(0, cell, 0, Vector2i(selected_tile_id, 0))
```

> Note: In Godot 4, `set_cell(layer, coords, source_id, atlas_coords)` is common for atlas-based TileSets.

---

## 4) Car system

Cars should:
- Spawn randomly at entry points.
- Follow a computed path on road cells.
- Move continuously.
- Stop if blocked by another car.

### 4.1 Car scene
`Car.tscn`:
- Root: `Node2D` (`Car`) with `car.gd`
- Child: `Sprite2D`
- Child: `Area2D` + `CollisionShape2D` (small detection area in front)

### 4.2 Car movement script

```gdscript
# scripts/car.gd
extends Node2D

var path: Array[Vector2] = []
var path_index := 0
var speed := 60.0
var max_speed := 60.0
var min_distance_to_next := 4.0
var blocked := false

func set_path(new_path: Array[Vector2]) -> void:
    path = new_path
    path_index = 0

func _process(delta: float) -> void:
    if blocked:
        speed = move_toward(speed, 0.0, 200.0 * delta)
    else:
        speed = move_toward(speed, max_speed, 100.0 * delta)

    if path_index >= path.size():
        queue_free()
        return

    var target := path[path_index]
    var to_target := target - global_position

    if to_target.length() < min_distance_to_next:
        path_index += 1
        return

    global_position += to_target.normalized() * speed * delta
    rotation = to_target.angle()

func set_blocked(value: bool) -> void:
    blocked = value
```

---

## 5) Traffic logic (slow/stop + collision avoidance)

Keep it lightweight (no heavy rigidbody physics).
Use simple distance checks in a manager.

```gdscript
# scripts/traffic_manager.gd
extends Node

@export var car_scene: PackedScene
@export var map_node: NodePath

var cars: Array[Node2D] = []
var max_cars := 50

func _process(_delta: float) -> void:
    _update_blocking()

func _update_blocking() -> void:
    for a in cars:
        if not is_instance_valid(a):
            continue
        var is_blocked := false
        for b in cars:
            if a == b or not is_instance_valid(b):
                continue
            # simple forward-distance logic
            var distance := a.global_position.distance_to(b.global_position)
            if distance < 20.0:
                var forward := Vector2.RIGHT.rotated(a.rotation)
                var dir_to_b := (b.global_position - a.global_position).normalized()
                if forward.dot(dir_to_b) > 0.5:
                    is_blocked = true
                    break
        a.set_blocked(is_blocked)
```

This is enough for beginner traffic behavior: cars slow/stop when another car is in front.

---

## 6) Pathfinding (simple + beginner-friendly)

Recommended approach: build an `AStarGrid2D` from road cells.

### 6.1 Build A* grid
- Grid size = map size.
- Mark non-road cells as solid.
- Entry and exit points are fixed cells on edges.

```gdscript
# scripts/map.gd (additions)
var astar := AStarGrid2D.new()

func rebuild_pathfinding() -> void:
    astar.region = Rect2i(0, 0, GRID_WIDTH, GRID_HEIGHT)
    astar.cell_size = Vector2(32, 32)
    astar.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_NEVER
    astar.update()

    for y in GRID_HEIGHT:
        for x in GRID_WIDTH:
            var cell := Vector2i(x, y)
            var source_id := roads.get_cell_source_id(0, cell)
            var is_road := source_id != -1
            astar.set_point_solid(cell, not is_road)

func get_world_path(start_cell: Vector2i, end_cell: Vector2i) -> Array[Vector2]:
    var id_path: Array[Vector2i] = astar.get_id_path(start_cell, end_cell)
    var world_path: Array[Vector2] = []
    for c in id_path:
        world_path.append(roads.to_global(roads.map_to_local(c)))
    return world_path
```

Call `rebuild_pathfinding()` every time player places/removes roads.

---

## 7) Basic UI

Use a `CanvasLayer` scene (`UI.tscn`) with:
- `Button` → Build Road
- `Button` → Build Intersection
- `Label` → Traffic Score

```gdscript
# scripts/ui_controller.gd
extends CanvasLayer

signal build_type_selected(type_name: String)

@onready var score_label: Label = $Panel/ScoreLabel

func _on_build_road_pressed() -> void:
    emit_signal("build_type_selected", "straight")

func _on_build_intersection_pressed() -> void:
    emit_signal("build_type_selected", "cross")

func set_score(value: int) -> void:
    score_label.text = "Traffic Score: %d" % value
```

### Scoring idea
Increase score when average speed is high and waiting time is low:

```gdscript
func calculate_score(cars: Array) -> int:
    if cars.is_empty():
        return 0
    var speed_sum := 0.0
    for c in cars:
        speed_sum += c.speed
    var avg_speed := speed_sum / cars.size()
    return int(avg_speed * 10.0)
```

---

## 8) Performance optimization (for low-end PCs)

1. Limit active cars to **50**.
2. Keep map small (e.g., 30x20).
3. Use simple sprites (32x32 PNG, low memory).
4. Avoid heavy physics (`RigidBody2D`) for traffic logic.
5. Use `_process` with cheap loops; avoid expensive per-car raycasts.
6. Rebuild A* only when roads change, not every frame.
7. Use Compatibility renderer.
8. Disable shadows/effects not needed in 2D.

---

## 9) Free asset websites

- **Kenney** (excellent free game art): https://kenney.nl/assets
- **OpenGameArt**: https://opengameart.org
- **itch.io free assets**: https://itch.io/game-assets/free
- **CraftPix free section**: https://craftpix.net/freebies/

Tip: Always check license terms (CC0, CC-BY, commercial use).

---

## 10) Exporting the game

### 10.1 Export for Windows
1. In Godot: **Editor → Manage Export Templates → Download and Install**.
2. Go to **Project → Export**.
3. Add preset: **Windows Desktop**.
4. Set executable name: `TrafficFixer2D.exe`.
5. Click **Export Project**.

### 10.2 Export for Web browser
1. In **Project → Export**, add preset: **Web**.
2. Ensure compatibility settings are default for simple 2D.
3. Click **Export Project** to generate HTML/JS/WASM files.
4. Host files on itch.io, GitHub Pages, or Netlify.

---

## Recommended beginner build order

1. Make map + tile types.
2. Add click-to-place roads.
3. Add one car that follows a fixed path.
4. Add A* pathfinding between entry/exit points.
5. Add multiple cars + stop-if-blocked logic.
6. Add score UI.
7. Tune spawn rate and max cars for smooth performance.

With this setup, you get a playable “fix the traffic” prototype that feels similar to traffic optimization gameplay, but is small and beginner-friendly.
