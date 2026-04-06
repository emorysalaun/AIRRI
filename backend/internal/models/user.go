package models

import "time"

type User struct {
	ID string `gorm:"column:id;primaryKey;type:uuid"`

	Email    string `gorm:"column:email;unique;not null"`
	Password string `gorm:"column:password;not null"`

	CreatedAt time.Time `gorm:"column:created_at;not null;default:CURRENT_TIMESTAMP"`
	UpdatedAt time.Time `gorm:"column:updated_at;not null;default:CURRENT_TIMESTAMP"`
}

func (User) TableName() string {
	return "users"
}
