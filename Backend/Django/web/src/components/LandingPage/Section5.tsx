import React from "react";
import { css, StyleSheet } from "aphrodite";

import BenchmarkChart from "../../Assets/Benchmark_chart.svg";
import venue_selection from "../../Assets/venue_selection.svg";
import counterparty_analysis from "../../Assets/counterparty_analysis.svg";
import regulatory_reporting from "../../Assets/regulatory_reporting.svg";
import order_optimization from "../../Assets/order_optimization.svg";

interface cardProps {
    image: string;
    title: string;
    style?: React.CSSProperties;
}

const Card: React.FC<cardProps> = ({ image, title, style }) => {
    return (
        <div className={css(styles.card)} style={{ ...style }}>
            <div className={css(styles.imageContainer)}>
                <img
                    src={image}
                    alt={title}
                    className={css(styles.cardImage)}
                />
            </div>
            <div className={css(styles.textContainer)}>
                <p className={css(styles.subtitle2)}>{title}</p>
            </div>
        </div>
    );
};

const Section5: React.FC = () => {
    return (
        <div className={css(styles.section5)}>
            <div>
                <p className={css(styles.subtitle2)}>ANALYTICS</p>
                <h2 className={css(styles.title)}>
                    Powerful Intelligence to improve your trade
                    execution.
                </h2>
            </div>

            <div className={css(styles.row)}>
                <Card image={BenchmarkChart} title="Liquidity Benchmarking" />
                <Card image={venue_selection} title="Venue Selection" />
                <Card
                    image={counterparty_analysis}
                    title="Counterparty Analysis"
                />
            </div>

            <div className={css(styles.row)}>
                <Card
                    image={regulatory_reporting}
                    title="Regulatory Reporting"
                />
                <Card image={order_optimization} title="Order Optimization" />
            </div>
        </div>
    );
};

export default Section5;

const styles = StyleSheet.create({
    section5: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        width: "100%",
        minHeight: "100%",
    },
    card: {
        flex: 1,
        backgroundColor: "#0F0F0F",
        borderRadius: "1rem",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
        height: "25vh",

        "@media (max-width: 768px)": {
            width: "80vw",
            minHeight: "20vh",
        },
    },
    title: {
        fontSize: "32px",
        margin: "10px",
        maxWidth: "80%",
        display: "inline-block",
    },
    subtitle2: {
        fontSize: "15px",
        fontWeight: 800,
        color: "gray",
        textAlign: "center",
        margin: 0,
    },
    row: {
        display: "flex",
        justifyContent: "space-around",
        marginTop: "1rem",
        gap: "1rem",

        width: "70dvw",

        "@media (max-width: 768px)": {
            flexDirection: "column",
            alignItems: "center",
            // paddingHorizontal: "10px",
        },
    },

    imageContainer: {
        flexGrow: 1,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "80%",
    },
    cardImage: {
        height: "70%",
        maxWidth: "80%",
    },
    textContainer: {
        textAlign: "center",
        height: "20%",
    },
});
