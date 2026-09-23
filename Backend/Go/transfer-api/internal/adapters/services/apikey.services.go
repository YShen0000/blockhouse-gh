package services

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"transfer-api/internal/infrastructure/database"
)

type APIKeyService struct {
	ctx context.Context
	DB  *database.MongoDB
}

func NewAPIKeyService(db *database.MongoDB) *APIKeyService {
	return &APIKeyService{DB: db, ctx: context.Background()}
}

func (s *APIKeyService) GenerateAPIKey() string {
	bytes := make([]byte, 16)
	if _, err := rand.Read(bytes); err != nil {
		return ""
	}
	s.DB.GetCollection("apikey").InsertOne(s.ctx, map[string]string{"api_key": hex.EncodeToString(bytes)})
	return hex.EncodeToString(bytes)
}
