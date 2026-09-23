import React from "react";
import { css, StyleSheet } from "aphrodite";

export interface TableProps {
    headers: string[];
    rows: string[][];
}

const Table: React.FC<TableProps> = ({ headers, rows }) => {
    return (
        <div className={css(styles.table)}>
            <table className={css(styles.tableElement)}>
                <thead>
                    <tr className={css(styles.headerRow)}>
                        {headers.map((header) => (
                            <th key={header} className={css(styles.tableCell)}>{header}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row, index) => (
                        <tr key={index} className={css(styles.bodyRow)}>
                            {row.map((cell, cellIndex) => (
                                <td key={cellIndex} className={css(styles.tableCell)}>{cell}</td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default Table;
// TODO table width coming out of 60% width container
const styles = StyleSheet.create({
    table: {
        width: "100%",
        height: "100%",
        overflow: "auto",
    },
    tableElement: {
        borderCollapse: "collapse",
        width: "100%",
    },
    headerRow: {
        backgroundColor: "#383838",
        fontWeight: "bold",
        border: "1px solid gray",
        borderCollapse: "collapse",
        padding: "5px",


        "> th": {
            borderRight: "1px solid gray",
        },
        "> th:last-child": {
            borderRight: "none",
        },
    },
    bodyRow: {
        height: "25px",
        border: "1px solid gray",
        borderCollapse: "collapse",
        padding: "5px",

        "&:nth-of-type(odd)": {
            backgroundColor: "#EDEDED", 
        },
        "&:nth-of-type(even)": {
            backgroundColor: "#FFF",
        },
        "&:hover": {
            backgroundColor: "#ddd",
        },
        "> td": {
            borderRight: "1px solid white",
        },
        "> td:last-child": {
            borderRight: "none",
        },
    },
    tableCell: {
        border: "1px solid gray",
        borderCollapse: "collapse",
        textAlign: "center",
        padding: "5px",
        // maxWidth: "140px",
        // overflow: "hidden",
        // textOverflow: "ellipsis",
        // whiteSpace: "pre-wrap",
        // wordWrap: "break-word",
    }
});
