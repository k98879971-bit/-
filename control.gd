extends Control


var score: int = 0
var base_click: int = 1
var multiplier_bought: bool = false
var auto_clicker: bool = false
var rebirths: int = 0
var world: int = 1
var world2_unlocked: bool = false

const SAVE_PATH := "user://save.cfg"
const X2_COST := 50
const AUTO_COST := 50000
const WORLD2_COST := 1000000
const AUTO_INTERVAL := 2.0

@onready var click_button: Button = $Button
@onready var score_label: Label = $Label
@onready var info_label: Label = $MultiplierLabel
@onready var shop_button: Button = $ShopButton
@onready var auto_button: Button = $AutoClickerButton
@onready var rebirth_button: Button = $RebirthButton
@onready var world_button: Button = $WorldButton
@onready var auto_timer: Timer = $AutoTimer


func _ready() -> void:
	load_score()
	setup_auto_timer()
	if world == 2:
		resize_click_button()
	update_ui()


func effective_click() -> int:
	return base_click * (1 << rebirths)


func _on_button_pressed() -> void:
	score += effective_click()
	if world == 2:
		randomize_button()
	update_ui()
	save_score()


func _on_shop_button_pressed() -> void:
	if multiplier_bought:
		return
	if score >= X2_COST:
		score -= X2_COST
		multiplier_bought = true
		base_click = 2
		update_ui()
		save_score()


func _on_auto_button_pressed() -> void:
	if auto_clicker:
		return
	if score >= AUTO_COST:
		score -= AUTO_COST
		auto_clicker = true
		setup_auto_timer()
		update_ui()
		save_score()


func _on_rebirth_button_pressed() -> void:
	# Сброс счёта и улучшений, множитель x2 навсегда. Авто-клик и мир 2 сохраняются.
	score = 0
	multiplier_bought = false
	base_click = 1
	rebirths += 1
	update_ui()
	save_score()


func _on_world_button_pressed() -> void:
	if world == 1:
		if not world2_unlocked:
			return
		world = 2
		resize_click_button()
		randomize_button()
	else:
		world = 1
		reset_click_button()
	update_ui()
	save_score()


func _on_auto_timer_timeout() -> void:
	score += effective_click()
	update_ui()
	save_score()


func setup_auto_timer() -> void:
	if auto_clicker:
		auto_timer.wait_time = AUTO_INTERVAL
		auto_timer.start()
	else:
		auto_timer.stop()


func randomize_button() -> void:
	var bounds := size
	var bw := click_button.size.x
	var bh := click_button.size.y
	var nx := randf_range(0.0, maxf(bounds.x - bw, 0.0))
	var ny := randf_range(0.0, maxf(bounds.y - bh, 0.0))
	click_button.position = Vector2(nx, ny)


func resize_click_button() -> void:
	click_button.size = Vector2(200, 180)
	click_button.add_theme_font_size_override("font_size", 120)


func reset_click_button() -> void:
	click_button.position = Vector2(395, 303)
	click_button.size = Vector2(314, 281)
	click_button.add_theme_font_size_override("font_size", 200)


func update_ui() -> void:
	score_label.text = "Счёт: " + str(score)
	info_label.text = "Клик: +" + str(effective_click()) + "   |   Мир " + str(world)

	if multiplier_bought:
		shop_button.text = "x2 куплено"
		shop_button.disabled = true
	else:
		shop_button.text = "x2 клик — " + str(X2_COST)

	if auto_clicker:
		auto_button.text = "Авто-клик куплен"
		auto_button.disabled = true
	else:
		auto_button.text = "Авто-клик — " + str(AUTO_COST)

	rebirth_button.text = "Перерождение\nстанет x" + str(1 << (rebirths + 1))

	if world == 2:
		world_button.text = "Вернуться в мир 1"
	else:
		world_button.text = "Мир 2 (1 млн)"
		world_button.disabled = not world2_unlocked


func save_score() -> void:
	var f := ConfigFile.new()
	f.set_value("game", "score", score)
	f.set_value("game", "base_click", base_click)
	f.set_value("game", "multiplier_bought", multiplier_bought)
	f.set_value("game", "auto_clicker", auto_clicker)
	f.set_value("game", "rebirths", rebirths)
	f.set_value("game", "world", world)
	f.set_value("game", "world2_unlocked", world2_unlocked)
	var err := f.save(SAVE_PATH)
	if err != OK:
		push_warning("Не удалось сохранить: " + str(err))


func load_score() -> void:
	var f := ConfigFile.new()
	if f.load(SAVE_PATH) == OK:
		score = int(f.get_value("game", "score", 0))
		base_click = int(f.get_value("game", "base_click", 1))
		multiplier_bought = bool(f.get_value("game", "multiplier_bought", false))
		auto_clicker = bool(f.get_value("game", "auto_clicker", false))
		rebirths = int(f.get_value("game", "rebirths", 0))
		world = int(f.get_value("game", "world", 1))
		world2_unlocked = bool(f.get_value("game", "world2_unlocked", false))


func _process(_delta: float) -> void:
	# Открываем мир 2 при достижении 1 млн кликов
	if not world2_unlocked and score >= WORLD2_COST:
		world2_unlocked = true
		update_ui()
		save_score()


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		save_score()
