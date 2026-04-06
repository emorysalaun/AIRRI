package models

import "time"

type Session struct {
	ID        string     `gorm:"primaryKey" json:"id"`
	CreatedAt time.Time  `json:"created_at"`
	EndedAt   *time.Time `json:"ended_at,omitempty"`
}

func (Session) TableName() string {
	return "sessions"
}
