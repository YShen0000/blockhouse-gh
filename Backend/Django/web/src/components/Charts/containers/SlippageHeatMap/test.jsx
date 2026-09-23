import React from "react";
import Plot from "react-plotly.js";

const HeatmapComponent = ({
    markouts,
    traders,
    intervals,
}) => {
    // Prepare the z-data for the heatmap
    const zData = markouts.map((markout) =>
        markout.map((value) => parseFloat(value.toFixed(2)))
    );

    return (
        <Plot
            data={[
                {
                    z: zData,
                    x: intervals,
                    y: traders,
                    type: "heatmap",
                    hoverongaps: false,
                },
            ]}
            layout={{
                title: "Trader Heatmap",
                xaxis: {
                    title: "Intervals",
                    type: "category",
                },
                yaxis: {
                    title: "Traders",
                    type: "category",
                },
            }}
        />
    );
};

export default HeatmapComponent;
