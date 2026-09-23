import React from 'react';
import { scaleLinear } from 'd3';
import { MarketPerformanceRadarChartData } from "../../../../hooks/charts/useMarketPerformanceRadarChartData";

type RadarChartProps = {
    data: MarketPerformanceRadarChartData;
    containerWidth: number;
    containerHeight: number;
};

const DEFAULT_LABEL = {
    MIN: "Not liquid",
    MAX: "Very liquid"
}

const RadarChart = ({ data: { metrics, data }, containerWidth = 500, containerHeight = 300 }: RadarChartProps) => {
    const legendHeight = 40;
    const size = Math.min(containerHeight - legendHeight - 50, containerWidth - 310);
    const radius = size / 2; // The radius of the radar chart
    const chartCenterX = containerWidth / 2;
    const chartCenterY = (containerHeight - legendHeight) / 2;
    const STROKE_COLOR = "#7a7a7a";
    const GRID_STROKE_COLOR = "#5a5a5a";
    const GRID_FONT_SIZE = "10px";
    const FONT_SIZE = "14px";
    const COLORS = ["#00B8B9", "#7962E7", "#3DBEF6"]; // add more as required

    const calculatePoint = (value: number, index: number, total: number, offset = 0): { x: number, y: number } => {
        const angle = ((Math.PI * 2) / total) * index - Math.PI / 2;
        const x = chartCenterX + ((radius + offset) * value) / metrics.length * Math.cos(angle);
        const y = chartCenterY + ((radius + offset) * value) / metrics.length * Math.sin(angle);
        return { x, y };
    };

    // Map the metrics to SVG paths for the axes and labels
    const axesAndLabels = metrics.map((metric, index) => {
        // const { x: xEnd, y: yEnd } = calculatePoint(metric.max_value, index, metrics.length);
        const { x: labelX, y: labelY } = calculatePoint(metric.max_value, index, metrics.length, 12); // Offset labels outside the polygon
        return (
            <g key={metric.name}>
                {/* <line
                    x1={chartCenterX}
                    y1={chartCenterY}
                    x2={xEnd}
                    y2={yEnd}
                    stroke={STROKE_COLOR}
                /> */}
                <text
                    x={labelX}
                    y={labelY}
                    fill={STROKE_COLOR}
                    fontSize={FONT_SIZE}
                    textAnchor={labelX >= chartCenterX ? "start" : "end"}
                    alignmentBaseline="central"
                >
                    {metric.name}
                </text>
            </g>
        );
    });

    // Create a linear scale for the metric values
    const metricValues = metrics.map(metric => metric.max_value);
    const metricScale = scaleLinear()
        .domain([0, Math.max(...metricValues)])
        .range([0, radius]);

    // Generate the ticks for the scale
    const ticks = metricScale.ticks(5);

    // Create a grid of polygons using the ticks
    const grid = ticks.map((tick, index) => {
        const points = metrics.map((metric, metricIndex) => {
            const point = calculatePoint(tick, metricIndex, metrics.length);
            return `${point.x},${point.y}`;
        }).join(' ');

        return (
            <g>
                <polygon
                    key={tick}
                    points={points}
                    stroke={GRID_STROKE_COLOR}
                    strokeWidth="1"
                    fill="none"
                />
                <text
                    x={chartCenterX}
                    y={chartCenterY - metricScale(tick) + 14}
                    fill={STROKE_COLOR}
                    fontSize={GRID_FONT_SIZE}
                    textAnchor="middle"
                >
                    {tick}
                </text>
            </g>
        );
    });

    // Add tick labels to min and max values of the grid
    const minLabel = (
        <text
            x={chartCenterX}
            y={chartCenterY}
            fill={STROKE_COLOR}
            fontSize={GRID_FONT_SIZE}
            textAnchor="middle"
        >
            {DEFAULT_LABEL.MIN}
        </text>
    );

    const maxLabel = (
        <text
            x={chartCenterX}
            y={chartCenterY - radius + 24}
            fill={STROKE_COLOR}
            fontSize={GRID_FONT_SIZE}
            textAnchor="middle"
        >
            {DEFAULT_LABEL.MAX}
        </text>
    );

    // Map the data sets to SVG polygons
    const polygons = data.map((dataset, datasetIndex) => {
        // Calculate the points for the polygon
        const points = metrics.map((metric, index) => {
            const value = dataset.values[metric.name];
            const point = calculatePoint(value, index, metrics.length);
            return `${point.x},${point.y}`;
        }).join(' ');

        return (
            <polygon
                key={dataset.label}
                points={points}
                stroke={COLORS[datasetIndex]}
                strokeWidth="2"
                fill={"transparent"}
            />
        );
    });

    const legendWidth = data.length * 100;
    const legendX = (containerWidth - legendWidth) / 2;
    const legend = data.map((dataset, index) => (
        <g key={dataset.label} transform={`translate(${legendX + index * 100}, 0)`}>
            <circle cx={3} cy={8} r={8} fill={COLORS[index]} />
            <text x={15} y={13} fontSize={FONT_SIZE} fill={STROKE_COLOR}>
                {dataset.label}
            </text>
        </g>
    ));

    const legendWrapper = (
        <g transform={`translate(0, ${containerHeight - legendHeight})`}>
            {legend}
        </g>
    );

    return (
        <svg width={containerWidth} height={containerHeight}>
            <g>
                {axesAndLabels}
                {polygons}
                {grid}
                {legendWrapper}
                {minLabel}
                {maxLabel}
            </g>
        </svg>
    );
};

export default RadarChart;
