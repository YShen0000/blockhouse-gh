import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { StyleSheet, css } from "aphrodite";
import MenuIcon from "@mui/icons-material/Menu";
import CloseIcon from "@mui/icons-material/Close";
import Avatar from "@mui/material/Avatar";

import BlockhouseInput from "../BlockhouseInput/BlockhouseInput";
import BlockhouseButton from "../Button/BlockhouseButton";
import Button from "../Button/Button";
import LoginModal from "../LoginModal/LoginModal";
import logo from "./logo.svg";
import DemoEmailModal from "../../components/LandingPage/DemoEmailModal";


import { useAuth } from "../../hooks/useAuth";

import { EVENT, EVENT_NAME, logEvent } from "../../utils/analytics";

interface NavLinkProps {
    href: string;
    label: string;
}

const Navbar = () => {
    const [isLoggedIn] = useAuth();
    const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
    const [searchInput, setSearchInput] = useState("");
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement | null>(null);
    const [isDemoEmailModalOpen, setIsDemoEmailModalOpen] = useState(false);

    const navigate = useNavigate();

    const toggleDrawer = () => {
        logEvent(EVENT.CLICK, { event_name: EVENT_NAME.NAVBAR.TOGGLE_DRAWER });
        setIsDrawerOpen(!isDrawerOpen);
    };

    const closeDrawer = () => setIsDrawerOpen(false);

    const handleLogout = () => {
        logEvent(EVENT.SIGN_OUT);
        localStorage.removeItem("token");
        setIsDropdownOpen(false);
        setIsDrawerOpen(false);
        navigate("/");
    };

    const Drawer = () => (
        <div
            className={`${css(styles.drawer)} ${isDrawerOpen ? css(styles.drawerOpen) : ""
                }`}
        >
            {isDemoEmailModalOpen && <DemoEmailModal isOpen={isDemoEmailModalOpen} setIsOpen={setIsDemoEmailModalOpen} />}

            <ul className={css(styles.drawerList)}>
                <div className={css(styles.closeContainer)}>
                    <button
                        onClick={closeDrawer}
                        className={css(styles.closeButton)}
                    >
                        <CloseIcon />
                    </button>
                </div>
                {isLoggedIn ? (
                    <>
                        <BlockhouseInput
                            icon="⌘ + K"
                            placeholder="Search"
                            setInput={setSearchInput}
                        />
                        <NavLink href="/list" label="Analytics" />
                        <NavLink href="/settings" label="Settings" />
                        <Button onClick={handleLogout} fullWidth={true}>
                            Logout
                        </Button>
                    </>
                ) : (
                    <>
                        <Button
                            onClick={() => {
                                logEvent(EVENT.CLICK, { event_name: EVENT_NAME.AUTH.OPEN_MODAL });
                                setIsLoginModalOpen(true);
                            }}
                            buttonType="secondary"
                            fullWidth={true}
                        >
                            Enter App
                        </Button>
                        {location.pathname !== "/demo" && (
                            <Button onClick={() => {
                                logEvent(EVENT.CLICK, { event_name: EVENT_NAME.EMAIL_CAPTURE.OPEN_MODAL, component: "navbar" });
                                setIsDemoEmailModalOpen(true)
                            }} fullWidth={true}>
                                Try Demo
                            </Button>
                        )}

                        <li>
                            <LoginModal
                                isOpen={isLoginModalOpen}
                                setIsOpen={setIsLoginModalOpen}
                            />
                        </li>
                    </>
                )}
            </ul>
        </div>
    );

    const DropdownMenu = () => (
        <div
            className={`${css(styles.dropdownMenu)} ${isDropdownOpen ? css(styles.dropdownOpen) : ""
                }`}
            ref={dropdownRef}
        >
            <div className={css(styles.dropdownList)}>
                <NavLink href="/list" label="Analytics" />
                <NavLink href="/settings" label="Settings" />
                <Button onClick={handleLogout} fullWidth>
                    Logout
                </Button>
            </div>
        </div>
    );

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target as Node)
            ) {
                setIsDropdownOpen(false);
            }
        }

        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    const NavigationLinks = () => (
        <ul className={css(styles.navList)}>
            {isLoggedIn ? (
                <>
                    <li>
                        <Avatar
                            className={css(styles.profilePic)}
                            variant="circular"
                            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                        >
                            B
                        </Avatar>
                        <DropdownMenu />
                    </li>
                </>
            ) : (
                <>
                    <li>
                        <BlockhouseButton
                            onClick={() => {
                                logEvent(EVENT.CLICK, { event_name: EVENT_NAME.AUTH.OPEN_MODAL });
                                setIsLoginModalOpen(true);
                            }}
                            type="clear"
                            text="Enter App"
                        />
                    </li>
                    {location.pathname !== "/demo" && (
                        <li>
                            <Button onClick={() => {
                                logEvent(EVENT.CLICK, { event_name: EVENT_NAME.EMAIL_CAPTURE.OPEN_MODAL, component: "navbar" });
                                setIsDemoEmailModalOpen(true)
                            }}>Try Demo</Button>
                        </li>
                    )}
                    <li>
                        <LoginModal
                            isOpen={isLoginModalOpen}
                            setIsOpen={setIsLoginModalOpen}
                        />
                    </li>
                </>
            )}
        </ul>
    );

    const NavLink: React.FC<NavLinkProps> = ({ href, label }) => (
        <li>
            <a href={href} className={css(styles.navLink)}>
                {label}
            </a>
        </li>
    );

    return (
        <nav className={css(styles.navbar)}>
            <div className={css(styles.logoSearch)}>
                <img
                    src={logo}
                    alt="Blockhouse Logo"
                    className={css(styles.icon)}
                    onClick={() => navigate("/")}
                />

                {isLoggedIn && (
                    <div className={css(styles.search)}>
                        <BlockhouseInput
                            icon="⌘ + K"
                            placeholder="Search"
                            setInput={setSearchInput}
                        />
                    </div>
                )}
            </div>

            <Drawer />

            <NavigationLinks />

            <div className={css(styles.menuContainer)}>
                <MenuIcon
                    className={css(styles.menuIcon)}
                    onClick={toggleDrawer}
                />
            </div>
        </nav>
    );
};

export default Navbar;

const styles = StyleSheet.create({
    navbar: {
        display: "flex",
        justifyContent: "space-between",
        paddingLeft: "60px",
        paddingRight: "60px",

        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        backgroundColor: "rgba(0, 0, 0, 0.5)",
        backdropFilter: "blur(10px)",
        zIndex: 1000,

        "@media (max-width: 768px)": {
            padding: 20,
        },
    },
    logoSearch: {
        display: "flex",
        alignItems: "center",
        gap: "12px",
        padding: "0 12px",
    },
    icon: {
        height: "27px",
        ":hover": {
            cursor: "pointer",
        },
    },
    search: {
        "@media (max-width: 768px)": {
            display: "none",
        },
    },

    navList: {
        listStyle: "none",
        display: "flex",
        alignItems: "center",
        gap: "30px",

        "@media (max-width: 768px)": {
            display: "none",
        },
    },
    navLink: {
        color: "gray",
        textDecoration: "none",
        fontSize: "16px",
        fontWeight: 500,
        ":hover": {
            cursor: "pointer",
            color: "white",
        },
    },

    menuContainer: {
        display: "none",
        alignItems: "center",
        gap: "30px",
        "@media (max-width: 768px)": {
            display: "flex",
        },
    },
    menuIcon: {
        ":hover": {
            cursor: "pointer",
        },
    },
    drawer: {
        display: "none",
        position: "fixed",
        top: 0,
        right: 0,
        width: "60%",
        height: "100vh",
        backgroundColor: "#0F0F0F",
        zIndex: 1001,
        overflow: "auto",
        padding: "20px",
    },
    drawerOpen: {
        display: "block",
    },
    drawerList: {
        listStyle: "none",
        padding: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "20px",
        marginTop: "20px",
        width: "100%",
    },

    closeContainer: {
        display: "flex",
        justifyContent: "flex-end",
        width: "100%",
        // padding: "20px",
    },
    closeButton: {
        background: "none",
        border: "none",
        color: "white",
        ":hover": {
            cursor: "pointer",
        },
        width: "100%",
        display: "flex",
        justifyContent: "flex-end",
        paddingRight: "20px",
    },
    profilePic: {
        cursor: "pointer",
    },
    dropdownMenu: {
        display: "none",
        borderRadius: "10px",
        position: "absolute",
        backgroundColor: "#0F0F0F",
        boxShadow: "0px 8px 16px 0px rgba(0,0,0,0.2)",
        padding: 30,
        zIndex: 1,
        right: 60,
        marginTop: 10,
    },
    dropdownOpen: {
        display: "block",
        padding: 20,
        width: 200,
        height: 100,
    },
    dropdownList: {
        listStyle: "none",
        padding: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "20px",
    },
});
