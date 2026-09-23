import Dropdown, { Option } from "../../Dropdown/Dropdown";
import Line, { TraderData } from "./Line";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { timeFilterOptions, TimeFilter } from "../constants";
import ChartContainer from "../containers/ChartContainer";
import useMockApiData from "../../../hooks/charts/useMockApiData";
import { EVENT, EVENT_NAME, logEvent } from "../../../utils/analytics";
import { ChartType } from "../../../pages/Analytics/ChartType";

const generateTimeSeries = (length: number) => {
    const now = new Date();
    now.setDate(now.getDate() - 1);
    now.setHours(9, 0, 0, 0);
    const timeSeries = [];
    let lastValue = Math.random() * 1000; 
    for (let i = 0; i < length; i++) {
        const change = (Math.random() - 0.5) * Math.random()*250;
        const value = Math.max(0, lastValue + change);
        timeSeries.push([now.toISOString(), value.toString()]);
        now.setMinutes(now.getMinutes() + 15);
        lastValue = value; 
    }
    return timeSeries as [string, string][];
}
const generateMockData = (): {data: TraderData, unique_cusips: string[]} => {
    const series = [generateTimeSeries(24), generateTimeSeries(24), generateTimeSeries(24)]
    return {
        "data": {
            "TraderX": series[0],
            "TraderY": series[1],
            "TraderZ": series[2],
            "Overall": series[0].map(([time, value], index) => [time, (parseFloat(value) + parseFloat(series[1][index][1]) + parseFloat(series[2][index][1])).toString()]),
        },
        "unique_cusips": [
            "CUSIP0002",
            "CUSIP0001"
        ]
    };
}


const SlippageOverTimeChart: React.FC = () => {
    const [cusip, setCusip] = useState<string>("");
    const [mockData, setMockData] = useState(generateMockData());
    // const [data, setData] = useState<TraderData | null>(null);
    // const [isLoading, setIsLoading] = useState(false);
    const [options, setOptions] = useState<Option[]>([]);
    const [timeFilter, setTimeFilter] = useState<TimeFilter>(
        TimeFilter.LAST_1_DAY
    );

    const [data, loading, error] = useMockApiData(mockData.data)

    useEffect(() => {
        setOptions(
            mockData.unique_cusips.map((c: string) => ({
                value: c,
                name: c,
            }))
        );
    }, []);
    const handleCusipSelect = (selectedOption: Option) => {
        setCusip(selectedOption.name);
        setMockData(generateMockData());
        logEvent(EVENT.SELECT, { event_name: EVENT_NAME.ANALYTICS_PAGE.SET_FILTER, filter: "cusip", chart: ChartType.SLIPPAGE_OVER_TIME_CHART });
    };

    const handleTimeFilterSelect = (selectedOption: any) => {
        setTimeFilter(selectedOption.value);
        setMockData(generateMockData());
        logEvent(EVENT.SELECT, { event_name: EVENT_NAME.ANALYTICS_PAGE.SET_FILTER, filter: "time", chart: ChartType.SLIPPAGE_OVER_TIME_CHART });
    };
    return (
        <ChartContainer
            title="Slippage Over Time"
            filters={<>
                <Dropdown
                    options={options}
                    onSelect={handleCusipSelect}
                    selected={cusip ? cusip : options[0]?.name}
                />

                <Dropdown
                    options={timeFilterOptions}
                    onSelect={handleTimeFilterSelect}
                    selected={timeFilter}
                />
            </>}
            isLoading={!!loading}
            data={data}
            Chart={Line}
        />

    );
};

export default SlippageOverTimeChart;


