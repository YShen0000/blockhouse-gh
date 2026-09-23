import React from "react";
import { scaleBand, scaleLinear } from "d3";
import formatNumber from "../../../../utils/formatNumber";

interface Value {
    category: string;
    value: number;
}

interface Group {
    groupName: string;
    values: Value[];
}

interface GroupedBarChartData {
    groups: Group[];
}

interface GroupedBarChartProps {
    data: GroupedBarChartData;
    containerWidth: number;
    containerHeight: number;
}

const GroupedBarChart: React.FC<GroupedBarChartProps> = ({
    data,
    containerWidth = 500,
    containerHeight = 300,
}) => {
    const { groups } = data;

    const margin = { top: 20, left: 40, right: 20, bottom: 80 };
    const chartWidth = containerWidth - margin.left - margin.right;
    const chartHeight = containerHeight - margin.top - margin.bottom;
    const TEXT_COLOR = "#7a7a7a";
    const COLORS = ["#7962E7", "#E77F65", "#7AE7C7"];
    const FONT_SIZE = "12px";

    // Collect all unique categories from all groups
    const allCategories = Array.from(
        new Set(
            groups.flatMap((group) =>
                group.values.map((value) => value.category)
            )
        )
    );

    const x0Scale = scaleBand()
        .domain(groups.map((d) => d.groupName))
        .rangeRound([0, chartWidth])
        .paddingInner(0.1);

    const x1Scale = scaleBand()
        .domain(allCategories)
        .rangeRound([0, x0Scale.bandwidth()])
        .padding(0.05);

    const minValue = Math.min(
        ...groups.flatMap((d) => d.values.map((v) => v.value))
    );
    const maxValue = Math.max(
        ...groups.flatMap((d) => d.values.map((v) => v.value))
    );
    const yScale = scaleLinear()
        .domain([Math.min(0, minValue), maxValue])
        .range([chartHeight, 0])
        .nice();

    let legendPosX = 0; // Starting position for the first legend item
    const legendSpacing = 10; // Spacing between legend item

    return (
        <svg width={containerWidth} height={containerHeight}>
            <g transform={`translate(${margin.left},${margin.top + 30})`}>
                <g transform={`translate(0,${-margin.top - 10})`}>
                    {allCategories.map((category, index) => {
                        const legendItem = (
                            <g
                                key={index}
                                transform={`translate(${legendPosX},0)`}
                            >
                                <rect
                                    width={18}
                                    height={18}
                                    fill={COLORS[index % COLORS.length]}
                                />
                                <text
                                    x={22}
                                    y={14}
                                    fontSize={FONT_SIZE}
                                    fill={TEXT_COLOR}
                                >
                                    {category}
                                </text>
                            </g>
                        );

                        // Estimate text width (assuming average character width is around 7 pixels, adjust as needed)
                        const estimatedTextWidth =
                            category.length * 7 + 22 + 18; // Text width + space + square width
                        legendPosX += estimatedTextWidth + legendSpacing; // Update position for the next legend item

                        return legendItem;
                    })}
                </g>
                {/* Axes */}
                <g className="axis axis--x">
                    <line
                        x1={0}
                        y1={yScale(0)}
                        x2={chartWidth}
                        y2={yScale(0)}
                        stroke={TEXT_COLOR}
                    />
                    {groups.map((group, i) => (
                        <text
                            key={i}
                            x={
                                x0Scale(group.groupName)! +
                                x0Scale.bandwidth() / 2
                            }
                            y={chartHeight + 20}
                            textAnchor="middle"
                            fontSize={FONT_SIZE}
                            fill={TEXT_COLOR}
                        >
                            {group.groupName}
                        </text>
                    ))}
                </g>
                <g className="axis axis--y">
                    {yScale.ticks().map((tick, i) => (
                        <g key={i} transform={`translate(0,${yScale(tick)})`}>
                            <line x1={0} x2={chartWidth} stroke={TEXT_COLOR} />
                            <text
                                x={-10}
                                y={0}
                                dy=".32em"
                                textAnchor="end"
                                fontSize={FONT_SIZE}
                                fill={TEXT_COLOR}
                            >
                                {formatNumber(tick)}
                            </text>
                        </g>
                    ))}
                </g>
                {/* Bars and Value Labels */}
                {groups.map((group, i) => (
                    <g
                        key={i}
                        transform={`translate(${x0Scale(group.groupName)},0)`}
                    >
                        {group.values.map((val, index) => (
                            <React.Fragment key={index}>
                                <rect
                                    x={x1Scale(val.category)!}
                                    y={
                                        val.value < 0
                                            ? yScale(0)
                                            : yScale(val.value)
                                    }
                                    width={x1Scale.bandwidth()}
                                    height={Math.abs(
                                        yScale(val.value) - yScale(0)
                                    )}
                                    fill={COLORS[index % COLORS.length]}
                                />
                                {/* <text
                                    x={
                                        x1Scale(val.category)! +
                                        x1Scale.bandwidth() / 2
                                    }
                                    y={
                                        val.value < 0
                                            ? yScale(val.value) + 15
                                            : yScale(val.value) - 5
                                    }
                                    fontSize={FONT_SIZE}
                                    fill={TEXT_COLOR}
                                    textAnchor="middle"
                                >
                                    {formatNumber(val.value)}
                                </text> */}
                            </React.Fragment>
                        ))}
                    </g>
                ))}
            </g>
        </svg>
    );
};

export default GroupedBarChart;
