package main

import (
	"airri-backend/internal/db"
	"airri-backend/internal/models"
	"log"
)

func main() {
	log.Println("Starting migration...")

	db.Init()

	err := db.DB.AutoMigrate(
		&models.User{},
		&models.Session{},
		&models.RenderConfig{},
		&models.Render{},
		&models.OCRResult{},
		&models.InteractionEvent{},
	)
	if err != nil {
		log.Fatal("Migration failed:", err)
	}

	log.Println("Migration complete.")
}