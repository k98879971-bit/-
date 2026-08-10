extends Control

var score: int = 0

@onready var score_label: Label = $Label

func _ready():
	update_score()

func _on_button_pressed():
	score += 1
	update_score()

func update_score():
	if score_label:
		score_label.text = "Счёт: " + str(score)
