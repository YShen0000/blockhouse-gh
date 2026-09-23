package config

import (
	"log"
	"os"
	"sync"

	"github.com/joho/godotenv"
)

type Config struct {
	// Kafka Config
	KafkaBroker   string
	KafkaTopic    string
	KafkaUsername string
	KafkaPassword string

	// S3 Config
	S3BucketName       string
	S3Region           string
	AWSAccessKeyID     string
	AWSSecretAccessKey string
	SOR_ENDPOINT       string

	// MongoDB Config
	MongoURI      string
	MongoDatabase string
}

var (
	instance *Config
	once     sync.Once
)

func LoadConfig() *Config {
	once.Do(func() {
		if err := godotenv.Load(); err != nil {
			log.Println("No .env file found. Using system environment variables.")
		}

		instance = &Config{
			// Kafka
			KafkaBroker:   getEnv("KAFKA_BROKER", "localhost:9092"),
			KafkaTopic:    getEnv("KAFKA_TOPIC", "default_topic"),
			KafkaUsername: getEnv("KAFKA_USERNAME", ""),
			KafkaPassword: getEnv("KAFKA_PASSWORD", ""),

			// S3
			S3BucketName:       getEnv("S3_BUCKET_NAME", ""),
			S3Region:           getEnv("S3_REGION", ""),
			AWSAccessKeyID:     getEnv("AWS_ACCESS_KEY_ID", ""),
			AWSSecretAccessKey: getEnv("AWS_SECRET_ACCESS_KEY", ""),
			SOR_ENDPOINT:       getEnv("SOR_ENDPOINT", ""),

			// MongoDB
			MongoURI:      getEnv("MONGODB_URI", "mongodb://localhost:27017"),
			MongoDatabase: getEnv("MONGODB_DATABASE", "Golang-SDK"),
		}
	})
	return instance
}

func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}
