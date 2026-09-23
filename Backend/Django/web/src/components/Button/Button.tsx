import React from "react";
import { CircularProgress } from "@mui/material";
import { StyleSheet, css } from "aphrodite";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
    size?: "s" | "m" | "lg" | "xl" | "2xl";
    fullWidth?: boolean;
    buttonType?: "primary" | "secondary";
    textColor?: string;
    textWeight?: 400 | 700;
    icon?: string;
    loading?: boolean;
    customStyles?: object;
};

const Button: React.FC<ButtonProps> = ({
    size = "m",
    fullWidth,
    buttonType = "primary",
    textColor,
    textWeight = 700,
    icon,
    loading = false,
    customStyles,
    ...props
}) => {
    const buttonStyles = getButtonStyles(
        buttonType,
        textColor,
        textWeight,
        loading
    );

    return (
        <button
            {...props}
            disabled={loading}
            className={css(
                styles.button,
                buttonStyles,
                styles[`button-${size}`],
                fullWidth && styles.fullWidth,
                loading ? styles.loading : styles.hoverStyle,
                customStyles && customStyles
            )}
        >
            {loading ? (
                <div className={css(styles.spinner)} aria-hidden="true">
                    <CircularProgress
                        size={spinnerSize(size)}
                        color="inherit"
                    />
                </div>
            ) : (
                <>
                    {icon && (
                        <img
                            src={icon}
                            className={css(styles.icon)}
                            alt="Button Icon"
                        />
                    )}
                    {props.children}
                </>
            )}
        </button>
    );
};

const getButtonStyles = (
    buttonType: "primary" | "secondary",
    textColor: string | undefined,
    textWeight: 400 | 700 | undefined,
    loading: boolean
) => {
    let backgroundColor, defaultTextColor;

    switch (buttonType) {
        case "primary":
            backgroundColor = loading ? "#e0e0e0" : "#FFFFFF";
            defaultTextColor = "Black";
            break;
        case "secondary":
            backgroundColor = loading ? "#2c2c2c" : "#3d3d3d";
            defaultTextColor = "White";
            break;
        default:
            backgroundColor = loading ? "#e0e0e0" : "#FFFFFF";
            defaultTextColor = "Black";
    }

    return StyleSheet.create({
        customButton: {
            backgroundColor,
            color: textColor || defaultTextColor,
            fontWeight: textWeight,
            cursor: loading ? "not-allowed" : "pointer",
        },
    }).customButton;
};

const spinnerSize = (size: string) => {
    return size === "s" || size === "m" ? 15 : size === "lg" ? 24 : 28;
};

const styles = StyleSheet.create({
    button: {
        padding: "10px 20px",
        borderRadius: "8px",
        border: "none",

        ":active": {
            animation: "bounce 0.8s ease forwards",
        },
    },
    hoverStyle: {
        ":hover": {
            transition: "0.3s",
            opacity: 0.8,
        },
    },
    loading: {
        cursor: "not-allowed",
        opacity: 0.8,
    },
    "button-s": {
        fontSize: "14px",
    },
    "button-m": {},
    "button-lg": {
        padding: "12px 24px",
        fontSize: "18px",
    },
    "button-xl": {
        padding: "14px 28px",
        fontSize: "20px",
    },
    "button-2xl": {
        padding: "16px 32px",
        fontSize: "22px",
    },
    fullWidth: {
        width: "100%",
    },
    icon: {
        marginRight: "8px",
        height: "1rem",
        verticalAlign: "middle",
    },
    spinner: {
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
    },

    empty: {},
});

export default Button;
