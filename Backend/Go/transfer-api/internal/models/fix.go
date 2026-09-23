package models

import "github.com/shopspring/decimal"

type FIXOrder struct {
	OrderID   string          `json:"orderid"`
	Symbol    string          `json:"symbol"`
	Quantity  decimal.Decimal `json:"quantity"`
	Side      string          `json:"side"`
	Price     decimal.Decimal `json:"price"`
}

type FIXResponse struct {
	FixMessage string `json:"fix_message"`
}
