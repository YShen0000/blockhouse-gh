import React, { useState } from 'react';
import ChartContainer from '../ChartContainer';
import { Benchmark, BenchmarkFilterOptions, TimeFilterLast5Days, timeFilterOptionsLast5Days } from '../../constants';
import Dropdown from '../../../Dropdown/Dropdown';
import SpreadChart from '../../primitives/SpreadChart';
import { EVENT, EVENT_NAME, logEvent } from '../../../../utils/analytics';
import { ChartType } from '../../../../pages/Analytics/ChartType';

const generateMockData = (benchmark) => {
    const benchmarkValue = 150
    return {
        bid_ask_chart: {
            benchmarks: {
                [BenchmarkFilterOptions.find(option => option.value === benchmark)?.name || "Last Price"]: benchmarkValue,
                "Bid": benchmarkValue - Math.random() * 0.015,
                "Ask": benchmarkValue + Math.random() * 0.015
            },
            notional_values_buy: [...Array(100).fill(0).map((_, i) => {
                const skewTowardsBid = benchmarkValue - Math.random() * 0.03 + Math.random() * 0.015;
                return [skewTowardsBid, Math.random() * 1000000 * Math.random()];
            })],
            notional_values_sell: [...Array(100).fill(0).map((_, i) => {
                const skewTowardsAsk = benchmarkValue + Math.random() * 0.03 - Math.random() * 0.015;
                return [skewTowardsAsk, Math.random() * 1000000 * Math.random()];
            })]
        }
    }
}

const SegmentedBidAskSpread = ({ fileId }) => {
    // TODO extract out hook
    const useTimeFilter = (initialValue) => {
        const [timeFilter, setTimeFilter] = useState(initialValue);
        const handleTimeFilterSelect = (selectedOption) => {
            setTimeFilter(selectedOption.value);
            logEvent(EVENT.SELECT, { event_name: EVENT_NAME.ANALYTICS_PAGE.SET_FILTER, filter: "time", chart: ChartType.SEGMENTED_BID_ASK_SPREAD_CHART });
        };
        return [timeFilter, handleTimeFilterSelect];
    };

    const [timeFilter, handleTimeFilterSelect] = useTimeFilter(TimeFilterLast5Days.LAST_1_DAY);
    const useBenchmark = (initialValue) => {
        const [benchmark, setBenchmark] = useState(initialValue);
        const handleBenchmarkSelect = (selectedOption) => {
            setBenchmark(selectedOption.value);
            logEvent(EVENT.SELECT, { event_name: EVENT_NAME.ANALYTICS_PAGE.SET_FILTER, filter: "benchmark", chart: ChartType.SEGMENTED_BID_ASK_SPREAD_CHART });
        };
        return [benchmark, handleBenchmarkSelect];
    };

    const [benchmark, handleBenchmarkSelect] = useBenchmark(Benchmark.LAST_PRICE);
    const chartData = generateMockData(benchmark)
    return (
        <ChartContainer
            title={"Segmented Bid Ask Spread"}
            filters={<>
                <Dropdown
                    options={timeFilterOptionsLast5Days}
                    onSelect={handleTimeFilterSelect}
                    selected={timeFilter}
                />
                <Dropdown
                    options={BenchmarkFilterOptions}
                    onSelect={handleBenchmarkSelect}
                    selected={benchmark}
                />
            </>}
            isLoading={false}
            data={chartData}
            Chart={SpreadChart}
        />
    );
};

export default SegmentedBidAskSpread