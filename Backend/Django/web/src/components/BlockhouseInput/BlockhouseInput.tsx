import React, {
    useState,
    useEffect,
    ReactNode,
    InputHTMLAttributes,
} from "react";
import { css, StyleSheet } from "aphrodite";

interface IBlockhouseInputProps extends InputHTMLAttributes<HTMLInputElement> {
    icon?: string | ReactNode;
    setInput: (input: string) => void;
    fullWidth?: boolean;
    multiline?: boolean;
    customStyles?: object;
}

const BlockhouseInput: React.FC<IBlockhouseInputProps> = ({
    icon,
    setInput,
    fullWidth,
    multiline = false,
    customStyles,
    ...inputProps
}) => {
    const [inputValue, setInputValue] = useState("");

    useEffect(() => {
        setInput(inputValue);
    }, [inputValue, setInput]);

    const handleChange = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
    ) => {
        setInputValue(event.target.value);
    };

    const textAreaRef = React.useRef<HTMLTextAreaElement>(null);
    useEffect(() => {
        if (multiline && textAreaRef.current) {
            textAreaRef.current.style.height = "0px";
            const scrollHeight = textAreaRef.current.scrollHeight;
            textAreaRef.current.style.height = `${scrollHeight}px`;
        }
    }, [inputValue, multiline]);

    return (
        <div
            className={css(
                multiline ? styles.bgBlack : styles.inputContainer,
                fullWidth && styles.fullWidth,
                customStyles && customStyles
            )}
        >
            {multiline ? (
                <textarea
                    ref={textAreaRef}
                    className={css(styles.textarea)}
                    onChange={handleChange}
                    {...(inputProps as React.TextareaHTMLAttributes<HTMLTextAreaElement>)}
                    // rows={1}
                />
            ) : (
                <input
                    className={css(styles.input)}
                    onChange={handleChange}
                    {...inputProps}
                />
            )}
            {icon && <span className={css(styles.commandKey)}>{icon}</span>}
        </div>
    );
};

export default BlockhouseInput;

const styles = StyleSheet.create({
    inputContainer: {
        display: "flex",
        width: "240px",
        alignItems: "center",
        backgroundColor: "#1F1F1F",
        borderRadius: "5px",
        padding: "5px",
    },
    fullWidth: {
        width: "100%",
    },
    input: {
        flex: 1,
        height: "24px",
        width: "95%",
        border: "none",
        color: "white",
        backgroundColor: "transparent",
        outline: "none",
        marginLeft: "5px",
    },
    textarea: {
        minHeight: "24px",
        maxHeight: "100px",
        width: "95%",
        border: "none",
        color: "white",
        backgroundColor: "#0D0D0D",
        outline: "none",
        marginLeft: "5px",
        overflowY: "auto",
        resize: "none",
        justifyContent: "center",
        fontFamily: "inherit",
    },
    commandKey: {
        fontSize: "14px",
        fontWeight: 600,
        margin: "5px",
        color: "#7A7A7A",
    },

    bgBlack: {
        display: "flex",
        width: "240px",
        alignItems: "center",
        border: "1px solid #1B1B1B",
        borderRadius: "5px",
        padding: "5px",
        backgroundColor: "#0D0D0D",
    },
});
