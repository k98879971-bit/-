extends Control


const SAVE_PATH := "user://save_dodge.cfg"

var player: ColorRect
var player_size := Vector2(64, 64)
var target_x: float = 0.0

var blocks: Array = []  # [{rect, speed}]
var fall_speed: float = 320.0
var spawn_interval: float = 0.9
var spawn_timer: float = 0.0

var score: int = 0
var best: int = 0
var running: bool = false

var score_label: Label
var best_label: Label
var overlay: ColorRect
var overlay_label: Label
var overlay_button: Button
var hint_label: Label


func _ready() -> void:
	build_ui()
	load_best()
	reset_game()


func build_ui() -> void:
	var bg := ColorRect.new()
	bg.color = Color("#101820")
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	player = ColorRect.new()
	player.color = Color("#f65058")
	player.size = player_size
	add_child(player)

	score_label = Label.new()
	score_label.add_theme_font_size_override("font_size", 48)
	score_label.add_theme_color_override("font_color", Color.WHITE)
	score_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(score_label)

	best_label = Label.new()
	best_label.add_theme_font_size_override("font_size", 28)
	best_label.add_theme_color_override("font_color", Color("#8aa0b8"))
	best_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(best_label)

	hint_label = Label.new()
	hint_label.text = "Веди пальцем — уклоняйся!"
	hint_label.add_theme_font_size_override("font_size", 24)
	hint_label.add_theme_color_override("font_color", Color("#8aa0b8"))
	hint_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(hint_label)

	overlay = ColorRect.new()
	overlay.color = Color(0, 0, 0, 0.6)
	overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	overlay.visible = false
	add_child(overlay)

	overlay_label = Label.new()
	overlay_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	overlay_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	overlay_label.add_theme_font_size_override("font_size", 56)
	overlay_label.add_theme_color_override("font_color", Color.WHITE)
	add_child(overlay_label)

	overlay_button = Button.new()
	overlay_button.text = "Ещё раз"
	overlay_button.add_theme_font_size_override("font_size", 40)
	overlay_button.pressed.connect(reset_game)
	add_child(overlay_button)


func layout_ui() -> void:
	var w := size.x
	var h := size.y
	score_label.position = Vector2(0, 40)
	score_label.size = Vector2(w, 60)
	best_label.position = Vector2(0, 104)
	best_label.size = Vector2(w, 40)
	hint_label.position = Vector2(0, h - 70)
	hint_label.size = Vector2(w, 40)
	player.position.y = h - player_size.y - 30
	if player.position.x == 0:
		player.position.x = (w - player_size.x) / 2.0
	overlay_label.position = Vector2(0, h * 0.36)
	overlay_label.size = Vector2(w, 150)
	overlay_button.position = Vector2(w * 0.5 - 150, h * 0.36 + 160)
	overlay_button.size = Vector2(300, 84)


func reset_game() -> void:
	for b in blocks:
		if is_instance_valid(b.rect):
			b.rect.queue_free()
	blocks.clear()
	score = 0
	fall_speed = 320.0
	spawn_interval = 0.9
	spawn_timer = 0.0
	running = true
	overlay.visible = false
	var w := size.x
	player.position = Vector2((w - player_size.x) / 2.0, size.y - player_size.y - 30)
	target_x = player.position.x
	update_score()


func update_score() -> void:
	score_label.text = str(score)
	best_label.text = "Рекорд: " + str(best)


func _process(delta: float) -> void:
	if not running:
		return

	# движение игрока к точке касания
	var dx := target_x - player.position.x
	if abs(dx) > 2.0:
		player.position.x += dx * 0.5
	else:
		player.position.x = target_x

	# спавн блоков
	spawn_timer -= delta
	if spawn_timer <= 0.0:
		spawn_block()
		spawn_timer = spawn_interval
		spawn_interval = maxf(spawn_interval * 0.985, 0.28)
		fall_speed += 6.0

	# падение блоков
	var to_remove := []
	for b in blocks:
		var rect: ColorRect = b.rect
		rect.position.y += b.speed * delta
		if rect.position.y > size.y:
			to_remove.append(b)
			score += 1
			if score > best:
				best = score
			update_score()

	for b in to_remove:
		b.rect.queue_free()
		blocks.erase(b)

	# коллизия
	var pr := Rect2(player.position, player.size)
	for b in blocks:
		var br := Rect2(b.rect.position, b.rect.size)
		if pr.intersects(br):
			game_over()
			return


func spawn_block() -> void:
	var rect := ColorRect.new()
	var bw := randf_range(50, 110)
	rect.size = Vector2(bw, bw)
	rect.color = Color("#f2aa4c") if randf() < 0.5 else Color("#2f8f83")
	var w := size.x
	rect.position = Vector2(randf_range(0, w - bw), -bw)
	var spd := fall_speed * randf_range(0.85, 1.15)
	blocks.append({"rect": rect, "speed": spd})
	add_child(rect)


func game_over() -> void:
	running = false
	save_best()
	overlay.visible = true
	overlay_label.text = "Игра окончена!\nСчёт: " + str(score)
	update_score()


func _input(event: InputEvent) -> void:
	if not running:
		return
	if event is InputEventScreenTouch or event is InputEventScreenDrag:
		target_x = event.position.x - player_size.x / 2.0
		target_x = clampf(target_x, 0.0, size.x - player_size.x)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_LEFT:
			target_x = clampf(target_x - 40.0, 0.0, size.x - player_size.x)
		elif event.keycode == KEY_RIGHT:
			target_x = clampf(target_x + 40.0, 0.0, size.x - player_size.x)
		elif event.keycode == KEY_R and not running:
			reset_game()


func save_best() -> void:
	var f := ConfigFile.new()
	f.set_value("g", "best", best)
	f.save(SAVE_PATH)


func load_best() -> void:
	var f := ConfigFile.new()
	if f.load(SAVE_PATH) == OK:
		best = int(f.get_value("g", "best", 0))


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		layout_ui()
	elif what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		if running:
			save_best()
