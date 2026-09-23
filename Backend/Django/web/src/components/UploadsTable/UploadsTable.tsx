import React from "react";
import { useNavigate } from "react-router-dom";
import { css, StyleSheet } from "aphrodite";
import Button from "../Button/Button";
import { File, SortConfig } from "./types";
import { useSortedUploads } from "./useSortedUploads";
import moment from "moment";

import downloadIcon from "../../Assets/icons/download-02.svg";
import deleteIcon from "../../Assets/icons/delete-02.svg";

import { normalizedFileSize } from "../FileDrop/FileDrop";

interface UploadsTableProps {
    uploads: File[];
    handleFileDelete: (fileId: number) => void;
}

const UploadsTable: React.FC<UploadsTableProps> = ({
    uploads,
    handleFileDelete,
}) => {
    const navigate = useNavigate();

    const [sortConfig, setSortConfig] = React.useState<SortConfig>({
        key: null,
        direction: "ascending",
    });
    const sortedUploads = useSortedUploads(uploads, sortConfig);

    const requestSort = (key: keyof File) => {
        let direction: "ascending" | "descending" = "ascending";
        if (sortConfig.key === key && sortConfig.direction === "ascending") {
            direction = "descending";
        }
        setSortConfig({ key, direction });
    };

    return (
        <div className={css(styles.container)}>
            <div className={css(styles.header)}>
                <p>Uploads List</p>
                <div>
                    <Button
                        onClick={() => navigate("/select-files")}
                        buttonType="secondary"
                        size="m"
                    >
                        Upload New
                    </Button>
                </div>
            </div>
            <br />
            <table className={css(styles.table)}>
                <thead className={css(styles.tableHeader)}>
                    <tr>
                        <th
                            className={css(
                                styles.tableCell,
                                styles.columnFileName
                            )}
                            onClick={() => requestSort("file_name")}
                        >
                            File
                        </th>
                        <th
                            className={css(styles.tableCell)}
                            onClick={() => requestSort("upload_date")}
                        >
                            Last Modified
                        </th>
                        <th
                            className={css(styles.tableCell)}
                            onClick={() => requestSort("file_size")}
                        >
                            Size
                        </th>
                        <th className={css(styles.tableCell)}></th>
                    </tr>
                </thead>
                <tbody>
                    {sortedUploads.map((upload: File, index) => (
                        <tr
                            key={upload.id}
                            className={css(
                                styles.tableRow,
                                index % 2 === 0 && styles.evenRow
                            )}
                        >
                            <td
                                className={css(
                                    styles.tableCell,
                                    styles.columnFileName
                                )}
                            >
                                {upload.file_name}
                            </td>
                            <td className={css(styles.tableCell)}>
                                {moment(upload.upload_date).format(
                                    "YYYY-MM-DD HH:mm:ss"
                                )}
                            </td>
                            <td className={css(styles.tableCell)}>
                                {normalizedFileSize(upload.file_size)}
                            </td>
                            <td className={css(styles.tableCell)}>
                                <div className={css(styles.actions)}>
                                    <Button
                                        onClick={() =>
                                            navigate(`/analytics/${upload.id}`)
                                        }
                                        buttonType="secondary"
                                        size="s"
                                    >
                                        Analyze
                                    </Button>
                                    <img
                                        src={downloadIcon}
                                        alt="Download"
                                        onClick={() =>
                                            window.open(
                                                `https://s3.amazonaws.com/analyticsv1/${upload.user_id}/${upload.file_name}`
                                            )
                                        }
                                        className={css(styles.actionBtn)}
                                    />
                                    <img
                                        src={deleteIcon}
                                        alt="Delete"
                                        onClick={() =>
                                            handleFileDelete(upload.id)
                                        }
                                        className={css(styles.actionBtn)}
                                    />
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default UploadsTable;

const styles = StyleSheet.create({
    container: {
        margin: "20px",
        backgroundColor: "#141414",
        borderRadius: "10px",
    },
    header: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        paddingLeft: "20px",
        backgroundColor: "#171717",
        fontWeight: "bold",
        fontSize: "24px",
        marginRight: "35px",
    },
    table: {
        width: "100%",
        borderCollapse: "collapse",
    },
    tableRow: {
        ":hover": {
            // opacity: 0.8,
        },
        height: "50px",
        alignItems: "center",
        border: "0.5px solid #222222",
    },
    evenRow: {
        backgroundColor: "#171717",
    },
    tableHeader: {
        backgroundColor: "#141414",
        height: "50px",
        color: "gray",
    },
    tableCell: {
        padding: "8px",
        textAlign: "center",
        width: "25%",
    },
    columnFileName: {
        textAlign: "left",
        paddingLeft: "20px",
    },
    actions: {
        display: "flex",
        justifyContent: "flex-end",
        alignItems: "center",
        gap: 20,
        paddingRight: "20px",
    },
    actionBtn: {
        padding: "5px",
        borderRadius: "5px",
        cursor: "pointer",
        ":hover": {
            backgroundColor: "#222222",
        },
    },
});
