import { line, scaleLinear } from 'd3';
import React from 'react';
import formatNumber from '../../../../utils/formatNumber';

interface SpreadChartProps {
    containerWidth: number;
    containerHeight: number;
    data: BidAskChartData; // Assuming data is an array for simplicity, adjust according to actual data structure
}

type BidAskChartData = {
    bid_ask_chart: {
        benchmarks: {
            "Last Price": number;
            "Bid": number;
            "Ask": number;
        };
        notional_values_buy: number[][];
        notional_values_sell: number[][];
    };
};

const SpreadChart: React.FC<SpreadChartProps> = ({ data, containerWidth = 500, containerHeight = 300 }): JSX.Element => {
    const STROKE_COLOR = "#7a7a7a";
    const COLORS = ["#00B8B9", "#7962E7", "#3DBEF6"]; // add more as required
    const margin = { top: 50, bottom: 80, right: 50, left: 80 };
    const chartHeight = containerHeight - margin.top - margin.bottom;
    const chartWidth = containerWidth - margin.left - margin.right;
    const bidAskMarketPrices = [...data.bid_ask_chart.notional_values_buy.map((d) => d[0]), ...data.bid_ask_chart.notional_values_sell.map((d) => d[0])]
    const bidAskNotionalPrices = [...data.bid_ask_chart.notional_values_buy.map((d) => d[1]), ...data.bid_ask_chart.notional_values_sell.map((d) => d[1])]
    const maxBidAskMarketPrice = Math.max(...bidAskMarketPrices)
    const minBidAskMarketPrice = Math.min(...bidAskMarketPrices)
    const maxBidAskNotionalPrice = Math.max(...bidAskNotionalPrices)
    const minBidAskNotionalPrice = Math.min(...bidAskNotionalPrices)

    const xScale = scaleLinear()
        .domain([minBidAskMarketPrice, maxBidAskMarketPrice])
        .range([0, chartWidth]);

    const yScale = scaleLinear()
        .domain([minBidAskNotionalPrice, maxBidAskNotionalPrice])
        .range([chartHeight, 0]);

    // const lineGenerator = line()
    //     .x(d => xScale(d[0]))
    //     .y(d => yScale(d[1]))
    return (
        <svg width={containerWidth} height={containerHeight}>
            <g transform={`translate(${margin.left}, ${margin.top})`}>
                {/* <path d={lineGenerator(data.bid_ask_chart.notional_values_buy as [number, number][])!} fill={'transparent'} stroke='white' />
                <path d={lineGenerator(data.bid_ask_chart.notional_values_sell as [number, number][])!} fill={'transparent'} stroke='white' /> */}
                {data.bid_ask_chart.notional_values_buy.map((d, i) => (
                    <circle
                        key={`buy-${i}`}
                        cx={xScale(d[0])}
                        cy={yScale(d[1])}
                        r={3}
                        fill={COLORS[0]}
                    />
                ))}
                {data.bid_ask_chart.notional_values_sell.map((d, i) => (
                    <circle
                        key={`sell-${i}`}
                        cx={xScale(d[0])}
                        cy={yScale(d[1])}
                        r={3}
                        fill={COLORS[1]}
                    />
                ))}
                <g className="y-axis">
                    <line
                        x1={-12}
                        y1={0}
                        x2={-12}
                        y2={chartHeight}
                        stroke={STROKE_COLOR}
                    />
                    {yScale.ticks(5).map((tickValue, index) => (
                        <g key={index} transform={`translate(0,${yScale(tickValue)})`}>
                            <line x1={-16} x2={-12} stroke={STROKE_COLOR} />
                            <text x={-20} y={5} textAnchor="end" fill={STROKE_COLOR}>
                                {formatNumber(tickValue)}
                            </text>
                        </g>
                    ))}
                </g>
                <g className="x-axis">
                    <line
                        x1={-12}
                        y1={chartHeight}
                        x2={chartWidth + 12}
                        y2={chartHeight}
                        stroke={STROKE_COLOR}
                    />
                </g>
                <g className="x-axis-labels">
                    {Object.entries(data.bid_ask_chart.benchmarks).map((point, index) => (
                        <>
                            <line
                                key={`benchmark-line-${index}`}
                                x1={xScale(point[1])}
                                x2={xScale(point[1])}
                                y1={0}
                                y2={chartHeight + index * 20}
                                stroke={STROKE_COLOR}
                                strokeDasharray="5,5"
                            />
                            <text
                                key={`benchmark-${index}`}
                                x={xScale(point[1])}
                                y={chartHeight + index * 20 + 20}
                                textAnchor="middle"
                                fill={STROKE_COLOR}
                            >
                                {point[0]}
                            </text>
                        </>
                    ))}
                </g>
            </g>
        </svg>
    );
};

export default SpreadChart;
