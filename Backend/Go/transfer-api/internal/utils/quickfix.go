package utils

import (
	"fmt"
	"time"
	"transfer-api/internal/models"

	"github.com/quickfixgo/enum"
	"github.com/quickfixgo/field"
	"github.com/quickfixgo/fix42/newordersingle"
	"github.com/shopspring/decimal"
)

func CreateFIXMessage(req models.FIXOrder) (string, error) {
	order := newordersingle.New(
		field.NewClOrdID(req.OrderID),
		field.NewHandlInst("1"),
		field.NewSymbol(req.Symbol),
		field.NewSide(sideToFIX(req.Side)),
		field.NewTransactTime(time.Now()),
		field.NewOrdType(orderTypeToFIX("limit")),
	)
	order.Set(field.NewOrderQty(req.Quantity, 0))

	msg := order.ToMessage()

	return msg.String(), nil
}

func sideToFIX(side string) enum.Side {
	if side == "buy" {
		return enum.Side_BUY
	}
	return enum.Side_SELL
}

func orderTypeToFIX(orderType string) enum.OrdType {
	if orderType == "limit" {
		return enum.OrdType_LIMIT
	}
	return enum.OrdType_MARKET
}

func CreateFIXOrder(order map[string]interface{}) (models.FIXOrder, error) {
	// Validate the required fields to create a FIX order
	orderID, ok := order["orderid"].(string)
	if !ok || orderID == "" {
		return models.FIXOrder{}, fmt.Errorf("invalid or missing 'orderid'")
	}

	symbol, ok := order["symbol"].(string)
	if !ok || symbol == "" {
		return models.FIXOrder{}, fmt.Errorf("invalid or missing 'symbol'")
	}

	side, ok := order["side"].(string)
	if !ok || side == "" {
		return models.FIXOrder{}, fmt.Errorf("invalid or missing 'side'")
	}

	var quantity float64
	if val, exists := order["quantity"]; exists {
		if q, isFloat := val.(float64); isFloat {
			quantity = q
		} else {
			return models.FIXOrder{}, fmt.Errorf("invalid 'quantity'; must be a number")
		}
	} else {
		return models.FIXOrder{}, fmt.Errorf("missing 'quantity'")
	}

	var price float64
	if val, exists := order["price"]; exists {
		if p, isFloat := val.(float64); isFloat {
			price = p
		} else {
			return models.FIXOrder{}, fmt.Errorf("invalid 'price'; must be a number")
		}
	} else {
		return models.FIXOrder{}, fmt.Errorf("missing 'price'")
	}

	// Create a FIXOrder object from the request
	fixOrder := models.FIXOrder{
		OrderID:  orderID,
		Symbol:   symbol,
		Quantity: decimal.NewFromFloat(quantity),
		Side:     side,
		Price:    decimal.NewFromFloat(price),
	}

	return fixOrder, nil

}
