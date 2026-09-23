package services

import (
	"context"
	"fmt"
	"go.mongodb.org/mongo-driver/bson"
	"time"

	"transfer-api/internal/config"
	"transfer-api/internal/infrastructure/database"
	"transfer-api/internal/models"
	"transfer-api/internal/utils"
)

type FIXService struct {
	ctx context.Context
	DB  *database.MongoDB
}

func NewFIXService(db *database.MongoDB) *FIXService {
	return &FIXService{DB: db, ctx: context.Background()}
}

func (s *FIXService) SORCredentials() models.SORCredentials {
	cfg := config.LoadConfig()
	credentials := models.SORCredentials{
		AwsAccessKeyId:     cfg.AWSAccessKeyID,
		AwsSecretAccessKey: cfg.AWSSecretAccessKey,
		SORRegion:          cfg.S3Region,
		SageMakerEndpoint:  cfg.SOR_ENDPOINT,
	}

	return credentials
}

func (s *FIXService) FIXOrder(order map[string]interface{}) (models.FIXResponse, error) {
	fixOrder, err := utils.CreateFIXOrder(order)

	if err != nil {
		return models.FIXResponse{}, fmt.Errorf("error creating FIX order: %v", err)
	}

	fixMessage, err := utils.CreateFIXMessage(fixOrder)

	if err != nil {
		return models.FIXResponse{}, fmt.Errorf("error creating FIX message: %v", err)
	}

	orderDocument := bson.M{
		"order":       order,
		"fix_message": fixMessage,
		"created_at":  time.Now(),
	}

	collection := s.DB.GetCollection("fix_orders")
	_, dbErr := collection.InsertOne(context.TODO(), orderDocument)

	if dbErr != nil {
		return models.FIXResponse{}, fmt.Errorf("error saving order to database: %v", dbErr)
	}

	// Return the FIX message in the response
	return models.FIXResponse{FixMessage: fixMessage}, nil
}
