import axios from "axios";
import Chart from "./Chart";
import ChartContainer from "../ChartContainer";
import Dropdown, { Option } from "../../../Dropdown/Dropdown";
import React, { useState, useCallback } from "react";
import { timeFilterOptions, TimeFilter } from "../../constants";

interface Props {
    fileId: string;
}

const PieChartContainer: React.FC<Props> = ({ fileId }) => {
    const [data, setData] = useState(null);
    const [timeFilter, setTimeFilter] = useState<TimeFilter>(
        TimeFilter.LAST_1_DAY
    );
    const [isLoading, setIsLoading] = useState(false);

    const token = localStorage.getItem("token");

    const fetchPieChartData = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await axios.post(
                "/api/analytics/piechart/",
                { fileId, timeFilter },
                {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            if (response.status === 200) {
                setData(response.data);
            } else {
                console.error("Error fetching pie chart data", response);
            }
        } catch (error) {
            console.error("Error fetching pie chart data", error);
        } finally {
            setIsLoading(false);
        }
    }, [fileId, timeFilter]);

    React.useEffect(() => {
        fetchPieChartData();
    }, [fetchPieChartData]);

    const handleTimeFilterSelect = (selectedOption: any) => {
        setTimeFilter(selectedOption.value);
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
            isLoading={isLoading}
            Chart={Chart}
        />
    );
};

export default PieChartContainer;

