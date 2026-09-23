package utils

import (
	"math/rand"
	"time"
	"transfer-api/internal/models"
)

// GenerateFakeTrade creates a simulated trade record.
func GenerateFakeTrade() models.Trade {
	symbols := []string{"AAPL", "GOOGL", "AMZN", "MSFT", "TSLA"}
	symbol := symbols[rand.Intn(len(symbols))]
	price := 100 + rand.Float64()*(1500-100)
	volume := rand.Intn(1000) + 1
	timestamp := time.Now().Format(time.RFC3339)

	return models.Trade{
		Symbol:    symbol,
		Price:     price,
		Volume:    volume,
		Timestamp: timestamp,
	}
}
