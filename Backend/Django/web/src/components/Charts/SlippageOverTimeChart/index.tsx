import axios from "axios";
import Dropdown, { Option } from "../../Dropdown/Dropdown";
import Line, { TraderData } from "./Line";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { timeFilterOptions, TimeFilter } from "../constants";
import useContainerDimensions from "../../../hooks/useContainerDimensions";
import ChartContainer from "../containers/ChartContainer";

interface Props {
    fileId: string;
}

const SlippageOverTimeChart: React.FC<Props> = ({ fileId }) => {
    const [cusip, setCusip] = useState<string>("");
    const [data, setData] = useState<TraderData | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [options, setOptions] = useState<Option[]>([]);
    const [timeFilter, setTimeFilter] = useState<TimeFilter>(
        TimeFilter.LAST_1_DAY
    );

    const token = localStorage.getItem("token");

    const fetchChartData = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await axios.post(
                "/api/analytics/execution_over_time/",
                { fileId, cusip, timeFilter },
                {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            if (response.status === 200) {
                setData(response.data.data);
                setOptions(
                    response.data.unique_cusips.map((c: string) => ({
                        value: c,
                        name: c,
                    }))
                );
            } else {
                console.error("Error fetching chart data", response);
            }
        } catch (error) {
            console.error("Error fetching chart data", error);
        } finally {
            setIsLoading(false);
        }
    }, [fileId, cusip, timeFilter]);

    useEffect(() => {
        fetchChartData();
    }, [fetchChartData]);

    const handleCusipSelect = (selectedOption: Option) => {
        setCusip(selectedOption.name);
    };

    const handleTimeFilterSelect = (selectedOption: any) => {
        setTimeFilter(selectedOption.value);
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
            isLoading={isLoading}
            data={data}
            Chart={Line}
        />

    );
};

export default SlippageOverTimeChart;
