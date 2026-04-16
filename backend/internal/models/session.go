package models

import "time"

type Session struct {
	ID        string     `gorm:"primaryKey" json:"id"`
	UserID    *string    `gorm:"column:user_id;index" json:"user_id,omitempty"`
	User      *User      `gorm:"foreignKey:UserID;references:ID" json:"user,omitempty"`
	CreatedAt time.Time  `json:"created_at"`
	EndedAt   *time.Time `json:"ended_at,omitempty"`
}

func (Session) TableName() string {
	return "sessions"
}
