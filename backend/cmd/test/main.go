package main

import (
	"airri-backend/internal/db"
	"airri-backend/internal/models"
	"log"
	"time"
)

func main() {
	log.Println("Running test script...")

	db.Init()

	userID := "11111111-1111-1111-1111-111111111111"
	sessionID := "22222222-2222-2222-2222-222222222222"

	user := models.User{
		ID:        userID,
		Email:     "test@example.com",
		Password:  "test-password",
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	if err := db.DB.FirstOrCreate(&user, models.User{ID: user.ID}).Error; err != nil {
		log.Fatal("failed to create user:", err)
	}

	session := models.Session{
		ID:        sessionID,
		UserID:    &user.ID,
		CreatedAt: time.Now(),
	}

	if err := db.DB.FirstOrCreate(&session, models.Session{ID: session.ID}).Error; err != nil {
		log.Fatal("failed to create session:", err)
	}

	event := models.InteractionEvent{
		UserID:    user.ID,
		SessionID: &session.ID,
		EventType: "test_event",
		Metadata:  `{"message":"hello world"}`,
		CreatedAt: time.Now(),
	}

	if err := db.DB.Create(&event).Error; err != nil {
		log.Fatal("failed to create event:", err)
	}

	log.Println("Test data inserted successfully.")
}