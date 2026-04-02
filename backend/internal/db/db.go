package db

import (
	"airri-backend/internal/models"
	"log"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

var DB *gorm.DB

func Init() {
	db, err := gorm.Open(sqlite.Open("../data/airri.db"), &gorm.Config{})
	if err != nil {
		log.Fatal("failed to connect database:", err)
	}

	err = db.AutoMigrate(&models.Session{})
	if err != nil {
		log.Fatal("failed to migrate database:", err)
	}

	DB = db
}