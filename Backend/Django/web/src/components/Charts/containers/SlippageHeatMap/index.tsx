import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import Dropdown, { Option } from "../../../Dropdown/Dropdown";
import Map from "./Map";
import { timeFilterOptions, TimeFilter } from "../../constants";
import ChartContainer from "../ChartContainer";
import useMockApiData from "../../../../hooks/charts/useMockApiData";
import { EVENT, EVENT_NAME, logEvent } from "../../../../utils/analytics";
import { ChartType } from "../../../../pages/Analytics/ChartType";

interface HeatMapProps {
    fileId: string;
}

interface HeatMapData {
    markouts: any;
    intervals: number[];
    traders: string[];
    unique_cusips: string[];
}

const generateMockData = (cusip?: string) => {
    const generateRandomMarkout = () => (Math.random() - 0.5) * 10;
    const traders = ["TraderA", "TraderB", "TraderC"];
    const intervals = [1, 30, 60, 90];
    const unique_cusips = ["CUSIP0001", "CUSIP0002"];
    
    const markouts = traders.map(() => intervals.map(() => generateRandomMarkout()));

    return {
        cusip: cusip || unique_cusips[Math.floor(Math.random() * unique_cusips.length)],
        markouts,
        traders,
        intervals,
        unique_cusips,
    };
};
const HeatMap: React.FC<HeatMapProps> = ({ fileId }) => {
    const [cusip, setCusip] = useState<string>("");
    const [timeFilter, setTimeFilter] = useState<TimeFilter>(
        TimeFilter.LAST_1_DAY
    );
    const [options, setOptions] = React.useState<Option[]>([]);

    const [mock, setMock] = useState(generateMockData());
    const [heatmapData, isLoading, error] = useMockApiData(mock);
    useEffect(() => {
        if (!heatmapData) return;
        if (typeof heatmapData === 'boolean' || heatmapData instanceof Error) return;
        setOptions(
            (heatmapData as HeatMapData).unique_cusips.map((c: string) => ({
                value: c,
                name: c,
            }))
        );
    }, [heatmapData]);

    const handleCusipSelect = (selectedOption: Option) => {
        setCusip(selectedOption.name);
        setMock(generateMockData(selectedOption.name));
        logEvent(EVENT.SELECT, { event_name: EVENT_NAME.ANALYTICS_PAGE.SET_FILTER, filter: "cusip", chart: ChartType.SLIPPAGE_HEAT_MAP });
    };

    const handleTimeFilterSelect = (selectedOption: any) => {
        setTimeFilter(selectedOption.value);
        setMock(generateMockData());
        logEvent(EVENT.SELECT, { event_name: EVENT_NAME.ANALYTICS_PAGE.SET_FILTER, filter: "time", chart: ChartType.SLIPPAGE_HEAT_MAP });
    };

    return (
        <ChartContainer
            title="Slippage Heatmap"
            filters={
                <>
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
            isLoading={isLoading}
            data={heatmapData}
            Chart={Map}
        />
    );
};

export default HeatMap;
