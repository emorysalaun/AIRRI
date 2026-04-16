package main

import (
	"airri-backend/internal/db"
	"airri-backend/internal/handlers"

	"github.com/labstack/echo/v4"
)

func main() {
	db.Init()

	e := echo.New()

	// register routes
	e.POST("/api/v0/interactions", handlers.CreateInteractionEvent)

	// start server
	e.Logger.Fatal(e.Start(":8080"))
}