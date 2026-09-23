package main

import (
	"github.com/gin-gonic/gin"
	"transfer-api/internal/adapters/controllers"
	"transfer-api/internal/adapters/middleware"
	"transfer-api/internal/adapters/services"
	"transfer-api/internal/config"
	"transfer-api/internal/infrastructure/database"
	"transfer-api/internal/infrastructure/kafka"
	"transfer-api/internal/infrastructure/s3"
)

var (
	server *gin.Engine
	// Infrastructure instances
	db  *database.MongoDB
	cfg *config.Config
	p   *kafka.KafkaProducer

	// Adapter instances
	ac *controllers.APIKeyController
	as *services.APIKeyService
	am *middleware.APIKeyMiddleware

	tdc *controllers.TransferDataController
	tds *services.TransferDataService

	fc *controllers.FIXController
	fs *services.FIXService

	s3Client *s3.S3
)

func init() {
	// Configs
	cfg = config.LoadConfig()
	server = gin.Default()

	// Infrastructure instances
	db = database.GetMongoDB()
	s3Client = s3.NewS3()
	p = kafka.NewKafkaProducer(s3Client, cfg)

	// Adapter instances
	am = middleware.NewAPIKeyMiddleware(db)
	as = services.NewAPIKeyService(db)
	ac = controllers.NewAPIKeyController(as, am)

	tds = services.NewTransferDataService(db, p)
	tdc = controllers.NewTransferDataController(tds, am)

	fs = services.NewFIXService(db)
	fc = controllers.NewFIXController(fs, am)
}

func main() {
	defer db.CloseMongoDB()

	root := server.Group("/")

	ac.RegisterRoutes(root)
	tdc.RegisterRoutes(root)
	fc.RegisterRoutes(root)

	server.Run(":8080")
}
