package models

import "time"

type InteractionEvent struct {
	ID uint `gorm:"primaryKey" json:"id"`

	SessionID *string `gorm:"column:session_id;index" json:"session_id,omitempty"`

	UserID string `gorm:"column:user_id;index;not null" json:"user_id"`

	EventType string `gorm:"column:event_type;index;not null" json:"event_type"`

	Metadata string `gorm:"type:TEXT;not null" json:"metadata"`

	CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
}

func (InteractionEvent) TableName() string {
	return "interaction_events"
}
