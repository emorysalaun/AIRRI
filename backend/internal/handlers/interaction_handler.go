package handlers

import (
	"airri-backend/internal/db"
	"airri-backend/internal/services"
	"net/http"

	"github.com/labstack/echo/v4"
)

type CreateInteractionEventRequest struct {
	SessionID  *string `json:"session_id"`
	EventType  string  `json:"event_type"`
	TargetType *string `json:"target_type"`
	TargetID   *string `json:"target_id"`
	Metadata   string  `json:"metadata"`
}

func CreateInteractionEvent(c echo.Context) error {
	var req CreateInteractionEventRequest

	err := c.Bind(&req)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{
			"error": "invalid request body",
		})
	}

	if req.EventType == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{
			"error": "event_type is required",
		})
	}

	// temporary until JWT is added
	userID := "ee487754-0af9-42d1-a869-7bc195b2f315"

	err = services.LogEvent(
		db.DB,
		userID,
		req.SessionID,
		req.EventType,
		req.TargetType,
		req.TargetID,
		req.Metadata,
	)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to create interaction event",
		})
	}

	return c.JSON(http.StatusCreated, map[string]string{
		"message": "interaction event created",
	})
}