// import React from "react";
import { css, StyleSheet } from "aphrodite";

import discover_icon from "../../Assets/LandingPage/product_flow/discover_icon.svg";
import streamline_icon from "../../Assets/LandingPage/product_flow/streamline_icon.svg";
import visualize_icon from "../../Assets/LandingPage/product_flow/visualize_icon.svg";
import export_icon from "../../Assets/LandingPage/product_flow/export_icon.svg";
import arrow from "../../Assets/LandingPage/product_flow/arrow.svg";

// import { logEvent } from "../../utils/analytics";

const card_content = [
    {
        title: "Discover Blockhouse",
        description:
            "Get started with a tailored onboarding session. We'll guide you through features and set up your account.",
        icon: discover_icon,
        index: "01",
    },
    {
        title: "Streamline Your Data",
        description:
            "Upload Excel files or integrate APIs for seamless data analysis and real-time insights.",
        icon: streamline_icon,
        index: "02",
    },
    {
        title: "Visualize Your Trades",
        description:
            "Access our intuitive dashboard to visualize trade data and utilize our AI Assistant for support.",
        icon: visualize_icon,
        index: "03",
    },
    {
        title: "Export with Ease",
        description:
            "Customize your dashboard and export graphs to Excel or chat logs to Word effortlessly.",
        icon: export_icon,
        index: "04",
    },
];
const productCard = (
    icon: string,
    index: string,
    title: string,
    description: string,
    isMobileView: boolean
) => {
    const cardIndex = parseInt(index, 10);
    const isOdd = cardIndex % 2 !== 0;
    const cardStyle = isMobileView
        ? {}
        : {
              marginLeft: isOdd ? "0px" : "80px",
              marginRight: isOdd ? "80px" : "0px",
          };

    return (
        <div className={css(styles.card)} style={cardStyle}>
            <div className={css(styles.cardIconContainer)}>
                <img src={icon} alt={title} className={css(styles.cardImage)} />
                <p className={css(styles.cardIndex)}>{index}</p>
            </div>

            <div className={css(styles.cardTitleContainer)}>
                <p className={css(styles.cardTitle)}>{title}</p>
                <p className={css(styles.cardDescription)}>{description}</p>
            </div>
        </div>
    );
};
const ProductFlow = () => {
    const isMobileView = window.innerWidth <= 1400;
    return (
        <div className={css(styles.section, styles.section1)}>
            <div>
                <p className={css(styles.subtitle2)}>PRODUCT</p>
                <h2 className={css(styles.title)}>
                    Using the Blockhouse Interface
                </h2>
            </div>
            <div className={css(styles.cardContainer)}>
                <div>
                    <img
                        src={arrow}
                        alt="arrow"
                        className={css(styles.arrowTwo)}
                    />
                </div>
                <div
                    className={css(styles.cardRow)}
                    style={{
                        flexDirection: "row",
                        flexWrap: "wrap",
                        justifyContent: "center",
                    }}
                >
                    {card_content.map((card) => {
                        return (
                            <div
                                key={card.title}
                                className={css(styles.cardContainer)}
                            >
                                <div
                                    key={card.title}
                                    className={css(styles.cardContainer)}
                                >
                                    {productCard(
                                        card.icon,
                                        card.index,
                                        card.title,
                                        card.description,
                                        isMobileView
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
                <div>
                    <img
                        src={arrow}
                        alt="arrow"
                        className={css(styles.arrowOne)}
                    />
                    <img
                        src={arrow}
                        alt="arrow"
                        className={css(styles.arrowThree)}
                    />
                </div>
            </div>
        </div>
    );
};

export default ProductFlow;

const styles = StyleSheet.create({
    section: {
        minHeight: "120vh",
        display: "flex",
        flexDirection: "column",
    },

    section1: {
        justifyContent: "center",
        alignItems: "center",
        width: "100%",
        // backgroundImage: `url(${backgroundSVG})`,
        backgroundRepeat: "no-repeat",

        "@media (max-width: 768px)": {
            // backgroundImage: `url(${backgroundSVGMobile})`,
            backgroundSize: "cover",
            backgroundPosition: "center top -150px",
            backgroundRepeat: "no-repeat",
            height: "140vh",
            justifyContent: "flex-start",
            paddingTop: "60px",
        },

        "@media (max-width: 1280px)": {
            backgroundPosition: "center top -200px",
        },

        "@media (max-height: 380px)": {
            height: "auto",
        }
    },

    title: {
        fontSize: "32px",
        margin: "10px",
    },

    subtitle2: {
        fontSize: "15px",
        fontWeight: 800,
        margin: "0",
        color: "gray",
        textAlign: "center",
    },

    cardRow: {
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        marginTop: "50px",
        // gap: 5,
    },

    arrowOne: {
        position: "absolute",
        top: 150,
        right: "22%",
        zIndex: 0,

        "@media (max-width: 768px)": {
            display: "none",
        },

        "@media (max-width: 1280px)": {
            display: "none",
        },

        "@media (max-width: 1440px)": {
            right: "15%",
        },
    },

    arrowTwo: {
        position: "absolute",
        top: 450,
        left: "22%",
        transform: "rotateY(180deg)",
        zIndex: 0,

        "@media (max-width: 768px)": {
            display: "none",
        },

        "@media (max-width: 1280px)": {
            display: "none",
        },

        "@media (max-width: 1440px)": {
            left: "15%",
        },
    },

    arrowThree: {
        position: "absolute",
        top: 700,
        right: "22%",
        zIndex: 0,

        "@media (max-width: 768px)": {
            display: "none",
        },

        "@media (max-width: 1280px)": {
            display: "none",
        },

        "@media (max-width: 1440px)": {
            right: "15%",
        },
    },

    cardContainer: {
        position: "relative",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        width: "100%",
        marginBottom: "20px",
    },

    card: {
        width: "400px",
        height: "180px",
        backgroundColor: "#0F0F0F",
        borderRadius: 15,
        textAlign: "left",
        padding: 20,
        justifyContent: "space-between",
        zIndex: 1,

        "@media (max-width: 768px)": {
            width: "350px",
            height: "200px",
        }
    },

    cardIconContainer: {
        display: "flex",
        flexDirection: "row",
        justifyContent: "space-between",
        marginBottom: "20px",
    },

    cardImage: {
        width: 54,
        height: 54,
    },

    cardIndex: {
        fontSize: 70,
        fontWeight: 500,
        margin: "0",
        position: "relative",
        display: "inline-block",
        color: "transparent",
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        backgroundImage: "linear-gradient(to top, #191919 0%, #191919 100%)",
    },

    cardTitleContainer: {
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        marginTop: "auto",
        // height: "100%",
    },

    cardTitle: {
        fontSize: 20,
        fontWeight: 600,
        margin: "0",
    },

    cardDescription: {
        fontSize: 14,
        color: "gray",
    },
});
