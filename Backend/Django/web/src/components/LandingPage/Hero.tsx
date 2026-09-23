import React, { useState } from "react";
import { css, StyleSheet } from "aphrodite";

import Button from "../Button/Button";
import TryNow from "./TryNow";
import { EVENT, EVENT_NAME, logEvent } from "../../utils/analytics";

import backgroundSVG from "../../Assets/LandingPage/LandingPageBackground.svg";
import backgroundSVGMobile from "../../Assets/backgroundMobile.svg";
import hero_picture from "../../Assets/LandingPage/hero-picture.svg";

interface HeroProps {
    setIsDemoEmailModalOpen: () => void;
  }
const Hero = ({setIsDemoEmailModalOpen}: HeroProps) => {
    return (
        <div className={css(styles.section, styles.section1)}>
            <div className={css(styles.headerTitleContainer)}>
                <TryNow setIsDemoEmailModalOpen={setIsDemoEmailModalOpen}/>
                <h1 className={css(styles.headerTitle)}>
                    The Smarter Way to Improve{" "}
                </h1>
                <h1 className={css(styles.headerTitle)}>
                    Trade Execution
                </h1>
                <p className={css(styles.subtitle)}>
                    Visualize unstructured data, Discover personalized trade insights,
                    Create dynamic{" "}
                </p>
                <p className={css(styles.subtitle)}>
                    trade reports — with no Excel or Code.
                </p>
                <br />
                <br />
                <Button size="xl" onClick={() => {
                    logEvent(EVENT.CLICK, { event_name: EVENT_NAME.EMAIL_CAPTURE.OPEN_MODAL, component: "hero" });
                    setIsDemoEmailModalOpen()
                }}>
                    Speak to Blockhouse AI
                </Button>
            </div>

            <div className={css(styles.heroImageContainer)}>
                <img src={hero_picture} alt="Hero Image" className={css(styles.heroImage)} />
            </div>
        </div>
    );
};

export default Hero;

const styles = StyleSheet.create({
    section: {
        height: "180vh",
        display: "flex",
        flexDirection: "column",
    },

    section1: {
        justifyContent: "center",
        alignItems: "center",
        width: "100%",
        backgroundImage: `url(${backgroundSVG})`,
        backgroundRepeat: "no-repeat",

        "@media (max-width: 768px)": {
            backgroundImage: `url(${backgroundSVGMobile})`,
            backgroundSize: "cover",
            backgroundPosition: "center top -150px",
            backgroundRepeat: "no-repeat",
            height: "100vh",
            justifyContent: "flex-start",
            paddingTop: "60px",
        },

        "@media (max-width: 1280px)": {
            backgroundPosition: "center top -200px",
        },
    },

    headerTitleContainer: {
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        marginBottom: "20px",
    },
    headerTitle: {
        fontSize: "64px",
        margin: "0",
        background:
            "linear-gradient(to right, #FFFFFF, #808080), rgba(0, 0, 0, 0.8)",
        WebkitBackgroundClip: "text", // Use vendor prefix
        WebkitTextFillColor: "transparent",

        "@media (max-width: 768px)": {
            fontSize: "36px",
        },
    },
    title: {
        fontSize: "32px",
        margin: "10px",
    },
    subtitle: {
        fontSize: "20px",
        fontWeight: 700,
        margin: "0",
        color: "gray",
        padding: "0 300px",

        "@media (max-width: 768px)": {
            fontSize: "18px",
            textAlign: "center",
            padding: "0 20px",
        },
    },

    heroImageContainer: {
        marginTop: 100,
    },

    heroImage: {
        width: "90%",
    }
});
