package services

import (
	"airri-backend/internal/models"
	"time"

	"gorm.io/gorm"
)

func StringPtr(s string) *string {
	return &s
}

func LogEvent(
	db *gorm.DB,
	userID string,
	sessionID *string,
	eventType string,
	targetType *string,
	targetID *string,
	metadata string,
) error {
	event := models.InteractionEvent{
		UserID:    userID,
		SessionID: sessionID,
		EventType: eventType,
		TargetType: targetType,
		TargetID:   targetID,
		Metadata:  metadata,
		CreatedAt: time.Now(),
	}

	return db.Create(&event).Error
}