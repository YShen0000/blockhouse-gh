import React from "react";
import { css, StyleSheet } from "aphrodite";

import { ChatBubbleProps } from "./ChatBubble";

import Line from "../Charts/SlippageOverTimeChart/Line";
import BarChart from "../Charts/primitives/BarChart/index";
import GroupedBarChart from "../Charts/primitives/GroupedBarChart";

interface ChartHelperProps {
    chart_type: "line" | "bar" | "grouped_bar_chart";
    data: any;
}

const chart = (type: ChartHelperProps["chart_type"], data: any) => {
    if (type === "line") {
        return <Line data={data} containerWidth={530} containerHeight={320} />;
    } else if (type === "bar") {
        return (
            <BarChart
                data={{ values: data }}
                containerWidth={530}
                containerHeight={300}
            />
        );
    } else if (type === "grouped_bar_chart") {
        console.log(data);
        return (
            <GroupedBarChart
                data={{ groups: data }}
                containerWidth={530}
                containerHeight={300}
            />
        );
    }
};
const ChartHelper: React.FC<ChartHelperProps> = ({ chart_type, data }) => {
    return (
        <div className={css(styles.chart)}>
            {chart(chart_type as any, data)}
        </div>
    );
};

export default ChartHelper;

const styles = StyleSheet.create({
    chart: {
        width: "100%",
        height: "100%",
    },
});
