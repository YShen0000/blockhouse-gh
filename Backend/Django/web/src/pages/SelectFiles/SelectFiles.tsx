import React from "react";
import { css, StyleSheet } from "aphrodite";
import UploadBox from "../../components/UploadBox/UploadBox";
import { logEvent } from "../../utils/analytics";

const SelectFiles = () => {
    return (
        <div className={css(styles.container)}>
            <UploadBox />
        </div>
    );
};

export default SelectFiles;

const styles = StyleSheet.create({
    container: {
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        height: "90vh",
    },
});
