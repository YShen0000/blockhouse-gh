package database

import (
	"context"
	"log"
	"sync"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"transfer-api/internal/config"
)

type MongoDB struct {
	client     *mongo.Client
	database   *mongo.Database
	collection map[string]*mongo.Collection
}

var (
	instance *MongoDB
	once     sync.Once
)

func GetMongoDB() *MongoDB {
	once.Do(func() {
		cfg := config.LoadConfig()

		client, err := mongo.Connect(context.Background(), options.Client().ApplyURI(cfg.MongoURI))
		if err != nil {
			log.Fatalf("Failed to connect MongoDB client: %v", err)
		}

		instance = &MongoDB{
			client:     client,
			database:   client.Database(cfg.MongoDatabase),
			collection: make(map[string]*mongo.Collection),
		}
	})
	return instance
}

func (db *MongoDB) GetCollection(name string) *mongo.Collection {
	if _, exists := db.collection[name]; !exists {
		db.collection[name] = db.database.Collection(name)
	}
	return db.collection[name]
}

func (db *MongoDB) CloseMongoDB() {
	if err := db.client.Disconnect(context.Background()); err != nil {
		log.Printf("Error while disconnecting from MongoDB: %v", err)
	} else {
		log.Println("Disconnected from MongoDB")
	}
}
