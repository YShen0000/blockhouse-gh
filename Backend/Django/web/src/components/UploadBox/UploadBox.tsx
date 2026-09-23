import axios from "axios";
import React, { useState } from "react";
import { StyleSheet, css } from "aphrodite";
import { useNavigate } from "react-router-dom";

import Button from "../Button/Button";
import FileDrop from "../FileDrop/FileDrop";

const UploadBox: React.FC = () => {
    const navigate = useNavigate();
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [uploadingFile, setUploadingFile] = useState(false);

    const uploadFile = () => {
        if (selectedFiles.length === 0) {
            return;
        }
        
        setUploadingFile(true);
        const formData = new FormData();

        selectedFiles.forEach((file) => {
            formData.append("files", file);
        });

        const token = localStorage.getItem("token");

        console.log("Uploading file", selectedFiles);
        axios
            .post("/api/analytics/upload/", formData, {
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "multipart/form-data",
                },
            })
            .then((response) => {
                console.log("File uploaded successfully", response.data);
                navigate("/list");
            })
            .catch((error) => {
                console.error("Error uploading file", error);
            })
            .finally(() => {
                setUploadingFile(false);
            });
    };

    const handleFileUpdate = (files: File[]) => {
        setSelectedFiles(files);
    };

    const handleCancel = () => {
        navigate("/upload");
    };

    return (
        <div className={css(styles.container)}>
            <div className={css(styles.uploadBox)}>
                <FileDrop
                    acceptedTypes=".csv"
                    onFilesChanged={handleFileUpdate}
                />
                <hr className={css(styles.horizontalLine)} />
                <div className={css(styles.uploadChange)}>
                    <Button
                        onClick={handleCancel}
                        buttonType="secondary"
                        fullWidth
                    >
                        Cancel
                    </Button>
                    <Button onClick={uploadFile} fullWidth loading={uploadingFile}>
                        Continue
                    </Button>
                </div>
            </div>
        </div>
    );
};

const styles = StyleSheet.create({
    container: {
        width: "540px",
        borderRadius: "15px",
        backgroundColor: "#141414",
    },
    uploadBox: {
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "20px",
    },
    iconRow: {
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: "20px",
    },
    secondaryText: {
        color: "gray",
    },
    horizontalLine: {
        width: "100%",
        border: "none",
        borderTop: "1px solid #292929",
        margin: "30px",
    },
    uploadChange: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "20px",
        width: "100%",
    },
});

export default UploadBox;
