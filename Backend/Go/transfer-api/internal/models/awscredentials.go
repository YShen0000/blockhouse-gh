package models

type S3Credentials struct {
	AwsAccessKeyId     string `json:"aws_access_key_id"`
	AwsSecretAccessKey string `json:"aws_secret_access_key"`
	S3Region           string `json:"s3_region"`
}

type SORCredentials struct {
	AwsAccessKeyId     string `json:"aws_access_key_id"`
	AwsSecretAccessKey string `json:"aws_secret_access_key"`
	SORRegion          string `json:"sor_region"`
	SageMakerEndpoint  string `json:"sagemaker_endpoint"`
}
