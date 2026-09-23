import { useState } from 'react';
import Dropdown, { Option } from "../../../Dropdown/Dropdown";
import { timeFilterOptions, TimeFilter } from "../../constants";
import useMockApiData from '../../../../hooks/charts/useMockApiData';
import BarChart from '../../primitives/BarChart';
import ChartContainer from '../ChartContainer';
import { EVENT, EVENT_NAME, logEvent } from '../../../../utils/analytics';
import { ChartType } from '../../../../pages/Analytics/ChartType';

const generateMockData = () => {
    const generateRandomValue = (min: number, max: number) => Math.floor(Math.random() * (max - min + 1)) + min;
    const values = [
        ["<1M", generateRandomValue(100000000, 200000000)],
        ["1-5M", generateRandomValue(50000000, 99999999)],
        ["5-10M", generateRandomValue(1000000, 49999999)],
        [">10M", generateRandomValue(0, 999999)]
    ];
    return { values };
};

const TradingVolumeBarChart = ({ fileId }: { fileId: string }) => {
    const [mock, setMock] = useState(generateMockData());
    const [data, loading, error] = useMockApiData(mock);
    const [timeFilter, setTimeFilter] = useState(TimeFilter.LAST_1_DAY);
    const handleTimeFilterSelect = (selectedOption: Option) => {
        setTimeFilter(selectedOption.value as TimeFilter);
        setMock(generateMockData());
        logEvent(EVENT.SELECT, { event_name: EVENT_NAME.ANALYTICS_PAGE.SET_FILTER, filter: "time", chart: ChartType.TRADING_VOLUME_BAR_CHART });
    };
    return (
        <ChartContainer
            title={"Trading Volume"}
            filters={<>
                <Dropdown
                    options={timeFilterOptions}
                    onSelect={handleTimeFilterSelect}
                    selected={timeFilter}
                />
            </>}
            isLoading={!!loading}
            data={data}
            Chart={BarChart}
        />
    );
};

export default TradingVolumeBarChart;