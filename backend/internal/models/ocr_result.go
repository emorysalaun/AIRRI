package models

import "time"

type OCRResult struct {
	ID uint `gorm:"column:id;primaryKey;autoIncrement"`

	RenderID uint   `gorm:"column:render_id;not null"`
	Model    string `gorm:"column:model;not null"`

	GeneratedText string  `gorm:"column:generated_text;type:text"`
	CER           float64 `gorm:"column:cer;not null"`

	CreatedAt time.Time `gorm:"column:created_at;not null;default:CURRENT_TIMESTAMP"`
}

func (OCRResult) TableName() string {
	return "ocr_results"
}
