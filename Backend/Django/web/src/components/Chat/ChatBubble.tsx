import React, { useState } from "react";
import { StyleSheet, css } from "aphrodite";

import Table, { TableProps } from "../Table/Table";
import ChartHelper from "./ChartHelper";

export interface ChatBubbleProps {
    type: "text" | "table" | "chart" | "grouped_bar_chart";
    chart_type: "line" | "bar" | null;
    data: TableProps | string | any;
    sender: "assistant" | "user";
    image?: string;
    timestamp?: Date;
}

const ChatBubble: React.FC<ChatBubbleProps> = ({
    type,
    chart_type,
    data,
    sender,
    timestamp,
    image,
}) => {
    const [showTimestamp, setShowTimestamp] = useState(false);

    const toggleTimestamp = () => {
        setShowTimestamp(!showTimestamp);
    };
    return (
        <div
            className={css(
                styles.bubble,
                sender === "assistant" ? styles.incoming : styles.outgoing
            )}
            onClick={toggleTimestamp}
        >
            {image && (
                <img src={image} alt="Avatar" className={css(styles.image)} />
            )}
            <div className={css(styles.textContainer)}>
                {type === "text" ? (
                    <div>{data as string}</div>
                ) : type === "table" ? (
                    <Table
                        headers={(data as TableProps).headers}
                        rows={(data as TableProps).rows}
                    />
                ) : (
                    <ChartHelper chart_type={chart_type as "line" | "bar" | "grouped_bar_chart"} data={data} />
                )}

                {showTimestamp && timestamp && (
                    <div className={css(styles.timestamp)}>
                        {timestamp.toLocaleTimeString()}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ChatBubble;

export const styles = StyleSheet.create({
    bubble: {
        display: "flex",
        alignItems: "flex-end",
        padding: "10px",
        borderRadius: "20px",
        maxWidth: "70%",
        margin: "5px",
        fontSize: "16px",
    },
    image: {
        width: "40px",
        height: "40px",
        borderRadius: "20px",
        marginRight: "10px",
    },
    textContainer: {
        display: "flex",
        textAlign: "left",
        flexDirection: "column",
        padding: "3px",
        whiteSpace: "pre-wrap",
    },
    incoming: {
        backgroundColor: "#1D1E1E",
        alignSelf: "flex-start",
        color: "#BDBDBD",
        borderBottomLeftRadius: "4px"
    },
    outgoing: {
        backgroundColor: "#141414",
        alignSelf: "flex-end",
        color: "#BDBDBD",
        borderBottomRightRadius: "4px"
    },
    timestamp: {
        fontSize: "12px",
        marginTop: "5px",
        textAlign: "right",
        color: "#666",
    },
});
