import React, { useState, useEffect, useRef } from "react";
import { StyleSheet, css } from "aphrodite";

export interface Option {
    value: string;
    name: string;
}

interface DropdownProps {
    options: Option[];
    onSelect: (selected: Option) => void;
    selected?: string;
    allowOverflow?: boolean;
}

const Dropdown: React.FC<DropdownProps> = ({
    options,
    onSelect,
    selected,
    allowOverflow = false,
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [selectedOption, setSelectedOption] = useState<Option | undefined>(
        options.find((option) => option.value === selected)
    );
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (selected !== undefined) {
            const newSelectedOption = options.find(
                (option) => option.value === selected
            );
            setSelectedOption(newSelectedOption);
        }
    }, [selected, options]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target as Node)
            ) {
                setIsOpen(false);
            }
        };

        if (isOpen) {
            document.addEventListener("mousedown", handleClickOutside);
        }
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [isOpen]);

    const toggleDropdown = () => setIsOpen(!isOpen);

    const handleOnClick = (option: Option) => {
        setSelectedOption(option);
        onSelect(option);
        setIsOpen(false);
    };

    return (
        <div className={css(styles.dropdown)} ref={dropdownRef}>
            <button className={css(styles.button)} onClick={toggleDropdown}>
                {selectedOption ? selectedOption.name : "Select"}
                <span className={css(styles.arrow, isOpen && styles.arrowUp)} />
            </button>
            {isOpen && (
                <ul
                    className={css(
                        styles.list,
                        allowOverflow ? styles.listOverflow : styles.noOverflow
                    )}
                >
                    {options.map((option) => (
                        <li
                            key={option.value}
                            className={css(
                                styles.listItem,
                                selectedOption &&
                                    option.value === selectedOption.value &&
                                    styles.selectedItem
                            )}
                            onClick={() => handleOnClick(option)}
                        >
                            {option.name}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default Dropdown;

const styles = StyleSheet.create({
    dropdown: {
        position: "relative",
        display: "inline-block",
        fontWeight: 500,
    },
    button: {
        backgroundColor: "#1F1F1F",
        border: "none",
        borderRadius: "10px",
        padding: "10px 15px",
        cursor: "pointer",
        display: "flex",
        justifyContent: "space-between",
        color: "white",
        gap: "20px",
        alignItems: "center",
        width: "150px",
        fontWeight: 500,
    },
    arrow: {
        border: "solid #7A7A7A",
        borderWidth: "0 2px 2px 0",
        display: "inline-block",
        padding: "3px",
        transform: "rotate(45deg)",
        transition: "transform 0.3s",
    },
    arrowUp: {
        transform: "rotate(-135deg)",
    },
    list: {
        position: "absolute",
        zIndex: 1,
        backgroundColor: "#1F1F1F",
        // border: "1px solid darkgray",
        borderRadius: "10px",
        listStyleType: "none",
        padding: 0,
        margin: 0,
        marginTop: "5px",
        width: "100%",
    },
    listItem: {
        padding: "10px 15px",
        margin: "5px",
        cursor: "pointer",
        textAlign: "left",
        fontSize: "14px",
        borderRadius: "10px",
        ":hover": {
            backgroundColor: "#2e2e2e",
        },
    },
    listOverflow: {
        width: "auto",
    },
    noOverflow: {
        width: "100%",
    },
    selectedItem: {
        backgroundColor: "#2e2e2e",
    },
});
