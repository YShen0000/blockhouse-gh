package middleware

import (
	"github.com/gin-gonic/gin"
	"transfer-api/internal/infrastructure/database"
)

type APIKeyMiddleware struct {
	DB *database.MongoDB
}

func NewAPIKeyMiddleware(db *database.MongoDB) *APIKeyMiddleware {
	return &APIKeyMiddleware{DB: db}
}

func (m *APIKeyMiddleware) CheckAPIKey() gin.HandlerFunc {
	return func(c *gin.Context) {
		apiKey := c.GetHeader("X-API-Key")
		if apiKey == "" {
			c.JSON(401, gin.H{"error": "API key is required"})
			c.Abort()
			return
		}

		client := m.DB.GetCollection("apikey").FindOne(c, map[string]string{"api_key": apiKey})

		if client.Err() != nil {
			c.JSON(401, gin.H{"error": "Invalid API key"})
			c.Abort()
			return
		}

		c.Set("client", client)
		c.Next()
	}
}
