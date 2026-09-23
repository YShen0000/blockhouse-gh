package controllers

import (
	"transfer-api/internal/adapters/middleware"
	"transfer-api/internal/adapters/services"

	"github.com/gin-gonic/gin"
)

type TransferDataController struct {
	TransferDataService *services.TransferDataService
	APIKeyMiddleware    *middleware.APIKeyMiddleware
}

func NewTransferDataController(transferDataService *services.TransferDataService, apiKeyMiddleware *middleware.APIKeyMiddleware) *TransferDataController {
	return &TransferDataController{TransferDataService: transferDataService, APIKeyMiddleware: apiKeyMiddleware}
}

func (c *TransferDataController) TransferData(ctx *gin.Context) {
	trade := c.TransferDataService.TransferData()
	ctx.JSON(200, map[string]interface{}{
		"message": "Data successfully sent to Kafka topic",
		"data": map[string]interface{}{
			"symbol":    trade.Symbol,
			"price":     trade.Price,
			"volume":    trade.Volume,
			"timestamp": trade.Timestamp,
		},
	})
}

func (c *TransferDataController) S3Credentials(ctx *gin.Context) {
	credentials := c.TransferDataService.S3Credentials()
	ctx.JSON(200, map[string]interface{}{
		"message": "AWS credentials successfully retrieved",
		"data":    credentials,
	})
}

func (c *TransferDataController) RegisterRoutes(rg *gin.RouterGroup) {
	routes := rg.Group("/transfer-data")

	routes.GET("/trades", c.APIKeyMiddleware.CheckAPIKey(), c.TransferData)
	routes.GET("/s3-credentials", c.APIKeyMiddleware.CheckAPIKey(), c.S3Credentials)
}
