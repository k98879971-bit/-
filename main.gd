extends Control


const GRID := 4
const SPAWN_CHANCE_4 := 0.1
const SAVE_PATH := "user://save2048.cfg"

const COLORS := {
	0: Color("#cdc1b4"),
	2: Color("#eee4da"),
	4: Color("#ede0c8"),
	8: Color("#f2b179"),
	16: Color("#f59563"),
	32: Color("#f67c5f"),
	64: Color("#f65e3b"),
	128: Color("#edcf72"),
	256: Color("#edcc61"),
	512: Color("#edc850"),
	1024: Color("#edc53f"),
	2048: Color("#edc22e"),
	4096: Color("#3c3a32"),
	8192: Color("#3c3a32"),
}

var board: Array = []
var score: int = 0
var best: int = 0
var game_over: bool = false
var won: bool = false

var tile_bg: Array = []
var tile_lbl: Array = []

var title: Label
var score_label: Label
var best_label: Label
var new_button: Button
var overlay: ColorRect
var overlay_label: Label
var overlay_button: Button

var touch_start: Vector2 = Vector2.ZERO
var dragging: bool = false


func _ready() -> void:
	build_ui()
	if not load_game():
		new_game()
	else:
		render()
		check_state()


func build_ui() -> void:
	var bg := ColorRect.new()
	bg.color = Color("#faf8ef")
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	title = Label.new()
	title.text = "2048"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 72)
	title.add_theme_color_override("font_color", Color("#776e65"))
	add_child(title)

	score_label = Label.new()
	score_label.add_theme_font_size_override("font_size", 34)
	score_label.add_theme_color_override("font_color", Color("#776e65"))
	add_child(score_label)

	best_label = Label.new()
	best_label.add_theme_font_size_override("font_size", 34)
	best_label.add_theme_color_override("font_color", Color("#776e65"))
	add_child(best_label)

	new_button = Button.new()
	new_button.text = "Новая игра"
	new_button.add_theme_font_size_override("font_size", 30)
	new_button.pressed.connect(new_game)
	add_child(new_button)

	for i in GRID * GRID:
		var c := ColorRect.new()
		c.color = COLORS[0]
		add_child(c)
		tile_bg.append(c)
		var l := Label.new()
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		add_child(l)
		tile_lbl.append(l)

	overlay = ColorRect.new()
	overlay.color = Color(0, 0, 0, 0.55)
	overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	overlay.visible = false
	add_child(overlay)

	overlay_label = Label.new()
	overlay_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	overlay_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	overlay_label.add_theme_font_size_override("font_size", 64)
	overlay_label.add_theme_color_override("font_color", Color.WHITE)
	add_child(overlay_label)

	overlay_button = Button.new()
	overlay_button.text = "Играть снова"
	overlay_button.add_theme_font_size_override("font_size", 40)
	overlay_button.pressed.connect(new_game)
	add_child(overlay_button)

	layout()


func layout() -> void:
	var w := size.x
	var h := size.y

	title.position = Vector2(w * 0.5 - 150, 6)
	title.size = Vector2(300, 80)

	score_label.position = Vector2(w * 0.5 - 300, 92)
	score_label.size = Vector2(280, 46)
	best_label.position = Vector2(w * 0.5 + 20, 92)
	best_label.size = Vector2(280, 46)

	new_button.position = Vector2(w - 210, 24)
	new_button.size = Vector2(190, 54)

	var header_h := 150.0
	var avail_h := h - header_h - 20
	var tile := clampf(min(w - 40, avail_h) / 4.6, 40.0, 140.0)
	var gap := tile * 0.12
	var bs := 4 * tile + 5 * gap
	var ox := (w - bs) / 2.0
	var oy := header_h + maxf(avail_h - bs, 0.0) / 2.0
	for r in GRID:
		for c in GRID:
			var idx := r * GRID + c
			var pos := Vector2(ox + gap + c * (tile + gap), oy + gap + r * (tile + gap))
			tile_bg[idx].position = pos
			tile_bg[idx].size = Vector2(tile, tile)
			tile_lbl[idx].position = pos
			tile_lbl[idx].size = Vector2(tile, tile)

	overlay_label.position = Vector2(0, h * 0.38)
	overlay_label.size = Vector2(w, 130)
	overlay_button.position = Vector2(w * 0.5 - 150, h * 0.38 + 150)
	overlay_button.size = Vector2(300, 84)


func new_game() -> void:
	board = []
	for r in GRID:
		var row := []
		for c in GRID:
			row.append(0)
		board.append(row)
	score = 0
	game_over = false
	won = false
	spawn_tile()
	spawn_tile()
	render()
	save_game()


func spawn_tile() -> void:
	var empty := []
	for r in GRID:
		for c in GRID:
			if board[r][c] == 0:
				empty.append(Vector2i(r, c))
	if empty.is_empty():
		return
	var pos: Vector2i = empty[randi() % empty.size()]
	board[pos.x][pos.y] = 4 if randf() < SPAWN_CHANCE_4 else 2


func _merge_line(line: Array) -> Array:
	var vals := []
	for v in line:
		if v != 0:
			vals.append(v)
	var merged := []
	var gained := 0
	var i := 0
	while i < vals.size():
		if i + 1 < vals.size() and vals[i] == vals[i + 1]:
			var nv: int = vals[i] * 2
			merged.append(nv)
			gained += nv
			i += 2
		else:
			merged.append(vals[i])
			i += 1
	while merged.size() < GRID:
		merged.append(0)
	return [merged, gained]


func move(dir: int) -> void:
	if game_over:
		return
	var moved := false
	var gained := 0
	match dir:
		0:  # left
			for r in GRID:
				var res: Array = _merge_line(board[r])
				gained += res[1]
				if res[0] != board[r]:
					moved = true
					board[r] = res[0]
		1:  # right
			for r in GRID:
				var rev: Array = board[r].duplicate()
				rev.reverse()
				var res: Array = _merge_line(rev)
				gained += res[1]
				res[0].reverse()
				if res[0] != board[r]:
					moved = true
					board[r] = res[0]
		2:  # up
			for c in GRID:
				var col := []
				for r in GRID:
					col.append(board[r][c])
				var res: Array = _merge_line(col)
				gained += res[1]
				for r in GRID:
					if board[r][c] != res[0][r]:
						moved = true
					board[r][c] = res[0][r]
		3:  # down
			for c in GRID:
				var col := []
				for r in GRID:
					col.append(board[r][c])
				col.reverse()
				var res: Array = _merge_line(col)
				gained += res[1]
				res[0].reverse()
				for r in GRID:
					if board[r][c] != res[0][r]:
						moved = true
					board[r][c] = res[0][r]
	if moved:
		score += gained
		if score > best:
			best = score
		spawn_tile()
		render()
		check_state()
		save_game()


func check_state() -> void:
	if not won and _has_tile(2048):
		won = true
	if not _can_move():
		game_over = true
	update_overlay()


func _has_tile(v: int) -> bool:
	for r in GRID:
		for c in GRID:
			if board[r][c] >= v:
				return true
	return false


func _has_empty() -> bool:
	for r in GRID:
		for c in GRID:
			if board[r][c] == 0:
				return true
	return false


func _can_move() -> bool:
	if _has_empty():
		return true
	for r in GRID:
		for c in GRID:
			var v: int = board[r][c]
			if r + 1 < GRID and board[r + 1][c] == v:
				return true
			if c + 1 < GRID and board[r][c + 1] == v:
				return true
	return false


func render() -> void:
	score_label.text = "Счёт: " + str(score)
	best_label.text = "Рекорд: " + str(best)
	for r in GRID:
		for c in GRID:
			var v: int = board[r][c]
			var idx := r * GRID + c
			tile_bg[idx].color = COLORS.get(v, COLORS[0])
			var lbl: Label = tile_lbl[idx]
			if v == 0:
				lbl.text = ""
			else:
				lbl.text = str(v)
				if v <= 4:
					lbl.add_theme_color_override("font_color", Color("#776e65"))
				else:
					lbl.add_theme_color_override("font_color", Color("#f9f6f2"))
			if v >= 10000:
				lbl.add_theme_font_size_override("font_size", 30)
			elif v >= 1000:
				lbl.add_theme_font_size_override("font_size", 38)
			elif v >= 100:
				lbl.add_theme_font_size_override("font_size", 46)
			else:
				lbl.add_theme_font_size_override("font_size", 54)


func update_overlay() -> void:
	if game_over:
		overlay.visible = true
		overlay_label.text = "Игра окончена!\nСчёт: " + str(score)
	else:
		overlay.visible = false
	if won and not game_over:
		# короткое поздравление в заголовке
		title.text = "2048 🎉"


func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed:
			touch_start = event.position
			dragging = true
		else:
			if dragging:
				_handle_swipe(event.position - touch_start)
				dragging = false
	elif event is InputEventScreenDrag:
		if dragging:
			var delta: Vector2 = event.position - touch_start
			if delta.length() > 60.0:
				_handle_swipe(delta)
				dragging = false


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_LEFT:
				move(0)
			KEY_RIGHT:
				move(1)
			KEY_UP:
				move(2)
			KEY_DOWN:
				move(3)
			KEY_R:
				new_game()


func _handle_swipe(delta: Vector2) -> void:
	if abs(delta.x) > abs(delta.y):
		if delta.x > 0:
			move(1)
		else:
			move(0)
	else:
		if delta.y > 0:
			move(3)
		else:
			move(2)


func save_game() -> void:
	var f := ConfigFile.new()
	f.set_value("g", "score", score)
	f.set_value("g", "best", best)
	f.set_value("g", "won", won)
	var flat := []
	for r in GRID:
		for c in GRID:
			flat.append(board[r][c])
	f.set_value("g", "board", flat)
	f.save(SAVE_PATH)


func load_game() -> bool:
	var f := ConfigFile.new()
	if f.load(SAVE_PATH) != OK:
		return false
	score = int(f.get_value("g", "score", 0))
	best = int(f.get_value("g", "best", 0))
	won = bool(f.get_value("g", "won", false))
	var flat: Array = f.get_value("g", "board", [])
	if flat.size() != GRID * GRID:
		return false
	board = []
	for r in GRID:
		var row := []
		for c in GRID:
			row.append(int(flat[r * GRID + c]))
		board.append(row)
	return true


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		layout()
	elif what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		save_game()
