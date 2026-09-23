package controllers

import (
	"github.com/gin-gonic/gin"
	"transfer-api/internal/adapters/middleware"
	"transfer-api/internal/adapters/services"
)

type APIKeyController struct {
	APIKeyService    *services.APIKeyService
	APIKeyMiddleware *middleware.APIKeyMiddleware
}

func NewAPIKeyController(apiKeyService *services.APIKeyService, apiKeyMiddleware *middleware.APIKeyMiddleware) *APIKeyController {
	return &APIKeyController{APIKeyService: apiKeyService, APIKeyMiddleware: apiKeyMiddleware}
}

func (c *APIKeyController) GenerateAPIKey(ctx *gin.Context) {
	apiKey := c.APIKeyService.GenerateAPIKey()
	ctx.JSON(200, gin.H{"api_key": apiKey})
}

func (c *APIKeyController) CheckAPIKey(ctx *gin.Context) {
	ctx.JSON(200, gin.H{"message": "API key is valid"})
}

func (c *APIKeyController) RegisterRoutes(rg *gin.RouterGroup) {
	routes := rg.Group("/api-key")

	routes.GET("/validate", c.APIKeyMiddleware.CheckAPIKey(), c.CheckAPIKey)
	routes.POST("/generate", c.GenerateAPIKey)
}
