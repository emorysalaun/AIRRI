package models

import "time"

type Render struct {
	ID uint `gorm:"column:id;primaryKey;autoIncrement"`

	SessionID string  `gorm:"column:session_id;not null"`
	Session   Session `gorm:"foreignKey:SessionID"`

	ConfigID uint         `gorm:"column:config_id;not null"`
	Config   RenderConfig `gorm:"foreignKey:ConfigID"`

	SourceText string `gorm:"column:source_text;type:text;not null"`
	FilePath   string `gorm:"column:file_path"`

	CreatedAt time.Time `gorm:"column:created_at;not null;default:CURRENT_TIMESTAMP"`
	UpdatedAt time.Time `gorm:"column:updated_at;not null;default:CURRENT_TIMESTAMP"`
}

func (Render) TableName() string {
	return "renders"
}
