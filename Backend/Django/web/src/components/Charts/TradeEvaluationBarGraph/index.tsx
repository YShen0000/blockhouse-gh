import axios from "axios";
import { CircularProgress } from "@mui/material";
import Dropdown, { Option } from "../../Dropdown/Dropdown";
import * as d3 from "d3";
import React, { useState, useCallback, useEffect } from "react";
import ReactDOM from "react-dom";
import { StyleSheet, css } from "aphrodite";
import { timeFilterOptions, TimeFilter } from "../constants";
import formatNumber from "../../../utils/formatNumber";
import ChartContainer from "../containers/ChartContainer";
import useMockApiData from "../../../hooks/charts/useMockApiData";
import { EVENT, EVENT_NAME, logEvent } from "../../../utils/analytics";
import { ChartType } from "../../../pages/Analytics/ChartType";

interface Props {
    fileId: string;
}

interface BarChartProps {
    data: [string, number][];
    containerWidth: number;
    containerHeight: number;
}

interface ApiData {
    [key: string]: number;
}

interface TooltipState {
    show: boolean;
    content: string;
    x: number;
    y: number;
}

interface TooltipProps {
    children: React.ReactNode;
    style: React.CSSProperties;
}

const Tooltip: React.FC<TooltipProps> = ({ children, style }) => {
    return ReactDOM.createPortal(
        <div
            style={{
                position: "fixed",
                pointerEvents: "none",
                zIndex: 100,
                ...style,
            }}
        >
            {children}
        </div>,
        document.body
    );
};
const generateMockData = () => {
    return {
        "aggregated_result": {
            "Expected TCA": (Math.random() - 0.5) * 10000000 * Math.random(),
            "Trade Impact": (Math.random() - 0.5) * 10000000 * Math.random(),
            "Net Trade Impact": (Math.random() - 0.5) * 10000000 * Math.random()
        },
        "unique_cusips": [
            "CUSIP0001",
            "CUSIP0002"
        ]
    };
};



const BarChart: React.FC<BarChartProps> = ({ data, containerWidth: width, containerHeight: height }) => {
    const [tooltip, setTooltip] = useState<TooltipState>({
        show: false,
        content: "",
        x: 0,
        y: 0,
    });

    const margin = { top: 20, right: 20, bottom: 20, left: 80 };
    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    const width1 = "80%";

    const yDomain = [
        Math.min(...data.map((d) => d[1]), 0),
        Math.max(...data.map((d) => d[1]), 0),
    ];
    const yScale = d3
        .scaleLinear()
        .domain(yDomain)
        .range([chartHeight, 0])
        .nice();
    // if all values are negative, value is 0
    // if all values are positive, value is chartHeight
    // else value lies linearly between the max and min
    const yZeroIntercept =
        Math.min(...data.map((d) => d[1])) < 0 &&
            Math.max(...data.map((d) => d[1])) <= 0
            ? 0
            : Math.min(...data.map((d) => d[1])) >= 0 &&
                Math.max(...data.map((d) => d[1])) > 0
                ? chartHeight
                : yScale(0);

    // Calculate the width of each bar
    const barWidth = chartWidth / data.length;
    const fontSize = 14;
    // todo: move colors to theme files
    const TEXT_COLOR = "#7a7a7a";
    const TEAL_COLOR = "#00B8B9";
    const PURPLE_COLOR = "#7962E7";
    const BLUE_COLOR = "#3DBEF6";
    const COLORS = [PURPLE_COLOR, TEAL_COLOR, BLUE_COLOR];

    return (
        <svg width={"100%"} height={"100%"}>
            <g transform={`translate(${margin.left},${margin.top})`}>
                {yScale.ticks(5).map((tickValue, i) => (
                    <g key={i} transform={`translate(0, ${yScale(tickValue)})`}>
                        <line x2={width1} stroke={TEXT_COLOR} />
                        <text
                            x={-20}
                            dy=".32em"
                            textAnchor="end"
                            fill={TEXT_COLOR}
                            fontSize={fontSize}
                        >
                            {formatNumber(tickValue)}
                        </text>
                    </g>
                ))}
                {data.map((d, i) => (
                    <g key={i} transform={`translate(${i * barWidth + 20},0)`}>
                        <rect
                            y={Math.min(yScale(d[1]), yZeroIntercept)}
                            width={barWidth * 0.8}
                            height={Math.abs(yScale(d[1]) - yZeroIntercept)}
                            fill={COLORS[i]}
                            rx={8}
                            ry={8}
                            onMouseEnter={(e) => {
                                setTooltip({
                                    show: true,
                                    content: `${d[0]}: ${formatNumber(d[1])}`,
                                    x: e.clientX + 10,
                                    y: e.clientY + 10,
                                });
                            }}
                            onMouseMove={(e) => {
                                setTooltip((prev) => ({
                                    ...prev,
                                    x: e.clientX + 10,
                                    y: e.clientY + 10,
                                }));
                            }}
                            onMouseLeave={() =>
                                setTooltip({
                                    show: false,
                                    content: "",
                                    x: 0,
                                    y: 0,
                                })
                            }
                        />
                        <text
                            x={barWidth * 0.4}
                            y={
                                yScale(d[1]) -
                                fontSize * (d[1] > 0 ? 1 : -1) +
                                4
                            } // offset = 4
                            textAnchor="middle"
                            fill={TEXT_COLOR}
                            fontSize={fontSize}
                        >
                            {formatNumber(d[1])}
                        </text>
                    </g>
                ))}
                {data.map((d, i) => (
                    <text
                        fontSize={fontSize}
                        fill={TEXT_COLOR}
                        key={i}
                        x={(i + 0.4) * barWidth}
                        y={chartHeight + 3 * fontSize}
                        textAnchor="middle"
                    >
                        {d[0]}
                    </text>
                ))}
            </g>
            {tooltip.show && (
                <Tooltip
                    style={{
                        top: tooltip.y,
                        left: tooltip.x,
                        backgroundColor: "#fff",
                        padding: "5px",
                        border: "1px solid #ccc",
                    }}
                >
                    {tooltip.content}
                </Tooltip>
            )}
        </svg>
    );
};

const BarGraphContainer: React.FC<Props> = ({ fileId }) => {
    const [cusip, setCusip] = useState<string>("");
    // const [data, setData] = useState<ApiData | null>(null);
    // const [isLoading, setIsLoading] = useState<boolean>(true);
    const [options, setOptions] = useState<Option[]>([]);
    const [timeFilter, setTimeFilter] = useState<TimeFilter>(
        TimeFilter.LAST_1_DAY
    );

    const [mockData, setMockData] = useState(generateMockData());
    const [data, isLoading, error] = useMockApiData(mockData);
    useEffect(() => {
        setOptions(
            mockData.unique_cusips.map((c: string) => ({
                value: c,
                name: c,
            }))
        );
    }, [mockData.unique_cusips]);

    // const token = localStorage.getItem("token");

    // const fetchBarGraphData = useCallback(async () => {
    //     setIsLoading(true);
    //     try {
    //         const response = await axios.post(
    //             "/api/analytics/bargraph/",
    //             { fileId, cusip, timeFilter },
    //             {
    //                 headers: {
    //                     Authorization: `Bearer ${token}`,
    //                 },
    //             }
    //         );

    //         if (response.status === 200) {
    //             setData(response.data.aggregated_result);
    //             setOptions(
    //                 response.data.unique_cusips.map((c: string) => ({
    //                     value: c,
    //                     name: c,
    //                 }))
    //             );
    //         }
    //     } catch (error) {
    //         console.error("Error fetching bar graph data", error);
    //     } finally {
    //         setIsLoading(false);
    //     }
    // }, [fileId, cusip, timeFilter]);

    // React.useEffect(() => {
    //     fetchBarGraphData();
    // }, [fetchBarGraphData]);

    const handleCusipSelect = (selectedOption: Option) => {
        setCusip(selectedOption.name);
        setMockData(generateMockData());
        logEvent(EVENT.SELECT, { event_name: EVENT_NAME.ANALYTICS_PAGE.SET_FILTER, filter: "cusip", chart: ChartType.TRADE_EVALUATION_BAR_GRAPH });
    };

    const handleTimeFilterSelect = (selectedOption: any) => {
        setTimeFilter(selectedOption.value);
        setMockData(generateMockData());
        logEvent(EVENT.SELECT, { event_name: EVENT_NAME.ANALYTICS_PAGE.SET_FILTER, filter: "time", chart: ChartType.TRADE_EVALUATION_BAR_GRAPH });
    };

    return (
        <ChartContainer
            title="Trade Evaluation"
            filters={
                <>
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
                </>
            }
            isLoading={!!isLoading}
            data={Object.entries(data?.aggregated_result || {})}
            Chart={BarChart}
        />
    );
};

export default BarGraphContainer;