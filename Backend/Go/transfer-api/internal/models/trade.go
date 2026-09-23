package models

type Trade struct {
	Symbol    string  `json:"symbol"`
	Price     float64 `json:"price"`
	Volume    int     `json:"volume"`
	Timestamp string  `json:"timestamp"`
}
