package s3

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"time"
	"transfer-api/internal/config"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsConfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

type S3 struct {
	client *s3.Client
}

func NewS3() *S3 {
	cfg := config.LoadConfig()
	aws, err := awsConfig.LoadDefaultConfig(
		context.TODO(),
		awsConfig.WithRegion(cfg.S3Region),
		awsConfig.WithCredentialsProvider(
			credentials.NewStaticCredentialsProvider(
				cfg.AWSAccessKeyID,
				cfg.AWSSecretAccessKey,
				"",
			),
		),
	)
	if err != nil {
		panic("unable to load SDK config, " + err.Error())
	}

	client := s3.NewFromConfig(aws)
	return &S3{client: client}
}

func (s *S3) UploadToS3(data []byte) error {
	cfg := config.LoadConfig()
	key := fmt.Sprintf("go-sdk/%d.json", time.Now().Unix())
	log.Printf("Uploading data to S3 with key: %s\n", key)
	_, err := s.client.PutObject(context.TODO(), &s3.PutObjectInput{
		Bucket: aws.String(cfg.S3BucketName),
		Key:    aws.String(key),
		Body:   bytes.NewReader(data),
	})
	if err != nil {
		log.Printf("Failed to upload to S3: %v\n", err)
	}
	return err
}
