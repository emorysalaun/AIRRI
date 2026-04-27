package main

import (
	"airri-backend/internal/db"
	"airri-backend/internal/models"
	"airri-backend/internal/services"
	"log"
	"time"

	"github.com/google/uuid"
)

func main() {
	log.Println("Running test script...")

	db.Init()

	userID := uuid.New().String()
	sessionID := uuid.New().String()

	// --- Create test user ---
	user := models.User{
		ID:        userID,
		Email:     "test@example.com",
		Password:  "test-password",
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	err := db.DB.FirstOrCreate(&user, models.User{Email: user.Email}).Error
	if err != nil {
		log.Fatal("failed to create user:", err)
	}

	// --- Create test session ---
	session := models.Session{
		ID:        sessionID,
		UserID:    &user.ID,
		CreatedAt: time.Now(),
	}

	err = db.DB.FirstOrCreate(&session, models.Session{ID: session.ID}).Error
	if err != nil {
		log.Fatal("failed to create session:", err)
	}

	// --- Log test interaction event ---
	err = services.LogEvent(
		db.DB,
		user.ID,
		&session.ID,
		"test_event",
		services.StringPtr("session"),
		&session.ID,
		`{"message":"hello world"}`,
	)
	if err != nil {
		log.Fatal("failed to log event:", err)
	}

	log.Println("Test data inserted successfully.")
}