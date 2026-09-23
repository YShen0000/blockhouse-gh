import React, { useState } from 'react';
import useMarketPerformanceRadarChartData from "../../../../hooks/charts/useMarketPerformanceRadarChartData";
import useMockApiData from "../../../../hooks/charts/useMockApiData";
import RadarChart from "../../primitives/RadarChart";
import ChartContainer from '../ChartContainer';
import { TimeFilter, timeFilterOptions } from '../../constants';
import Dropdown, { Option } from '../../../Dropdown/Dropdown';
import { EVENT, EVENT_NAME, logEvent } from '../../../../utils/analytics';
import { ChartType } from '../../../../pages/Analytics/ChartType';

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

const generateRandom = (min: number, max: number) => {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

const generateMockData = (): MarketPerformanceRadarChartData => {
    return {
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
                    "Asset Level ADV": generateRandom(2, 5),
                    "Bid-Ask (width at touch)": generateRandom(2, 5),
                    "Immediacy": generateRandom(2, 5),
                    "Price Resilience": generateRandom(2, 5),
                    "Market Depth": generateRandom(2, 5)
                }
            },
            {
                "label": "Our Benchmark",
                "values": {
                    "Asset Level ADV": generateRandom(2, 5),
                    "Bid-Ask (width at touch)": generateRandom(2, 5),
                    "Immediacy": generateRandom(2, 5),
                    "Price Resilience": generateRandom(2, 5),
                    "Market Depth": generateRandom(2, 5)
                }
            }
        ]
    }
}



const LiquidityPentagonChart = ({ fileId }: { fileId: string }) => {
    const [mock, setMock] = useState(generateMockData());
    const [data, loading, error] = useMockApiData(mock);
    const [timeFilter, setTimeFilter] = useState(TimeFilter.LAST_30_DAYS);
    const handleTimeFilterSelect = (selectedOption: Option) => {
        setTimeFilter(selectedOption.value as TimeFilter);
        setMock(generateMockData());
        logEvent(EVENT.SELECT, { event_name: EVENT_NAME.ANALYTICS_PAGE.SET_FILTER, filter: "time", chart: ChartType.LIQUIDITY_PENTAGON_CHART });
    };


    return (
        <ChartContainer
            title={"Liquidity Pentagon"}
            filters={<>
                <Dropdown
                    options={timeFilterOptions}
                    onSelect={handleTimeFilterSelect}
                    selected={timeFilter}
                />
            </>}
            isLoading={!!loading}
            data={data}
            Chart={RadarChart}
        />
    );
};

export default LiquidityPentagonChart;