extends Control


var score: int = 0
var click_value: int = 1
var multiplier_bought: bool = false

const SAVE_PATH := "user://save.cfg"
const UPGRADE_COST := 50

@onready var score_label: Label = $Label
@onready var click_label: Label = $MultiplierLabel
@onready var shop_button: Button = $ShopButton


func _ready() -> void:
	load_score()
	update_ui()


func _on_button_pressed() -> void:
	score += click_value
	update_ui()
	save_score()


func _on_shop_button_pressed() -> void:
	if multiplier_bought:
		return
	if score >= UPGRADE_COST:
		score -= UPGRADE_COST
		multiplier_bought = true
		click_value = 2
		update_ui()
		save_score()


func update_ui() -> void:
	score_label.text = "Счёт: " + str(score)
	click_label.text = "Клик: +" + str(click_value)
	if multiplier_bought:
		shop_button.text = "x2 куплено"
		shop_button.disabled = true
	else:
		shop_button.text = "x2 клик — " + str(UPGRADE_COST)


func save_score() -> void:
	var f := ConfigFile.new()
	f.set_value("game", "score", score)
	f.set_value("game", "click_value", click_value)
	f.set_value("game", "multiplier_bought", multiplier_bought)
	var err := f.save(SAVE_PATH)
	if err != OK:
		push_warning("Не удалось сохранить: " + str(err))


func load_score() -> void:
	var f := ConfigFile.new()
	if f.load(SAVE_PATH) == OK:
		score = int(f.get_value("game", "score", 0))
		click_value = int(f.get_value("game", "click_value", 1))
		multiplier_bought = bool(f.get_value("game", "multiplier_bought", false))


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		save_score()
