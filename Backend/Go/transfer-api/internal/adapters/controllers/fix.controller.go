package controllers

import (
	"transfer-api/internal/adapters/middleware"
	"transfer-api/internal/adapters/services"

	"github.com/gin-gonic/gin"
)

type FIXController struct {
	FIXService       *services.FIXService
	APIKeyMiddleware *middleware.APIKeyMiddleware
}

func NewFIXController(fixService *services.FIXService, apiKeyMiddleware *middleware.APIKeyMiddleware) *FIXController {
	return &FIXController{FIXService: fixService, APIKeyMiddleware: apiKeyMiddleware}
}

func (c *FIXController) SORCredentials(ctx *gin.Context) {
	credentials := c.FIXService.SORCredentials()
	ctx.JSON(200, map[string]interface{}{
		"message": "SOR credentials successfully retrieved",
		"data":    credentials,
	})
}

func (c *FIXController) FIXOrder(ctx *gin.Context) {
	var orders map[string]interface{}

	if err := ctx.ShouldBindJSON(&orders); err != nil {
		ctx.JSON(400, gin.H{"error": err.Error()})
		return
	}

	order_message, err := c.FIXService.FIXOrder(orders)

	if err != nil {
		ctx.JSON(400, gin.H{"error": err.Error()})
		return
	}

	ctx.JSON(200, gin.H{"message": "Orders received", "data": order_message})
}

func (c *FIXController) RegisterRoutes(rg *gin.RouterGroup) {
	routes := rg.Group("/fix")

	routes.GET("/sor-credentials", c.APIKeyMiddleware.CheckAPIKey(), c.SORCredentials)
	routes.POST("/order", c.APIKeyMiddleware.CheckAPIKey(), c.FIXOrder)
}
