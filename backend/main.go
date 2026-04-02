package main

import (
	"airri-backend/internal/db"
	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func main() {
	db.Init()

	e := echo.New()
	e.Use(middleware.CORS())

	e.GET("/", func(c echo.Context) error {
		return c.String(200, "AIRRI backend running")
	})

	e.Logger.Fatal(e.Start(":8080"))
}