import React from 'react';

import { scaleBand, scaleLinear } from 'd3';
import formatNumber from '../../../../utils/formatNumber';
export interface TradingVolumeBarChartData {
    values: Array<[string, number]>;
}
type BarChartProps = {
    data: TradingVolumeBarChartData;
    containerWidth: number;
    containerHeight: number;
};
const BarChart = ({ data, containerWidth = 500, containerHeight = 300 }: BarChartProps) => {
    const { values } = data;

    const margin = {
        top: 20,
        left: 80,
        right: 40,
        bottom: 40
    }
    // Define dimensions and spacing for the chart
    const chartWidth = containerWidth - margin.left - margin.right;
    const chartHeight = containerHeight - margin.top - margin.bottom;
    const TEXT_COLOR = "#7a7a7a";
    const PURPLE_COLOR = "#7962E7";
    const FONT_SIZE = "14px"

    const yDomain = [
        Math.min(...values.map((d) => d[1]), 0),
        Math.max(...values.map((d) => d[1]), 0),
    ];
    const yScale = scaleLinear()
        .domain(yDomain)
        .range([chartHeight, 0])
        .nice();
    const xDomain = [...values.map((d) => d[0])]
    const xScale = scaleBand()
        .domain(xDomain)
        .range([0, chartWidth])
        .padding(0.25);
    const bandwidth = xScale.bandwidth()
    return (
        <svg width={containerWidth} height={containerHeight}>
            <g className="bars" transform={`translate(${margin.left},${margin.top})`}>
                {/* x axis */}
                <line
                    x1={-4}
                    y1={chartHeight}
                    x2={chartWidth}
                    y2={chartHeight}
                    stroke={TEXT_COLOR}
                />
                {/* y axis */}
                <line
                    x1={0}
                    y1={0}
                    x2={0}
                    y2={chartHeight + 4}
                    stroke={TEXT_COLOR}
                />
                {/* horizontal grid and y axis labels */}
                {yScale.ticks(6).map((tickValue, index) => (
                    <g key={index} transform={`translate(0,${yScale(tickValue)})`}>
                        <line x1={-4} x2={chartWidth} stroke={TEXT_COLOR} />
                        <text x={-10} y={5} textAnchor="end" fontSize={FONT_SIZE} fill={TEXT_COLOR}>
                            {formatNumber(tickValue)}
                        </text>
                    </g>
                ))}
                {values.map((value, index) => {
                    const x = xScale(value[0]) || 0;
                    const barHeight = chartHeight - yScale(value[1]);
                    return (
                        <g key={index}>
                            <rect
                                x={x}
                                y={chartHeight - barHeight}
                                width={xScale.bandwidth()}
                                height={barHeight}
                                fill={PURPLE_COLOR}
                            />
                            <text x={x + (bandwidth / 2)} y={chartHeight + 24} textAnchor="middle" fontSize={FONT_SIZE} fill={TEXT_COLOR}>
                                {value[0]}
                            </text>
                            <text x={x + (bandwidth / 2)} y={chartHeight - barHeight - 12} textAnchor="middle" fontSize={FONT_SIZE} fill={TEXT_COLOR}>
                                {formatNumber(value[1])}
                            </text>
                        </g>
                    );
                })}

            </g>
            <g className="axes">

            </g>

        </svg>
    );
};

export default BarChart;