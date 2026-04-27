package models

import "time"

type InteractionEvent struct {
	ID uint `gorm:"primaryKey" json:"id"`

	SessionID *string  `gorm:"column:session_id;index" json:"session_id,omitempty"`
	Session   *Session `gorm:"foreignKey:SessionID;references:ID"`

	UserID string `gorm:"column:user_id;index;not null" json:"user_id"`
	User   User   `gorm:"foreignKey:UserID;references:ID"`

	EventType string `gorm:"column:event_type;index;not null" json:"event_type"`

	TargetType *string `gorm:"column:target_type;index" json:"target_type,omitempty"`
	TargetID   *string `gorm:"column:target_id;index" json:"target_id,omitempty"`

	Metadata string `gorm:"type:TEXT" json:"metadata"`

	CreatedAt time.Time `json:"created_at"`
}

func (InteractionEvent) TableName() string {
	return "interaction_events"
}