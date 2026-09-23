import React from "react";
import { StyleSheet, css } from "aphrodite";
import logo from "../Navbar/logo.svg";
import { Link, useNavigate } from "react-router-dom";

import linkedin from "../../Assets/social_media/linkedin.svg";

const Footer: React.FC = () => {
    const navigate = useNavigate();
    return (
        <div className={css(styles.footer)}>
            <div className={css(styles.leftRow)}>
                <div className={css(styles.logo)}>
                    <img
                        src={logo}
                        alt="Blockhouse Logo"
                        className={css(styles.icon)}
                        onClick={() => navigate("/")}
                    />
                </div>

                <div>
                    <p className={css(styles.title)}>
                        Blockhouse Capital @2024
                    </p>
                </div>
            </div>

            <div className={css(styles.rightRow)}>
                <div className={css(styles.contentSection)}>
                    <div className={css(styles.links)}>
                        <div className={css(styles.subMenu)}>
                            <p className={css(styles.title)}>LEGAL</p>
                            <Link
                                to="/terms-of-service"
                                className={css(styles.link)}
                            >
                                Terms of service
                            </Link>
                            <Link
                                to="/privacy-policy"
                                className={css(styles.link)}
                            >
                                Privacy Policy
                            </Link>
                        </div>
                        <div className={css(styles.subMenu)}>
                            <p className={css(styles.title)}>COMPANY</p>
                            <Link to="/careers" className={css(styles.link)}>
                                Careers
                            </Link>
                            <Link to="/" className={css(styles.link)}>
                                Investment
                            </Link>
                        </div>
                    </div>
                </div>

                <div className={css(styles.socialMedia)}>
                    <Link
                        to="https://www.linkedin.com/company/blockhouse-capital/"
                        className={css(styles.link)}
                    >
                        <img
                            src={linkedin}
                            alt="LinkedIn"
                            className={css(styles.socialIcon)}
                        />
                    </Link>
                </div>
            </div>
        </div>
    );
};

const styles = StyleSheet.create({
    footer: {
        display: "flex",
        flexDirection: "row",
        justifyContent: "space-between",
        padding: "50px",
        backgroundColor: "#0F0F0F",
        height: "200px",
        width: "80%",
        marginBottom: "1rem",

        "@media (max-width: 768px)": {
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            height: "auto",
            borderRadius: "15px",
            padding: "30px",
        },
    },
    logo: {
        height: "100%",
        width: "100%",
        cursor: "pointer",
        display: "flex",
        alignItems: "flex-start",
    },
    icon: {
        height: "30px",
    },

    contentSection: {
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-end",
    },

    links: {
        display: "flex",
        flexDirection: "row",
        gap: "40px",

        "@media (max-width: 768px)": {
            flexDirection: "row",
            gap: "70px",
            width: "100%",
            justifyContent: "space-between",
            alignItems: "center",
        },
    },
    leftRow: {
        display: "flex",
        justifyContent: "space-between",
        flexDirection: "column",
        alignItems: "center",

        "@media (max-width: 768px)": {
            flexDirection: "column",
            gap: "20px",
            width: "100%",
            justifyContent: "center",
            alignItems: "flex-start",
        },
    },
    rightRow: {
        display: "flex",
        justifyContent: "space-between",
        flexDirection: "column",
        alignItems: "center",

        "@media (max-width: 768px)": {
            flexDirection: "column",
            gap: "40px",
            width: "100%",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginTop: "3rem",
        },
    },
    title: {
        fontWeight: 500,
        margin: "0",
        color: "#7A7A7A",
    },
    subMenu: {
        fontSize: "14px",
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
    },
    socialMedia: {
        width: "100%",
        marginTop: "auto",
        display: "flex",
        justifyContent: "flex-end",
        flexDirection: "row",
        gap: "30px",

        "@media (max-width: 768px)": {
            justifyContent: "flex-start",
        },
    },
    socialIcon: {
        width: "24px",
    },
    link: {
        color: "white",
        textDecoration: "none",
        ":hover": {
            textDecoration: "underline",
        },
        paddingTop: 20,
    },
});

export default Footer;
