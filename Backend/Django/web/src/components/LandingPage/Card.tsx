import React from "react";
import { StyleSheet, css } from "aphrodite";

interface cardProps {
    title: string;
    description: string;
    image: string;
}

const Card: React.FC<cardProps> = ({ title, description, image }) => {
    return (
        <div className={css(styles.card)}>
            <div className={css(styles.cardTitleContainer)}>
                <p className={css(styles.cardTitle)}>{title}</p>
                <p className={css(styles.cardDescription)}>{description}</p>
            </div>
            <img src={image} alt={title} className={css(styles.cardImage)} />
        </div>
    );
};

export default Card;

const styles = StyleSheet.create({
    // Card
    card: {
        display: "flex",
        width: "20%",
        height: "320px",
        maxWidth: "324px",
        maxHeight: "424px",
        flexDirection: "column",
        borderRadius: "15px",
        alignItems: "center",
        textAlign: "left",
        padding: "25px",
        backgroundColor: "#0F0F0F",
        border: "1px solid #1B1B1B",

        "@media (max-width: 768px)": {
            width: "100%",
        },
    },
    cardTitleContainer: {
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
    },
    cardTitle: {
        fontSize: "24px",
        fontWeight: 500,
        color: "white",
        margin: 0,
    },
    cardDescription: {
        textAlign: "left",
        fontSize: "14px",
        color: "gray",
    },
    cardImage: {
        margin: "auto",
        width: "176px",
        height: "176px",
    },
});
