import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { StyleSheet, css } from "aphrodite";

interface PieChartProps {
    data: {
        agg_comp: number;
        agg_noncomp: number;
        comp_volume_by_trader_percentage: { [key: string]: number };
        noncomp_volume_by_trader_percentage: { [key: string]: number };
        comp_volume_by_counterparty_percentage: { [key: string]: number };
        noncomp_volume_by_counterparty_percentage: { [key: string]: number };
    };
}

interface ChartProps extends PieChartProps {
    containerWidth: number;
    containerHeight: number;
}

interface PieChartDataItem {
    name: string;
    value: number;
}

type TooltipDataType = {
    traderData: { [key: string]: number };
    counterpartyData: { [key: string]: number };
} | null;

const Chart: React.FC<ChartProps> = ({ data, containerWidth, containerHeight }) => {
    const margin = {
        top: 20,
        right: 20,
        bottom: 40,
        left: 20
    }
    const ref = useRef<SVGSVGElement>(null);
    const tooltipRef = useRef<HTMLDivElement>(null);
    const [tooltipVisibility, setTooltipVisibility] = useState<
        "visible" | "hidden"
    >("hidden");
    const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
    const [tooltipData, setTooltipData] = useState<TooltipDataType>(null);
    useEffect(() => {
        if (ref.current) {
            drawPieChart();
        }
    }, [data, containerHeight, containerWidth]);

    const drawPieChart = () => {
        const width = containerWidth - margin.left - margin.right;
        const height = containerHeight - margin.top - margin.bottom;
        const radius = Math.min(width, height) / 2;

        const pie = d3.pie<PieChartDataItem>().value((d) => d.value);
        const pieData = pie([
            { name: "Completed", value: data.agg_comp },
            { name: "Non-Completed", value: data.agg_noncomp },
        ]);

        const arc = d3
            .arc<d3.PieArcDatum<PieChartDataItem>>()
            .innerRadius(0)
            .outerRadius(radius);

        const svg = d3
            .select(ref.current)
            .attr("width", width)
            .attr("height", height + 40)
            .html("");

        const g = svg
            .append("g")
            .attr("transform", `translate(${width / 2}, ${height / 2})`);

        const totalValue = pieData.reduce((sum, entry) => sum + entry.value, 0);
        const updateTooltipPosition = (event: MouseEvent) => {
            const tooltipWidth = tooltipRef.current?.offsetWidth || 0; // Assuming tooltip width
            const tooltipHeight = tooltipRef.current?.offsetHeight || 0; // Assuming tooltip height
            const svgRect = svg!.node()!.getBoundingClientRect();
            let x = event.clientX - svgRect.left;
            let y = event.clientY - svgRect.top;

            // Prevent tooltip from going beyond the right edge
            if (x + tooltipWidth > svgRect.width) {
                x = svgRect.width - tooltipWidth;
            }

            // Prevent tooltip from going beyond the bottom edge
            if (y + tooltipHeight > svgRect.height) {
                y = svgRect.height - tooltipHeight;
            }

            setTooltipPosition({ x, y });
        };
        // Draw pie chart
        g.selectAll("path")
            .data(pieData)
            .join("path")
            .attr("d", arc)
            .attr("fill", (d) =>
                d.data.name === "Completed" ? "#25BA54" : "#FFE176"
            )
            .on("mouseover", (event, d) => {
                setTooltipVisibility("visible");
                const traderData =
                    d.data.name === "Completed"
                        ? data.comp_volume_by_trader_percentage
                        : data.noncomp_volume_by_trader_percentage;
                const counterpartyData =
                    d.data.name === "Completed"
                        ? data.comp_volume_by_counterparty_percentage
                        : data.noncomp_volume_by_counterparty_percentage;

                setTooltipData({ traderData, counterpartyData });

                updateTooltipPosition(event);
            })
            .on("mousemove", (event) => {
                updateTooltipPosition(event);
            })
            .on("mouseout", () => {
                setTooltipVisibility("hidden");
                setTooltipData(null);
            });

        const legend = svg.append("g")
            .attr("transform", `translate(${width / 2}, ${height})`);

        legend.selectAll(null)
            .data(pieData)
            .enter()
            .append("rect")
            .attr("x", (_, i) => i * 96 - 96)
            .attr("y", 14)
            .attr("width", 12)
            .attr("height", 12)
            .attr("rx", 6)
            .attr("ry", 6)
            .attr("fill", (d) => d.data.name === "Completed" ? "#25BA54" : "#FFE176");
        legend.selectAll(null)
            .data(pieData)
            .enter()
            .append("text")
            .attr("x", (_, i) => i * 96 - 80)
            .attr("y", 25)
            .attr("font-size", "14px")
            .attr("fill", "#7a7a7a")
            .text((d) => d.data.name);
        // Labels
        g.selectAll("text")
            .data(pieData)
            .join("text")
            .attr("transform", (d) => `translate(${arc.centroid(d)})`)
            .attr("text-anchor", "middle")
            .text((d) => `${((d.data.value / totalValue) * 100).toFixed(1)}%`)
            .style("pointer-events", "none");
    };

    const renderTable = () => {
        if (!tooltipData) return null;

        const traderRows = Object.entries(tooltipData.traderData).map(
            ([key, value], index) => (
                <tr key={index}>
                    <td>{key}</td>
                    <td>{(value).toFixed(2)}%</td>
                </tr>
            )
        );

        const counterpartyRows = Object.entries(
            tooltipData.counterpartyData
        ).map(([key, value], index) => (
            <tr key={index}>
                <td>{key}</td>
                <td>{(value).toFixed(2)}%</td>
            </tr>
        ));

        return (
            <>
                <table>
                    <thead>
                        <tr>
                            <th>Trader</th>
                            <th>Trading Value %</th>
                        </tr>
                    </thead>
                    <tbody>{traderRows}</tbody>
                </table>
                <hr />
                <table>
                    <thead>
                        <tr>
                            <th>Counterparty</th>
                            <th>Trading Value %</th>
                        </tr>
                    </thead>
                    <tbody>{counterpartyRows}</tbody>
                </table>
            </>
        );
    };

    return (
        <div style={{ position: "relative" }}>
            <svg ref={ref} />
            <div
                ref={tooltipRef}
                id="tooltip"
                className={css(styles.tooltip)}
                style={{
                    pointerEvents: "none",
                    visibility: tooltipVisibility,
                    left: `${tooltipPosition.x + 30}px`,
                    top: `${tooltipPosition.y - 40}px`,
                }}
            >
                {renderTable()}
            </div>
        </div>
    );
};

export default Chart;

const styles = StyleSheet.create({
    tooltip: {
        position: "absolute",
        width: "250px",
        color: "black",
        border: "1px solid gray",
        backgroundColor: "white",
        padding: "5px",
        borderRadius: "5px",
        zIndex: 100,
    },
});
