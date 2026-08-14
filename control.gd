extends Control


var score: int = 0

const SAVE_PATH := "user://save.cfg"

@onready var score_label: Label = $Label


func _ready() -> void:
	load_score()
	update_score()


func _on_button_pressed() -> void:
	score += 1
	update_score()
	save_score()


func update_score() -> void:
	score_label.text = "Счёт: " + str(score)


func save_score() -> void:
	var f := ConfigFile.new()
	f.set_value("game", "score", score)
	var err := f.save(SAVE_PATH)
	if err != OK:
		push_warning("Не удалось сохранить счёт: " + str(err))


func load_score() -> void:
	var f := ConfigFile.new()
	if f.load(SAVE_PATH) == OK:
		score = int(f.get_value("game", "score", 0))


func _notification(what: int) -> void:
	# Страховка: сохраняем при сворачивании/потере фокуса (Android)
	if what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		save_score()
