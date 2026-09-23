import React from "react";
import { css, StyleSheet } from "aphrodite";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { useState } from "react";
import { EVENT, EVENT_NAME, logEvent } from "../../utils/analytics";

interface TryNowProps {
    setIsDemoEmailModalOpen: () => void;
}
const TryNow: React.FC<TryNowProps> = ({setIsDemoEmailModalOpen}: TryNowProps) => {

    return (
        <>
            <div className={css(styles.container)} onClick={() => {
                logEvent(EVENT.CLICK, { event_name: EVENT_NAME.EMAIL_CAPTURE.OPEN_MODAL, component: "try_now" });
                setIsDemoEmailModalOpen()
            }}>
                <div className={css(styles.headline)}>
                    Free trial with trade data
                </div>

                <hr className={css(styles.verticalLine)} />
                <>
                    <p className={css(styles.tryNow)}>Try Now</p>
                    <KeyboardArrowRightIcon />
                </>
            </div>
        </>
    );
};

export default TryNow;

const styles = StyleSheet.create({
    container: {
        display: "flex",
        justifyContent: "space-around",
        alignItems: "center",
        height: 40,
        width: 350,
        backgroundColor: "#141414",
        borderRadius: 50,
        marginBottom: 40,

        ":hover": {
            cursor: "pointer",
        },
    },
    verticalLine: {
        border: "1px solid #2C2C2C",
        height: 30,
        marginLeft: 5,
        marginRight: 5,
    },
    icon: {
        color: "white",
    },

    headline: {
        color: "#B8B8B8",
        paddingLeft: 10,
    },

    tryNow: {
        fontWeight: 500,
        color: "white",
        textDecoration: "none",

        display: "flex",
        justifyContent: "center",
        alignItems: "center",

        ":hover": {
            textDecoration: "underline",
        },
    },
});
