package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/IBM/sarama"
)

const (
	polygonAPIKey = "r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc" // Your Polygon API key
)

// AggregatesResponse represents the response structure from Polygon API
type AggregatesResponse struct {
	Results []Aggregate `json:"results"`
}

// Aggregate represents the OHLCV (Open, High, Low, Close, Volume) data for a specific date
type Aggregate struct {
	Timestamp int64   `json:"t"` // Timestamp in Unix format
	Open      float64 `json:"o"`
	High      float64 `json:"h"`
	Low       float64 `json:"l"`
	Close     float64 `json:"c"`
	Volume    float64 `json:"v"`
}

// Quote represents the bid and ask prices and sizes
type Quote struct {
	Timestamp int64   `json:"t"` // Timestamp in Unix format
	BidPrice  float64 `json:"bp"`
	AskPrice  float64 `json:"ap"`
	BidSize   int     `json:"bs"`
	AskSize   int     `json:"as"`
}

// Fetch historical trading data for a given symbol and date range
func fetchHistoricalData(symbol, startDate, endDate string) ([]Aggregate, error) {
	url := fmt.Sprintf("https://api.polygon.io/v2/aggs/ticker/%s/range/1/day/%s/%s?apiKey=%s",
		symbol, startDate, endDate, polygonAPIKey)

	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to fetch data: %s", resp.Status)
	}

	var data AggregatesResponse
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}

	return data.Results, nil
}

// Fetch quote data for a given symbol and date range
func fetchQuotes(symbol, startDate, endDate string) ([]Quote, error) {
	url := fmt.Sprintf("https://api.polygon.io/v3/quotes/%s?startDate=%s&endDate=%s&apiKey=%s",
		symbol, startDate, endDate, polygonAPIKey)

	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to fetch data: %s", resp.Status)
	}

	var data struct {
		Quotes []Quote `json:"quotes"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}

	return data.Quotes, nil
}

// Aggregate quotes to minute-wise format
func aggregateQuotes(quotes []Quote) map[int64]Quote {
	aggregatedQuotes := make(map[int64]Quote)

	for _, quote := range quotes {
		minute := quote.Timestamp / 60000 // convert milliseconds to minute timestamp

		if existingQuote, exists := aggregatedQuotes[minute]; exists {
			// Update the existing quote with new data
			existingQuote.BidSize += quote.BidSize
			existingQuote.AskSize += quote.AskSize
			aggregatedQuotes[minute] = existingQuote
		} else {
			// Initialize a new aggregated quote
			aggregatedQuotes[minute] = quote
		}
	}

	return aggregatedQuotes
}

func main() {
	// Configure the Kafka producer
	config := sarama.NewConfig()
	config.Producer.Return.Successes = true
	producer, err := sarama.NewSyncProducer([]string{"localhost:9092"}, config)
	if err != nil {
		log.Fatalf("Failed to create producer: %v", err)
	}
	defer producer.Close()

	fmt.Println("Sending historical trading data...")

	// Define the date range (two years from today)
	startDate := time.Now().AddDate(-2, 0, 0).Format("2006-01-02")
	endDate := time.Now().Format("2006-01-02")

	// List of stock symbols to fetch data for
	symbols := []string{"AAPL", "JNJ", "JPM", "XOM", "PG", "KO", "BA", "V", "NEE", "UNP", "ZBRA", "LULU", "ENPH", "GRMN", "CHGG", "EMN", "ALLE", "DRI", "MOH", "LII", "FNKO", "NSTG", "CAL", "LOVE", "VTSI", "HLIT", "PBPB", "XCUR", "GSM", "HCI"}

	// Fetch and send data for each symbol
	for _, symbol := range symbols {
		historicalData, err := fetchHistoricalData(symbol, startDate, endDate)
		if err != nil {
			log.Printf("Error fetching data for %s: %v", symbol, err)
			continue
		}

		if len(historicalData) == 0 {
			log.Printf("No historical data found for %s", symbol)
			continue
		}

		// Fetch and aggregate quotes here
		quotes, err := fetchQuotes(symbol, startDate, endDate)
		if err != nil {
			log.Printf("Error fetching quotes for %s: %v", symbol, err)
			continue
		}
		aggregatedQuotes := aggregateQuotes(quotes)

		for _, data := range historicalData {
			// Get the aggregated quote for the current minute
			quote, exists := aggregatedQuotes[data.Timestamp/1000]
			if !exists {
				// If no quote data exists for the current minute, initialize with default values
				quote = Quote{
					BidPrice: 0,
					AskPrice: 0,
					BidSize:  0,
					AskSize:  0,
				}
			}

			// Format the message as a JSON string including aggregated quotes
			trade := fmt.Sprintf(`{"symbol": "%s", "timestamp": "%s", "open": %.2f, "high": %.2f, "low": %.2f, "close": %.2f, "volume": %.2f, "bid_price": %.2f, "ask_price": %.2f, "bid_size": %d, "ask_size": %d}`,
				symbol, time.Unix(data.Timestamp/1000, 0).Format(time.RFC3339), data.Open, data.High, data.Low, data.Close, data.Volume, quote.BidPrice, quote.AskPrice, quote.BidSize, quote.AskSize)

			// Prepare the Kafka message
			msg := &sarama.ProducerMessage{
				Topic: "historical-data",
				Value: sarama.StringEncoder(trade),
			}

			// Send the message to Kafka
			partition, offset, err := producer.SendMessage(msg)
			if err != nil {
				log.Printf("Failed to send message: %v", err)
			} else {
				fmt.Printf("Message sent to partition %d at offset %d: %s\n", partition, offset, trade)
			}
		}
	}

	fmt.Println("Finished sending historical trading data.")
}
