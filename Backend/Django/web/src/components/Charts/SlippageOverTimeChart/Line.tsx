import React, { useCallback, useState, useRef } from "react";
import { format } from "d3-format";
import { scaleLinear, line, extent, schemeCategory10, scaleUtc } from "d3";
import { StyleSheet, css } from "aphrodite";

export interface TraderData {
    [key: string]: [string, string][];
}

interface LineChartProps {
    data: TraderData;
    containerWidth: number;
    containerHeight: number;
}

const Line: React.FC<LineChartProps> = ({
    data,
    containerWidth,
    containerHeight,
}) => {
    const svgRef = useRef<SVGSVGElement | null>(null);
    const [tooltip, setTooltip] = useState<{
        x: number;
        y: number;
        trader: string;
        pnl: number;
        date: string;
        show: boolean;
    }>({
        x: 0,
        y: 0,
        trader: "",
        pnl: 0,
        date: "",
        show: false,
    });

    const legendItemWidth = 120; // Width of each legend item
    const legendItemHeight = 30; // Height of each legend item
    const margin = { top: 10, right: 30, bottom: 85, left: 100 };
    const chartWidth = containerWidth - margin.left - margin.right;
    const chartHeight = containerHeight - margin.top - margin.bottom;

    const FONT_SIZE = 14;
    // todo: move colors to theme files
    const TEXT_COLOR = "#7a7a7a";
    const GRID_COLOR = "#444";

    // Extract all data points for all traders
    const allDataPoints: { date: Date; pnl: number }[] = [];

    Object.entries(data).forEach(([trader, traderData]) => {
        const traderDataPoints = traderData.map(([date, pnl]) => ({
            date: new Date(date),
            pnl: +pnl, // Convert pnl to a number
        }));
        allDataPoints.push(...traderDataPoints);
    });

    const xScale = scaleUtc()
        .domain(extent(allDataPoints, (d) => d.date) as [Date, Date])
        .range([margin.left, containerWidth - margin.right]);

    const yScale = scaleLinear()
        .domain(extent(allDataPoints, (d) => d.pnl) as [number, number])
        .nice()
        .range([chartHeight, margin.top]);

    // Create a line generator
    const lineGenerator = line<{ date: Date; pnl: number }>()
        .x((d) => xScale(d.date))
        .y((d) => yScale(d.pnl));

    // loop with -1 times item width since first iteration will add width
    let legendOffsetX = -legendItemWidth;
    let legendOffsetY = 0;

    const calculateTooltipPosition = useCallback(
        (
            e: React.MouseEvent<SVGCircleElement, MouseEvent>,
            tooltipWidth: number,
            tooltipHeight: number
        ): { x: number; y: number } => {
            const svgRect = svgRef.current?.getBoundingClientRect();
            if (!svgRect) return { x: 0, y: 0 };

            let x = e.clientX - svgRect.left;
            let y = e.clientY - svgRect.top;

            if (x + tooltipWidth > svgRect.width) {
                x = svgRect.width - tooltipWidth - 20;
            } else if (x < tooltipWidth / 2) {
                x = 20;
            }

            if (y + tooltipHeight > svgRect.height) {
                y = y - tooltipHeight - 20;
            } else if (y < tooltipHeight) {
                y = 60;
            }

            return { x, y };
        },
        []
    );

    const handleMouseEnter = useCallback(
        (
            e: React.MouseEvent<SVGCircleElement, MouseEvent>,
            trader: string,
            pnl: number,
            date: Date
        ) => {
            const { x, y } = calculateTooltipPosition(e, 220, 60);
            setTooltip({
                x,
                y,
                trader,
                pnl,
                date: date.toLocaleDateString(),
                show: true,
            });
        },
        [calculateTooltipPosition]
    );

    return (
        <svg ref={svgRef} width={containerWidth} height={containerHeight}>
            <g className="x-axis" transform={`translate(0,${chartHeight})`}>
                {xScale.ticks(6).map((value, index) => (
                    <g key={index} transform={`translate(${xScale(value)},0)`}>
                        <line y1={6} y2={-chartHeight} stroke={GRID_COLOR} />
                        <text
                            style={{ textAnchor: "middle" }}
                            y={20}
                            fill={TEXT_COLOR}
                            fontSize={FONT_SIZE}
                        >
                            {xScale.tickFormat()(value)}
                        </text>
                    </g>
                ))}
                <g
                    transform={`rotate(-90) translate(${
                        chartHeight / 2 - 80
                    },30)`}
                >
                    <text fill={TEXT_COLOR} fontSize={FONT_SIZE}>
                        {Object.keys(data).some(key => key.includes("STT")) ? "Average STT (bips)" : "Aggregated PnL"}
                    </text>
                </g>
            </g>
            <g className="y-axis" transform={`translate(${margin.left},0)`}>
                {yScale.ticks(7).map((value, index) => (
                    <g key={index} transform={`translate(0,${yScale(value)})`}>
                        <line x1={-6} x2={chartWidth} stroke={GRID_COLOR} />
                        <text
                            style={{ textAnchor: "end" }}
                            x={-10}
                            y={4}
                            fill={TEXT_COLOR}
                            fontSize={FONT_SIZE}
                        >
                            {format(".2s")(value)}
                        </text>
                    </g>
                ))}
            </g>
            {Object.entries(data).map(([trader, traderData], i) => {
                const lineData = traderData.map(([date, pnl]) => ({
                    date: new Date(date),
                    pnl: +pnl,
                }));

                // Create a legend item for each trader
                if (legendOffsetX + 2 * legendItemWidth > chartWidth) {
                    // Initially looping with -1 * width
                    legendOffsetX = 0; // Reset X offset
                    legendOffsetY += legendItemHeight; // Move to the next line
                } else {
                    legendOffsetX += legendItemWidth; // Initially looping with -1 * width
                }

                return (
                    <g key={i}>
                        <path
                            className={`line line-${i}`}
                            fill="none"
                            stroke={schemeCategory10[i]}
                            strokeWidth={2}
                            d={lineGenerator(lineData) || undefined}
                        />
                        <g
                            className="legend"
                            transform={`translate(${margin.left}, ${
                                containerHeight - margin.bottom + 40
                            })`}
                        >
                            <g
                                transform={`translate(${legendOffsetX}, ${legendOffsetY})`}
                            >
                                <rect
                                    width={16}
                                    height={16}
                                    rx={8}
                                    ry={8}
                                    fill={schemeCategory10[i]}
                                />
                                <text
                                    x={20}
                                    y={13}
                                    style={{
                                        fontSize: FONT_SIZE,
                                        fill: TEXT_COLOR,
                                    }}
                                >
                                    {trader}
                                </text>
                            </g>
                        </g>
                        {lineData.map((point, index) => (
                            <circle
                                key={index}
                                cx={xScale(point.date)}
                                cy={yScale(point.pnl)}
                                r={5}
                                fill={schemeCategory10[i]}
                                fillOpacity="0"
                                style={{ cursor: 'pointer' }}
                                onMouseEnter={(e) =>
                                    handleMouseEnter(
                                        e,
                                        trader,
                                        point.pnl,
                                        point.date
                                    )
                                }
                                onMouseLeave={() =>
                                    setTooltip((prev) => ({
                                        ...prev,
                                        show: false,
                                    }))
                                }
                            />
                        ))}
                    </g>
                );
            })}

            {tooltip.show && (
                <g transform={`translate(${tooltip.x}, ${tooltip.y})`}>
                    <rect
                        x={10}
                        y={-60}
                        width={140}
                        height={60}
                        fill="white"
                        stroke="#666"
                        opacity="0.9"
                    />
                    <text
                        x={15}
                        y={-45}
                        fill="#666"
                    >{`Trader: ${tooltip.trader}`}</text>
                    <text x={15} y={-30} fill="#666">{`PnL: ${format(".2f")(
                        tooltip.pnl
                    )}`}</text>{" "}
                    <text
                        x={15}
                        y={-15}
                        fill="#666"
                    >{`Date: ${tooltip.date}`}</text>
                </g>
            )}
        </svg>
    );
};

export default Line;
