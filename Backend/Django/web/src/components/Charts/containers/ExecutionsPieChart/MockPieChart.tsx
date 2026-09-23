import axios from "axios";
import Chart from "./Chart";
import ChartContainer from "../ChartContainer";
import Dropdown, { Option } from "../../../Dropdown/Dropdown";
import React, { useState, useCallback, useEffect } from "react";
import { timeFilterOptions, TimeFilter } from "../../constants";
import useMockApiData from "../../../../hooks/charts/useMockApiData";
import { EVENT, EVENT_NAME, logEvent } from "../../../../utils/analytics";
import { ChartType } from "../../../../pages/Analytics/ChartType";


function generateRandomData() {
    const generateRandomPercentage = () => Math.random() * 100;
    const sum = (arr: number[]) => arr.reduce((acc, val) => acc + val, 0);
    const generateRandomVolumeByEntity = (entities: string[]) => {
        const percentages = entities.map(() => generateRandomPercentage());
        const total = sum(percentages);
        return entities.reduce((acc, entity, index) => {
            acc[entity as string] = (percentages[index] / total) * 100;
            return acc;
        }, {} as Record<string, number>);
    };

    const traders = ["TraderX", "TraderY", "TraderZ"];
    const counterparties = ["CounterpartyA", "CounterpartyB", "CounterpartyC"];

    const agg_comp = Math.floor(Math.random() * 100000000000);
    const agg_noncomp = Math.floor(Math.random() * 100000000000);
    const total_notional = agg_comp + agg_noncomp;

    return {
        "agg_comp": agg_comp,
        "agg_noncomp": agg_noncomp,
        "total_notional": total_notional,
        "comp_volume_by_trader_percentage": generateRandomVolumeByEntity(traders),
        "noncomp_volume_by_trader_percentage": generateRandomVolumeByEntity(traders),
        "comp_volume_by_counterparty_percentage": generateRandomVolumeByEntity(counterparties),
        "noncomp_volume_by_counterparty_percentage": generateRandomVolumeByEntity(counterparties)
    };
}


const PieChartContainer: React.FC = () => {
    const [timeFilter, setTimeFilter] = useState<TimeFilter>(
        TimeFilter.LAST_1_DAY
    );
    const [mockData, setMockData] = useState(generateRandomData());
    const [data, loading, error] = useMockApiData(mockData);

    const handleTimeFilterSelect = (selectedOption: any) => {
        setTimeFilter(selectedOption.value);
        setMockData(generateRandomData());
        logEvent(EVENT.SELECT, { event_name: EVENT_NAME.ANALYTICS_PAGE.SET_FILTER, filter: "time", chart: ChartType.EXECUTIONS_PIE_CHART });
    };

    return (
        <ChartContainer
            title="Executions"
            filters={
                <Dropdown
                    options={timeFilterOptions}
                    onSelect={handleTimeFilterSelect}
                    selected={timeFilter}
                />
            }
            data={data}
            isLoading={!!loading}
            Chart={Chart}
        />
    );
};

export default PieChartContainer;

