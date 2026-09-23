import { useState } from 'react';

interface Metrics {
    name: string;
    max_value: number;
}

interface Values {
    [key: string]: number;
}

interface DataPoint {
    label: string;
    values: Values;
}

export interface MarketPerformanceRadarChartData {
    metrics: Metrics[];
    data: DataPoint[];
}

const useMarketPerformanceRadarChartData = (): MarketPerformanceRadarChartData => {
    const [chartData, _] = useState({
        "metrics": [
            {
                "name": "Asset Level ADV",
                "max_value": 5,
            },
            {
                "name": "Bid-Ask (width at touch)",
                "max_value": 5,
            },
            {
                "name": "Immediacy",
                "max_value": 5,
            },
            {
                "name": "Price Resilience",
                "max_value": 5,
            },
            {
                "name": "Market Depth",
                "max_value": 5,
            }
        ],
        "data": [
            {
                "label": "Reference",
                "values": {
                    "Asset Level ADV": 3,
                    "Bid-Ask (width at touch)": 2,
                    "Immediacy": 3,
                    "Price Resilience": 4,
                    "Market Depth": 3
                }
            },
            {
                "label": "Our Benchmark",
                "values": {
                    "Asset Level ADV": 4,
                    "Bid-Ask (width at touch)": 3,
                    "Immediacy": 4,
                    "Price Resilience": 3,
                    "Market Depth": 4
                }
            }
        ]
    });
    return chartData;
};

export default useMarketPerformanceRadarChartData;