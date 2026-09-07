extends Node2D


const WORLD := 3000.0
const PLAYER_HALF := 15.0
const PLAYER_SPEED := 230.0

const DAY_LEN := 55.0
const NIGHT_LEN := 28.0

# --- state ---
var player: Node2D
var cam: Camera2D

var hp: float = 100.0
var hunger: float = 100.0

var wood: int = 0
var stone: int = 0
var has_axe: bool = false
var has_pickaxe: bool = false
var has_sword: bool = false

var resources: Array = []   # {node, kind, hp}
var enemies: Array = []     # {node, hp, last_hit}
var walls: Array = []       # {pos: Vector2}

var is_night: bool = false
var phase_timer: float = DAY_LEN
var days: int = 1
var best_days: int = 0
var dead: bool = false
var build_mode: bool = false

# input
var move_vec: Vector2 = Vector2.ZERO
var joy_id: int = -1
var joy_center: Vector2 = Vector2.ZERO

# ui
var ui: CanvasLayer
var hp_bg: ColorRect
var hp_fill: ColorRect
var hunger_bg: ColorRect
var hunger_fill: ColorRect
var lbl_wood: Label
var lbl_stone: Label
var lbl_day: Label
var lbl_phase: Label
var action_btn: Button
var craft_btn: Button
var build_btn: Button
var craft_panel: Control
var build_hint: Label
var joy_base: ColorRect
var joy_knob: ColorRect
var night_overlay: ColorRect
var over_overlay: Control
var ov_lbl: Label
var ov_btn: Button


func _ready() -> void:
	randomize()
	load_best()
	_build_world()
	_build_ui()
	_layout()


func _build_world() -> void:
	player = _make_box(Color("#ff5a5f"), Vector2(30, 30))
	player.position = Vector2(WORLD / 2.0, WORLD / 2.0)
	add_child(player)

	cam = Camera2D.new()
	cam.position = player.position
	cam.zoom = Vector2(1.4, 1.4)
	cam.enabled = true
	add_child(cam)

	for i in 42:
		_spawn_resource("tree")
	for i in 32:
		_spawn_resource("rock")
	for i in 30:
		_spawn_resource("bush")


func _make_box(color: Color, sz: Vector2) -> Node2D:
	var n := Node2D.new()
	var r := ColorRect.new()
	r.color = color
	r.size = sz
	r.position = -sz / 2.0
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	n.add_child(r)
	return n


func _spawn_resource(kind: String) -> void:
	var node: Node2D
	match kind:
		"tree":
			node = _make_box(Color("#3e7c3a"), Vector2(40, 40))
		"rock":
			node = _make_box(Color("#8a8f98"), Vector2(34, 34))
		"bush":
			node = _make_box(Color("#57a05a"), Vector2(30, 30))
	node.position = Vector2(randf_range(60, WORLD - 60), randf_range(60, WORLD - 60))
	add_child(node)
	resources.append({"node": node, "kind": kind, "hp": 3 if kind != "bush" else 1})


func _build_ui() -> void:
	ui = CanvasLayer.new()
	add_child(ui)

	hp_bg = ColorRect.new()
	hp_bg.color = Color("#333333")
	hp_bg.size = Vector2(220, 22)
	hp_bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(hp_bg)
	hp_fill = ColorRect.new()
	hp_fill.color = Color("#e0484e")
	hp_fill.size = Vector2(220, 22)
	hp_fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(hp_fill)

	hunger_bg = ColorRect.new()
	hunger_bg.color = Color("#333333")
	hunger_bg.size = Vector2(220, 18)
	hunger_bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(hunger_bg)
	hunger_fill = ColorRect.new()
	hunger_fill.color = Color("#f2a23c")
	hunger_fill.size = Vector2(220, 18)
	hunger_fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(hunger_fill)

	lbl_wood = Label.new()
	lbl_wood.add_theme_font_size_override("font_size", 26)
	lbl_wood.add_theme_color_override("font_color", Color.WHITE)
	ui.add_child(lbl_wood)

	lbl_stone = Label.new()
	lbl_stone.add_theme_font_size_override("font_size", 26)
	lbl_stone.add_theme_color_override("font_color", Color.WHITE)
	ui.add_child(lbl_stone)

	lbl_day = Label.new()
	lbl_day.add_theme_font_size_override("font_size", 30)
	lbl_day.add_theme_color_override("font_color", Color.WHITE)
	lbl_day.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	ui.add_child(lbl_day)

	lbl_phase = Label.new()
	lbl_phase.add_theme_font_size_override("font_size", 22)
	lbl_phase.add_theme_color_override("font_color", Color("#ffd76e"))
	lbl_phase.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	ui.add_child(lbl_phase)

	action_btn = Button.new()
	action_btn.text = "ДЕЙСТВИЕ"
	action_btn.add_theme_font_size_override("font_size", 30)
	action_btn.pressed.connect(_on_action)
	ui.add_child(action_btn)

	craft_btn = Button.new()
	craft_btn.text = "КРАФТ"
	craft_btn.add_theme_font_size_override("font_size", 26)
	craft_btn.pressed.connect(_toggle_craft)
	ui.add_child(craft_btn)

	build_btn = Button.new()
	build_btn.text = "СТРОИТЬ"
	build_btn.add_theme_font_size_override("font_size", 26)
	build_btn.pressed.connect(_toggle_build)
	ui.add_child(build_btn)

	build_hint = Label.new()
	build_hint.text = "Тапни по земле — стена (5 дерева)"
	build_hint.add_theme_font_size_override("font_size", 22)
	build_hint.add_theme_color_override("font_color", Color("#9fe8ff"))
	build_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	build_hint.visible = false
	ui.add_child(build_hint)

	craft_panel = Control.new()
	var cp_bg := ColorRect.new()
	cp_bg.color = Color(0, 0, 0, 0.85)
	cp_bg.size = Vector2(300, 360)
	craft_panel.add_child(cp_bg)
	craft_panel.visible = false
	ui.add_child(craft_panel)

	var items := [
		["Топор (3 дер, 2 кам)", "_craft_axe"],
		["Кирка (3 дер, 2 кам)", "_craft_pickaxe"],
		["Меч (2 дер, 4 кам)", "_craft_sword"],
		["Стена (5 дер)", "_craft_wall"],
	]
	var y := 20.0
	for it in items:
		var b := Button.new()
		b.text = it[0]
		b.add_theme_font_size_override("font_size", 22)
		b.position = Vector2(20, y)
		b.size = Vector2(260, 64)
		b.pressed.connect(Callable(self, it[1]))
		craft_panel.add_child(b)
		y += 84

	joy_base = ColorRect.new()
	joy_base.color = Color(1, 1, 1, 0.12)
	joy_base.size = Vector2(160, 160)
	joy_base.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(joy_base)
	joy_knob = ColorRect.new()
	joy_knob.color = Color(1, 1, 1, 0.35)
	joy_knob.size = Vector2(70, 70)
	joy_knob.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(joy_knob)

	night_overlay = ColorRect.new()
	night_overlay.color = Color("#0a1230")
	night_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	night_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	night_overlay.modulate.a = 0.0
	ui.add_child(night_overlay)

	over_overlay = Control.new()
	var ov_bg := ColorRect.new()
	ov_bg.color = Color(0, 0, 0, 0.7)
	ov_bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	over_overlay.add_child(ov_bg)
	ov_lbl = Label.new()
	ov_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	ov_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	ov_lbl.add_theme_font_size_override("font_size", 48)
	ov_lbl.add_theme_color_override("font_color", Color.WHITE)
	over_overlay.add_child(ov_lbl)
	ov_btn = Button.new()
	ov_btn.text = "Заново"
	ov_btn.add_theme_font_size_override("font_size", 38)
	ov_btn.pressed.connect(_restart)
	over_overlay.add_child(ov_btn)
	over_overlay.visible = false
	ui.add_child(over_overlay)

	var hint := Label.new()
	hint.text = "Собирай дерево/камень, ночью отбивайся от волков"
	hint.add_theme_font_size_override("font_size", 20)
	hint.add_theme_color_override("font_color", Color("#cccccc"))
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.position = Vector2(0, 180)
	hint.size = Vector2(get_viewport_rect().size.x, 30)
	ui.add_child(hint)


func _layout() -> void:
	var vp := get_viewport_rect().size
	var w := vp.x
	var h := vp.y

	hp_bg.position = Vector2(14, 12)
	hp_fill.position = Vector2(14, 12)
	hunger_bg.position = Vector2(14, 40)
	hunger_fill.position = Vector2(14, 40)

	lbl_wood.position = Vector2(14, 66)
	lbl_wood.size = Vector2(200, 30)
	lbl_stone.position = Vector2(14, 96)
	lbl_stone.size = Vector2(200, 30)

	lbl_day.position = Vector2(w / 2.0 - 100, 12)
	lbl_day.size = Vector2(200, 36)
	lbl_phase.position = Vector2(w / 2.0 - 130, 50)
	lbl_phase.size = Vector2(260, 28)

	action_btn.size = Vector2(150, 90)
	action_btn.position = Vector2(w - 165, h - 200)
	craft_btn.size = Vector2(150, 60)
	craft_btn.position = Vector2(w - 165, h - 105)
	build_btn.size = Vector2(150, 60)
	build_btn.position = Vector2(w - 320, h - 105)

	build_hint.position = Vector2(0, h - 250)
	build_hint.size = Vector2(w, 30)

	craft_panel.position = Vector2(w / 2.0 - 150, h / 2.0 - 200)

	joy_base.position = Vector2(20, h - 200)
	joy_knob.position = joy_base.position + joy_base.size / 2.0 - joy_knob.size / 2.0

	ov_btn.size = Vector2(280, 80)
	ov_btn.position = Vector2(w / 2.0 - 140, h / 2.0 + 40)
	ov_lbl.size = Vector2(w, 140)
	ov_lbl.position = Vector2(0, h / 2.0 - 130)


func _process(delta: float) -> void:
	if dead:
		return
	_update_time(delta)
	_move_player(delta)
	_update_enemies(delta)
	_update_ui()
	_fix_cam()


func _update_time(delta: float) -> void:
	phase_timer -= delta
	hunger -= delta * 0.9
	if hunger <= 0.0:
		hunger = 0.0
		hp -= delta * 4.0
	if phase_timer <= 0.0:
		if is_night:
			is_night = false
			phase_timer = DAY_LEN
			days += 1
			if days > best_days:
				best_days = days
				save_best()
			_clear_enemies()
		else:
			is_night = true
			phase_timer = NIGHT_LEN
			_spawn_night_enemies()
	night_overlay.modulate.a = 0.55 if is_night else 0.0
	if hp <= 0.0:
		_die()


func _move_player(delta: float) -> void:
	var vel := move_vec * PLAYER_SPEED
	if vel != Vector2.ZERO:
		var t: Vector2 = player.position + vel * delta
		if not _blocked(Vector2(t.x, player.position.y), PLAYER_HALF):
			player.position.x = t.x
		if not _blocked(Vector2(player.position.x, t.y), PLAYER_HALF):
			player.position.y = t.y
		hunger -= delta * 0.4


func _blocked(center: Vector2, half: float) -> bool:
	if center.x < half or center.x > WORLD - half or center.y < half or center.y > WORLD - half:
		return true
	for w in walls:
		var wr := Rect2(w["pos"] - Vector2(24, 24), Vector2(48, 48))
		if wr.grow(half).has_point(center):
			return true
	return false


func _fix_cam() -> void:
	cam.position = player.position


func _on_action() -> void:
	if dead:
		return
	var best_e: Dictionary = {}
	var best_d := 90.0
	for e in enemies:
		var en: Node2D = e["node"]
		var d: float = player.position.distance_to(en.position)
		if d < best_d:
			best_d = d
			best_e = e
	if not best_e.is_empty():
		var dmg := 3 if has_sword else 1
		best_e["hp"] -= dmg
		var en: Node2D = best_e["node"]
		_bump(en, (en.position - player.position).normalized() * 18.0)
		if best_e["hp"] <= 0:
			en.queue_free()
			enemies.erase(best_e)
			hunger = minf(hunger + 2.0, 100.0)
		return

	var best_r: Dictionary = {}
	best_d = 80.0
	for r in resources:
		var rn: Node2D = r["node"]
		var d: float = player.position.distance_to(rn.position)
		if d < best_d:
			best_d = d
			best_r = r
	if best_r.is_empty():
		return
	var kind: String = best_r["kind"]
	var dmg := 1
	if kind == "tree" and has_axe:
		dmg = 3
	if kind == "rock" and has_pickaxe:
		dmg = 3
	best_r["hp"] -= dmg
	var rn: Node2D = best_r["node"]
	_bump(rn, (rn.position - player.position).normalized() * 8.0)
	if best_r["hp"] <= 0:
		match kind:
			"tree":
				wood += 3
			"rock":
				stone += 3
			"bush":
				hunger = minf(hunger + 22.0, 100.0)
		rn.queue_free()
		resources.erase(best_r)
		_spawn_resource(kind)


func _bump(node: Node2D, off: Vector2) -> void:
	node.position += off


func _spawn_night_enemies() -> void:
	var count := mini(2 + days, 9)
	for i in count:
		var e := _make_box(Color("#7a4b3a"), Vector2(28, 28))
		var ang := randf_range(0.0, TAU)
		var dist := randf_range(500.0, 800.0)
		e.position = player.position + Vector2(cos(ang), sin(ang)) * dist
		e.position = e.position.clamp(Vector2(40, 40), Vector2(WORLD - 40, WORLD - 40))
		add_child(e)
		enemies.append({"node": e, "hp": 3, "last_hit": 0})


func _clear_enemies() -> void:
	for e in enemies:
		var en: Node2D = e["node"]
		en.queue_free()
	enemies.clear()


func _update_enemies(delta: float) -> void:
	if not is_night:
		return
	var now := Time.get_ticks_msec()
	for e in enemies:
		var en: Node2D = e["node"]
		var dir: Vector2 = (player.position - en.position).normalized()
		var t: Vector2 = en.position + dir * 150.0 * delta
		if not _blocked(Vector2(t.x, en.position.y), 14.0):
			en.position.x = t.x
		if not _blocked(Vector2(en.position.x, t.y), 14.0):
			en.position.y = t.y
		if player.position.distance_to(en.position) < 30.0:
			if now - e["last_hit"] > 900:
				e["last_hit"] = now
				hp -= 12.0
				_bump(en, dir * -20.0)
	if hp <= 0.0:
		_die()


func _toggle_craft() -> void:
	craft_panel.visible = not craft_panel.visible


func _craft_axe() -> void:
	if not has_axe and wood >= 3 and stone >= 2:
		wood -= 3
		stone -= 2
		has_axe = true


func _craft_pickaxe() -> void:
	if not has_pickaxe and wood >= 3 and stone >= 2:
		wood -= 3
		stone -= 2
		has_pickaxe = true


func _craft_sword() -> void:
	if not has_sword and wood >= 2 and stone >= 4:
		wood -= 2
		stone -= 4
		has_sword = true


func _craft_wall() -> void:
	if wood >= 5:
		wood -= 5
		build_mode = true
		build_hint.visible = true
		craft_panel.visible = false


func _toggle_build() -> void:
	if wood >= 5:
		build_mode = not build_mode
		build_hint.visible = build_mode


func _place_wall(world_pos: Vector2) -> void:
	if wood < 5:
		build_mode = false
		build_hint.visible = false
		return
	var snapped := (world_pos / 48.0).round() * 48.0
	snapped = snapped.clamp(Vector2(48, 48), Vector2(WORLD - 48, WORLD - 48))
	if snapped.distance_to(player.position) < 60.0:
		return
	wood -= 5
	var wnode := _make_box(Color("#8a5a2b"), Vector2(48, 48))
	wnode.position = snapped
	add_child(wnode)
	walls.append({"pos": snapped, "node": wnode})
	build_hint.visible = false
	build_mode = false


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if dead:
			return
		if event.pressed:
			if event.position.x < get_viewport_rect().size.x * 0.42 and joy_id == -1:
				joy_id = event.index
				joy_center = event.position
				joy_base.position = joy_center - joy_base.size / 2.0
				joy_knob.position = joy_center - joy_knob.size / 2.0
			elif build_mode:
				var world_pos := _screen_to_world(event.position)
				_place_wall(world_pos)
		else:
			if event.index == joy_id:
				joy_id = -1
				move_vec = Vector2.ZERO
				joy_knob.position = joy_base.position + joy_base.size / 2.0 - joy_knob.size / 2.0
	elif event is InputEventScreenDrag and event.index == joy_id:
		var delta: Vector2 = event.position - joy_center
		var maxl := 60.0
		if delta.length() > maxl:
			delta = delta.normalized() * maxl
		joy_knob.position = joy_center + delta - joy_knob.size / 2.0
		move_vec = delta / maxl

	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_W:
				move_vec.y = -1
			KEY_S:
				move_vec.y = 1
			KEY_A:
				move_vec.x = -1
			KEY_D:
				move_vec.x = 1
			KEY_SPACE:
				_on_action()


func _screen_to_world(sp: Vector2) -> Vector2:
	return player.position + (sp - get_viewport_rect().size / 2.0) / cam.zoom.x


func _update_ui() -> void:
	hp_fill.size.x = 220.0 * (hp / 100.0)
	hunger_fill.size.x = 220.0 * (hunger / 100.0)
	lbl_wood.text = "Дерево: " + str(wood)
	lbl_stone.text = "Камень: " + str(stone)
	lbl_day.text = "День " + str(days)
	lbl_phase.text = "НОЧЬ — волки идут!" if is_night else "День — собирай ресурсы"


func _die() -> void:
	dead = true
	save_best()
	over_overlay.visible = true
	ov_lbl.text = "Вы погибли\nДней выжито: " + str(days) + "\nРекорд: " + str(best_days)


func _restart() -> void:
	dead = false
	hp = 100.0
	hunger = 100.0
	wood = 0
	stone = 0
	has_axe = false
	has_pickaxe = false
	has_sword = false
	days = 1
	is_night = false
	phase_timer = DAY_LEN
	build_mode = false
	build_hint.visible = false
	over_overlay.visible = false
	_clear_enemies()
	for r in resources:
		var rn: Node2D = r["node"]
		rn.queue_free()
	resources.clear()
	for w in walls:
		var wn: Node2D = w["node"]
		wn.queue_free()
	walls.clear()
	for i in 42:
		_spawn_resource("tree")
	for i in 32:
		_spawn_resource("rock")
	for i in 30:
		_spawn_resource("bush")
	player.position = Vector2(WORLD / 2.0, WORLD / 2.0)


func save_best() -> void:
	var f := ConfigFile.new()
	f.set_value("g", "best", best_days)
	f.save("user://save_surv.cfg")


func load_best() -> void:
	var f := ConfigFile.new()
	if f.load("user://save_surv.cfg") == OK:
		best_days = int(f.get_value("g", "best", 0))
