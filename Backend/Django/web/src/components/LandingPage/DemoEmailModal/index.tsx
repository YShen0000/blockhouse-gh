import { Modal, message } from "antd";
import { StyleSheet, css } from "aphrodite";
import logo from "../../../Assets/LoginLogo.svg";
import EmailLogo from "../../../Assets/EmailLogo.svg";
import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

import { EVENT, EVENT_NAME, identifyUserEmail, logEvent } from "../../../utils/analytics";
import Button from "../../Button/Button";
import BlockhouseInput from "../../BlockhouseInput/BlockhouseInput";

interface ILoginModalProps {
    isOpen: boolean;
    setIsOpen: (isOpen: boolean) => void;
}

const DemoEmailModal: React.FC<ILoginModalProps> = (props) => {
    const [email, setEmail] = useState<string>("");
    const navigate = useNavigate();

    const showErrorMessage = (errorMessage: string) => {
        message.error(errorMessage);
    };

    const onDemoClick = async () => {
        const formData = new FormData();
        formData.append("email", email);
        try {
            const response = await axios.post("/api/analytics/email_capture/", formData);
            navigate("/demo");
            logEvent(EVENT.CLICK, { event_name: EVENT_NAME.EMAIL_CAPTURE.SUBMIT });
            identifyUserEmail(email);
            props.setIsOpen(false);
        } catch (err: any) {
            console.log(err);
            showErrorMessage(err.response?.data?.error);
        }
    };

    const handleClose = () => {
        props.setIsOpen(false); 
        logEvent(EVENT.CLICK, { event_name: EVENT_NAME.EMAIL_CAPTURE.CLOSE_MODAL });
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
                    <h1 className={css(styles.title)}>Try Blockhouse demo</h1>
                </div>

                <BlockhouseInput
                    icon={<img src={EmailLogo} alt="emailLogo" />}
                    placeholder={"Email"}
                    setInput={setEmail}
                />
                <Button onClick={onDemoClick} fullWidth>
                    Continue
                </Button>
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

export default DemoEmailModal;
