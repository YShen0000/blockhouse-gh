import React, { useRef, useEffect, useState, ReactElement } from "react";
import * as d3 from "d3";
import { css, StyleSheet } from "aphrodite";

interface HeatmapProps {
    data: {
        markouts: number[][];
        traders: string[];
        intervals: number[];
    };
    containerWidth: number;
    containerHeight: number;
}

const GREEN_COLOR = "#00AC4F";
const YELLOW_COLOR = "#FFEA92";
const RED_COLOR = "#B5001F";

const Map: React.FC<HeatmapProps> = ({ data: { markouts, traders, intervals }, containerWidth, containerHeight }) => {
    const d3Container = useRef<SVGSVGElement | null>(null);
    const [tooltipContent, setTooltipContent] = useState<ReactElement>();
    const [tooltipPosition, setTooltipPosition] = useState<{
        x: number;
        y: number;
    }>({ x: 0, y: 0 });
    const [showTooltip, setShowTooltip] = useState<boolean>(false);
    useEffect(() => {
        if (markouts && d3Container.current && traders && intervals) {
            const margin = { top: 0, right: 60, bottom: 60, left: 40 };
            const padding = { top: 0, right: 60, bottom: 40, left: 90 };
            const legendGap = 20
            const svgWidth = containerWidth - margin.left - margin.right;
            const svgHeight = containerHeight - margin.top - margin.bottom;
            const svgContainer = d3.select(d3Container.current);
            svgContainer.selectAll("*").remove(); // Empty previous svg chart if present
            const svg = svgContainer
                .attr("width", svgWidth) // Additional space for the legend
                .attr("height", svgHeight)
                .append("g")
            // Scales
            const x = d3
                .scaleBand()
                .range([padding.left, svgWidth - padding.right])
                .domain(intervals.map((d) => d.toString() + " m"))
                .padding(0.01);
            const y = d3
                .scaleBand()
                .range([padding.top, svgHeight - padding.bottom])
                .domain(traders)
                .padding(0.01);

            const flatMarkouts = markouts.flat();
            const minVal = d3.min(flatMarkouts) ?? 0;
            const maxVal = d3.max(flatMarkouts) ?? 0;

            const colorScale = d3
                .scaleLinear<string>()
                .domain([minVal, (minVal + maxVal) / 2, maxVal])
                .range([RED_COLOR, YELLOW_COLOR, GREEN_COLOR]);

            markouts.forEach((row, i) => {
                svg.selectAll()
                    .data(row)
                    .enter()
                    .append("rect")
                    .attr("x", (_, j) => x(intervals[j].toString() + " m")!)
                    .attr("y", y(traders[i])!)
                    .attr("rx", 6)
                    .attr("ry", 6)
                    .attr("width", x.bandwidth())
                    .attr("height", y.bandwidth())
                    .style("fill", (d) => colorScale(d))
                    .on("mouseover", function () {
                        setShowTooltip(true);
                    })
                    .on("mousemove", function (event) {
                        const [mouseX, mouseY] = d3.pointer(event);
                        const offsetX = 20;
                        const offsetY = -20; // Adjusted to prevent tooltip from exceeding svg dimensions

                        const tooltipX = Math.min(mouseX + offsetX, svgWidth - 100); // Ensure tooltip fits within svg width
                        const tooltipY = Math.max(mouseY + offsetY, 0); // Ensure tooltip does not exceed svg top

                        setTooltipPosition({ x: tooltipX, y: tooltipY });

                        const d = d3.select(this).data()[0] as number;
                        setTooltipContent(
                            <div>
                                <p>Trader: {traders[i]}</p>
                                <p>Value: {d.toFixed(4)}</p>
                            </div>
                        );
                    })
                    .on("mouseout", function () {
                        setShowTooltip(false);
                    });
            });
            svg.append("g")
                .attr("transform", `translate(0,${svgHeight - padding.bottom + legendGap})`)
                .call(d3.axisBottom(x).tickSize(0))
                .select(".domain")
                .style("display", "none");

            svg.append("g")
                .call(d3.axisLeft(y).tickSize(0))
                .attr("transform", `translate(${padding.left - legendGap},0)`)
                .select(".domain")
                .style("display", "none");

            svg.selectAll(".tick text")
                .style("fill", "#7a7a7a")
                .style("font-size", "14px");

            const legendHeight = svgHeight - padding.top - padding.bottom;
            const legendWidth = 8;
            const legendRadius = 4;
            const legendTranslate = {
                left: svgWidth - padding.right + legendGap,
                top: padding.top,
            };

            const legendSvg = d3
                .select(d3Container.current)
                .append("g")
                .attr(
                    "transform",
                    `translate(${legendTranslate.left},${legendTranslate.top})`
                );

            const gradient = legendSvg
                .append("defs")
                .append("linearGradient")
                .attr("id", "gradient")
                .attr("x1", "0%")
                .attr("y1", "100%")
                .attr("x2", "0%")
                .attr("y2", "0%");

            gradient
                .append("stop")
                .attr("offset", "0%")
                .attr("stop-color", RED_COLOR);

            gradient
                .append("stop")
                .attr("offset", "50%")
                .attr("stop-color", YELLOW_COLOR);

            gradient
                .append("stop")
                .attr("offset", "100%")
                .attr("stop-color", GREEN_COLOR);

            legendSvg
                .append("rect")
                .attr("width", legendWidth)
                .attr("height", legendHeight)
                .attr("rx", legendRadius)
                .attr("ry", legendRadius)
                .style("fill", "url(#gradient)");

            const legendScale = d3
                .scaleLinear()
                .range([legendHeight, 0])
                .domain([minVal, maxVal]);

            legendSvg
                .append("g")
                .call(d3.axisRight(legendScale).ticks(5).tickSize(0))
                .attr("transform", `translate(${legendWidth},0)`)
                .select(".domain")
                .style("display", "none");

            legendSvg
                .selectAll(".tick text")
                .style("fill", "#7a7a7a")
                .style("font-size", "14px");
        }
    }, [markouts, traders, intervals, containerWidth, containerHeight]);
    return (
        <div style={{ position: "relative" }}>
            <svg ref={d3Container} />
            {showTooltip && (
                <div
                className={css(styles.tooltip)}
                style={{ left: tooltipPosition.x, top: tooltipPosition.y - 120 }}
                >
                {tooltipContent}
                </div>
            )}
        </div>
    );
};

export default Map;

const styles = StyleSheet.create({
    tooltip: {
        position: "absolute",
        textAlign: "left",
        padding: "10px",
        font: "14px sans-serif",
        background: "#f9f9f9",
        border: "1px solid #ddd",
        boxShadow: "0px 2px 4px rgba(0,0,0,0.2)",
        borderRadius: "8px",
        pointerEvents: "none",
        color: "#333",
        maxWidth: "200px",
        zIndex: 1,
    },
});
