package main

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func main() {
	// Инициализация HTTP-сервера с настройками по умолчанию
	r := gin.Default()

	// Эндпоинт для проверки работоспособности сервиса
	r.GET("/status", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "backend is running",
		})
	})

	// Эндпоинт для приема данных детекции
	r.POST("/api/detections", func(c *gin.Context) {
		var data map[string]interface{}

		// Привязка входящего JSON к переменной
		if err := c.ShouldBindJSON(&data); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid data format"})
			return
		}

		// Вывод уведомления о получении данных
		println("Получен пакет данных от ML-сервиса")

		c.JSON(http.StatusOK, gin.H{
			"message": "data accepted",
		})
	})

	// Запуск сервера на порту 8080
	r.Run(":8080")
}
