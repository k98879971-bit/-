extends Control



var score: int = 0

@onready var score_label = $Label

func _ready():
	update_score()

func _on_button_pressed():
	score += 1
	update_score()

func update_score():
	score_label.text = "Счёт: " + str(score)



var clicks := 0

@onready var label = $Label


 
