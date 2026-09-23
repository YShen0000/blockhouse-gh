package kafka

import (
	"crypto/tls"
	"fmt"
	"github.com/IBM/sarama"
	"github.com/xdg/scram"
	"log"

	"transfer-api/internal/config"
	"transfer-api/internal/infrastructure/s3"
	"transfer-api/internal/utils"
)

type KafkaProducer struct {
	producer sarama.SyncProducer
	s3Client *s3.S3
	cfg      *config.Config
}

func NewKafkaProducer(S3Client *s3.S3, cfg *config.Config) *KafkaProducer {
	config := sarama.NewConfig()

	// Producer config
	config.Producer.RequiredAcks = sarama.WaitForAll
	config.Producer.Retry.Max = 5
	config.Producer.Return.Successes = true

	// SASL config
	config.Net.SASL.Enable = true
	config.Net.SASL.User = cfg.KafkaUsername
	config.Net.SASL.Password = cfg.KafkaPassword
	config.Net.SASL.Handshake = true
	config.Net.SASL.Mechanism = sarama.SASLTypeSCRAMSHA256

	// TLS Config
	config.Net.TLS.Enable = true
	config.Net.TLS.Config = &tls.Config{
		InsecureSkipVerify: true,
	}

	// Provide the SCRAM client generator for SHA-256
	config.Net.SASL.SCRAMClientGeneratorFunc = func() sarama.SCRAMClient {
		return &utils.XDGSCRAMClient{HashGeneratorFcn: scram.SHA256}
	}

	producer, err := sarama.NewSyncProducer([]string{cfg.KafkaBroker}, config)
	if err != nil {
		log.Fatalf("Failed to create Kafka producer: %v", err)
	}

	return &KafkaProducer{producer: producer, s3Client: S3Client, cfg: cfg}
}

func (k *KafkaProducer) SendMessage(data string) error {
	msg := &sarama.ProducerMessage{
		Topic: k.cfg.KafkaTopic,
		Value: sarama.StringEncoder(data),
	}

	partition, offset, err := k.producer.SendMessage(msg)
	if err != nil {
		return fmt.Errorf("failed to send message to Kafka: %v", err)
	}
	log.Printf("Message sent to Kafka on partition %d at offset %d: %s\n", partition, offset, data)

	// Upload data to S3
	if err := k.s3Client.UploadToS3([]byte(data)); err != nil {
		log.Printf("Failed to upload to S3: %v", err)
	} else {
		log.Println("Data successfully stored in S3.")
	}
	return nil
}

func (k *KafkaProducer) Close() {
	if err := k.producer.Close(); err != nil {
		log.Printf("Failed to close Kafka producer: %v", err)
	}
}
