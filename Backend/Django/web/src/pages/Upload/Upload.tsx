import Button from "../../components/Button/Button";
import React from "react";
import { css, StyleSheet } from "aphrodite";

import upload_file from "../../Assets/icons/upload_file.svg";
import api_connector from "../../Assets/icons/api_connector.svg";

import { useNavigate } from "react-router-dom";
import { logEvent } from "../../utils/analytics";

const Upload = () => {
    const navigate = useNavigate();
    const handleBrowseFiles = () => {
        navigate("/select-files");
    };

    return (
        <div className={css(styles.container)}>
            {/* <UploadBox /> */}
            <div className={css(styles.getStarted)}>
                <h2>To Get Started</h2>
                <p className={css(styles.secondaryText)}>
                    Drag and drop your CSV files here, or choose a file. You can
                    also connect using our API.
                </p>
                <br />

                <div className={css(styles.iconRow)}>
                    <Button onClick={handleBrowseFiles} icon={upload_file}>
                        Browse Files
                    </Button>
                    <p className={css(styles.secondaryText)}>or</p>
                    <Button buttonType="secondary" icon={api_connector}>
                        Connect API
                    </Button>
                </div>
            </div>
        </div>
    );
};

export default Upload;

const styles = StyleSheet.create({
    container: {
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        height: "60vh",
    },

    getStarted: {
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        width: 540,
        height: 308,
        border: "2px dashed gray",
        borderRadius: "15px",
        padding: "20px",
    },
    iconRow: {
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: "20px",
    },
    uploadChange: {
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: "20px",
    },
    secondaryText: {
        color: "gray",
    },
});
