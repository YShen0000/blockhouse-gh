import React, { useRef } from "react";
import { CircularProgress } from "@mui/material";
import { css, StyleSheet } from "aphrodite";
import useContainerDimensions from "../../../../hooks/useContainerDimensions";
import { DragIndicator } from "@mui/icons-material";
import { EVENT, EVENT_NAME, logEvent } from "../../../../utils/analytics";

const ChartContainer: React.FC<{
    title: string;
    filters: React.ReactNode;
    isLoading: boolean;
    data: any;
    Chart: React.ComponentType<{
        data: any;
        containerWidth: number;
        containerHeight: number;
    }>;
}> = ({ title, filters, isLoading, data, Chart }) => {
    const containerRef = useRef(null);
    const containerDimensions = useContainerDimensions(containerRef);
    return (
        <div className={css(styles.container)}>
            <div className={css(styles.header)}>
                <div className={css(styles.chartTitle)}>{title}</div>
                <div onClick={() => logEvent(EVENT.CLICK, { event_name: EVENT_NAME.ANALYTICS_PAGE.DRAG_CHART, chart: title })} className={"draggable " + css(styles.dragHandle)}>
                    <DragIndicator htmlColor="#444"/>
                </div>
            </div>
            <div className={css(styles.filterRow)}>{filters}</div>
            <div ref={containerRef} className={css(styles.chartContainer)}>
                {isLoading ? (
                    <CircularProgress color="inherit" />
                ) : data ? (
                    <Chart
                        data={data}
                        containerWidth={containerDimensions.width}
                        containerHeight={containerDimensions.height}
                    />
                ) : (
                    <div>No Data Available</div>
                )}
            </div>
        </div>
    );
};

const styles = StyleSheet.create({
    container: {
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        gap: "1rem",
        padding: "1rem",
        boxSizing: "border-box",
    },
    header: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
    },
    chartTitle: {
        fontSize: "1.25rem",
        fontWeight: 600,
        textAlign: "left",
    },
    dragHandle: {
        color: "ccc",
        cursor: "grab",
    },
    filterRow: {
        display: "flex",
        justifyContent: "flex-start",
        alignItems: "center",
        flexDirection: "row",
        gap: "1rem",
    },
    chartContainer: {
        display: "flex",
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        width: "100%",
        maxHeight: "100%"
    },
});

export default ChartContainer;
