package kafka

import (
	"log"

	"github.com/IBM/sarama"
	"transfer-api/internal/config"
	"transfer-api/internal/infrastructure/s3"
)

type KafkaConsumer struct {
	producer sarama.SyncProducer
	s3Client *s3.S3
	cfg      *config.Config
}

func NewKafkaConsumer(S3Client *s3.S3, cfg *config.Config) *KafkaConsumer {
	kafkaConfig := sarama.NewConfig()
	kafkaConfig.Producer.Return.Successes = true

	var err error
	producer, err := sarama.NewSyncProducer([]string{cfg.KafkaBroker}, kafkaConfig)
	if err != nil {
		log.Fatalf("Failed to start Kafka producer: %v", err)
		return nil
	}

	return &KafkaConsumer{producer: producer, s3Client: S3Client, cfg: cfg}
}

// ListenAndUpload listens for Kafka messages and uploads them to S3
func (c *KafkaConsumer) ListenAndUpload(brokers []string) {
	consumer, err := sarama.NewConsumer(brokers, nil)
	if err != nil {
		log.Fatalf("Failed to start consumer: %v", err)
	}
	defer consumer.Close()

	partitionConsumer, err := consumer.ConsumePartition(c.cfg.KafkaTopic, 0, sarama.OffsetNewest)
	if err != nil {
		log.Fatalf("Failed to start partition consumer: %v", err)
	}
	defer partitionConsumer.Close()

	for msg := range partitionConsumer.Messages() {
		log.Printf("Received message: %s", string(msg.Value))
		if err := c.s3Client.UploadToS3(msg.Value); err != nil {
			log.Printf("Failed to upload to S3: %v", err)
		} else {
			log.Println("Data successfully stored in S3.")
		}
	}
}
