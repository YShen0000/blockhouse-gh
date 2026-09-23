package services

import (
	"context"
	"encoding/json"
	"transfer-api/internal/config"
	"transfer-api/internal/infrastructure/database"
	"transfer-api/internal/infrastructure/kafka"
	"transfer-api/internal/models"
	"transfer-api/internal/utils"
)

type TransferDataService struct {
	ctx      context.Context
	DB       *database.MongoDB
	producer *kafka.KafkaProducer
}

func NewTransferDataService(db *database.MongoDB, producer *kafka.KafkaProducer) *TransferDataService {
	return &TransferDataService{ctx: context.Background(), DB: db, producer: producer}
}

func (s *TransferDataService) TransferData() models.Trade {
	trade := utils.GenerateFakeTrade()

	dataToSend, _ := json.Marshal(trade)
	s.producer.SendMessage(string(dataToSend))

	return trade
}

func (s *TransferDataService) S3Credentials() models.S3Credentials {
	cfg := config.LoadConfig()
	credentials := models.S3Credentials{
		AwsAccessKeyId:     cfg.AWSAccessKeyID,
		AwsSecretAccessKey: cfg.AWSSecretAccessKey,
		S3Region:           cfg.S3Region,
	}

	return credentials
}
