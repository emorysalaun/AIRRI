package main

import (
	"airri-backend/internal/db"
	"airri-backend/internal/handlers"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func main() {
	db.Init()

	e := echo.New()
	e.Use(middleware.CORS())

	// health check route
	e.GET("/", func(c echo.Context) error {
		return c.String(200, "AIRRI backend running")
	})

	e.POST("/api/v0/interactions", handlers.CreateInteractionEvent)

	e.Logger.Fatal(e.Start(":8080"))
}