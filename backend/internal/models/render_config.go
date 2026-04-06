package models

import "time"

type RenderConfig struct {
	ID uint `gorm:"column:id;primaryKey;autoIncrement"`

	Noise         float64 `gorm:"column:noise;not null;default:0"`
	Stripes       float64 `gorm:"column:stripes;not null;default:0"`
	StripeMode    string  `gorm:"column:stripe_mode;not null"`
	StripeAngle   float64 `gorm:"column:stripe_angle;not null;default:45"`
	Color         string  `gorm:"column:color;not null"`
	OpacityJitter float64 `gorm:"column:opacity_jitter;not null;default:0"`

	FontSize    int     `gorm:"column:font_size;not null;default:16"`
	LineSpacing float64 `gorm:"column:line_spacing;not null;default:0"`
	CharSpacing float64 `gorm:"column:char_spacing;not null;default:0"`
	WordSpacing float64 `gorm:"column:word_spacing;not null;default:0"`

	Seed int64 `gorm:"column:seed;not null"`

	CreatedAt time.Time `gorm:"column:created_at;not null;default:CURRENT_TIMESTAMP"`
	UpdatedAt time.Time `gorm:"column:updated_at;not null;default:CURRENT_TIMESTAMP"`
}

func (RenderConfig) TableName() string {
	return "render_configs"
}
