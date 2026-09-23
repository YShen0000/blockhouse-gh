import { Modal, message } from "antd";
import { StyleSheet, css } from "aphrodite";
import logo from "../../../src/Assets/LoginLogo.svg";
import lock from "../../../src/Assets/icons/lock.svg";
import BlockhouseInput from "../BlockhouseInput/BlockhouseInput";
import Button from "../Button/Button";
import EmailLogo from "../../Assets/EmailLogo.svg";
import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

import { EVENT, EVENT_NAME, logEvent } from "../../utils/analytics";

interface ILoginModalProps {
    isOpen: boolean;
    setIsOpen: (isOpen: boolean) => void;
}

const LoginModal: React.FC<ILoginModalProps> = (props) => {
    const [email, setEmail] = useState<string>("");
    const [password, setPassword] = useState<string>("");
    const navigate = useNavigate();

    const showErrorMessage = (errorMessage: string) => {
        message.error(errorMessage);
    };

    const onLogin = async () => {
        const formData = new FormData();
        formData.append("email", email);
        formData.append("password", password);
        try {
            const response = await axios.post("/api/analytics/signin/", formData);
            if (response.data.access) {
                localStorage.setItem("token", response.data.access);
                logEvent(EVENT.SIGN_IN);
            }
            navigate("/upload");
            props.setIsOpen(false);
        } catch (err: any) {
            console.log(err);
            showErrorMessage(err.response?.data?.error);
        }
    };

    const handleClose = () => {
        props.setIsOpen(false);
        logEvent(EVENT.CLICK, { event_name: EVENT_NAME.AUTH.CLOSE_MODAL });
    };

    return (
        <Modal
            open={props.isOpen}
            onCancel={handleClose}
            footer={null}
            closeIcon={null}
            classNames={{ content: css(styles.loginModalBackground) }}
            centered={true}
            width={320}
            wrapClassName={css(styles.wrapperBackground)}
        >
            <div className={css(styles.loginModalContainer)}>
                <div className={css(styles.title)}>
                    <img
                        src={logo}
                        alt="Login Logo"
                        className={css(styles.logoImage)}
                    />
                    <h1 className={css(styles.title)}>Sign into Blockhouse</h1>
                </div>

                <BlockhouseInput
                    icon={<img src={EmailLogo} alt="emailLogo" />}
                    placeholder={"Email"}
                    setInput={setEmail}
                />
                <BlockhouseInput
                    icon={<img src={lock} alt="lock" />}
                    placeholder={"Password"}
                    setInput={setPassword}
                    type={"password"}
                />

                <Button onClick={() => onLogin()} fullWidth>
                    Continue
                </Button>
                <div className={css(styles.rowContainer)}>
                    <p className={css(styles.grey)}>New to blockhouse?</p>
                    <div
                        className={css(styles.helpText)}
                        // onClick={handleDemoClick}
                    >
                        Request Access
                    </div>
                </div>
            </div>
        </Modal>
    );
};

const styles = StyleSheet.create({
    wrapperBackground: {
        backgroundColor: "black",
    },
    loginModalBackground: {
        backgroundColor: "#141414",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
    },
    logoImage: {
        height: "40px",
    },
    loginModalContainer: {
        display: "flex",
        flexDirection: "column",
        gap: 20,
        justifyContent: "center",
        alignItems: "center",
        // width: "100%",
    },
    title: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        color: "white",
        fontSize: "20px",
    },
    rowContainer: {
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "row",
        gap: "5px",
    },
    or: {
        color: "white",
        margin: "0px",
    },
    line: {
        borderTop: "1px solid #292929",
        width: "110px",
    },
    helpText: {
        color: "white",
        margin: "0px",
        ":hover": {
            textDecoration: "underline",
            cursor: "pointer",
        },
    },
    grey: {
        color: "#7A7A7A",
    },
});

export default LoginModal;
