import React, { useState, useRef } from "react";
import { StyleSheet, css } from "aphrodite";

import excel_icon from "../../Assets/icons/excel-icon.svg";
import plusIcon from "../../Assets/icons/ei_plus.svg";
import CloseIcon from "@mui/icons-material/Close";

interface FileDropProps {
    acceptedTypes?: string;
    onFilesChanged: (files: File[]) => void;
}

export const normalizedFileSize = (size: number) => {
    if (size < 1024) {
        return size + " B";
    }
    if (size < 1048576) {
        return (size / 1024).toFixed(2) + " KB";
    }
    return (size / 1048576).toFixed(2) + " MB";
};

const FileRow = ({ file, onRemove }: { file: File; onRemove: () => void }) => {
    const fileSizeInMB = normalizedFileSize(file.size);

    return (
        <div className={css(styles.fileRow)}>
            <div className={css(styles.fileNameGroup)}>
                <img src={excel_icon} alt="Excel Icon" />
                <p>{file.name}</p>
            </div>

            <div className={css(styles.fileNameGroup)}>
                <p className={css(styles.secondaryText)}>{fileSizeInMB}</p>
                <CloseIcon
                    onClick={onRemove}
                    className={css(styles.closeIcon)}
                />
            </div>
        </div>
    );
};

const FileDrop: React.FC<FileDropProps> = ({
    acceptedTypes,
    onFilesChanged,
}) => {
    const [files, setFiles] = useState<File[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const onDrop = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault();
        event.stopPropagation();
        processFiles(event.dataTransfer.files);
    };

    const onDragOver = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault();
    };

    const onClick = () => {
        if (fileInputRef.current) {
            fileInputRef.current.click();
        }
    };

    const onFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files) {
            processFiles(event.target.files);
        }
    };

    const processFiles = (fileList: FileList) => {
        const newFiles = Array.from(fileList).filter((file) => {
            if (!acceptedTypes) return true;
            return acceptedTypes
                .split(",")
                .some(
                    (type) =>
                        file.type.match(type.trim()) ||
                        file.name.endsWith(type.trim())
                );
        });
        setFiles((prevFiles) => {
            const updatedFiles = [...prevFiles, ...newFiles];
            onFilesChanged(updatedFiles); // Invoke the callback with the updated files
            return updatedFiles;
        });

        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    const removeFile = (index: number) => {
        setFiles((prevFiles) => {
            const updatedFiles = prevFiles.filter((_, i) => i !== index);
            onFilesChanged(updatedFiles); // Invoke the callback with the updated files
            return updatedFiles;
        });
    };

    return (
        <div className={css(styles.container)}>
            <div className={css(styles.titleRow)}>
                <h4 className={css(styles.iconGroupText)}>Uploaded Files</h4>
                <p className={css(styles.secondaryText)}>
                    {files.length} Files Added
                </p>
            </div>
            <div
                onClick={onClick}
                onDrop={onDrop}
                onDragOver={onDragOver}
                className={css(styles.dropZone)}
            >
                <div className={css(styles.iconGroup)}>
                    <img src={plusIcon} alt="Add File" />
                    <h4 className={css(styles.iconGroupHeading)}>
                        Drop your files here
                    </h4>
                    <p className={css(styles.iconGroupText)}>
                        <span className={css(styles.BrowseText)}>
                            browse files
                        </span>{" "}
                        from your computer
                    </p>
                </div>

                <input
                    type="file"
                    ref={fileInputRef}
                    style={{ display: "none" }}
                    onChange={onFileInputChange}
                    multiple
                />
            </div>
            {files.length > 0 && (
                <div className={css(styles.fileList)}>
                    {files.map((file, index) => (
                        <FileRow
                            key={index}
                            file={file}
                            onRemove={() => removeFile(index)}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

export default FileDrop;

const styles = StyleSheet.create({
    container: {
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        width: "100%",
        height: "100%",
        gap: 20,
    },
    titleRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        width: "100%",
        margin: 0,
    },
    secondaryText: {
        color: "gray",
        margin: 0,
    },
    BrowseText: {
        color: "#B8B8B8",
    },
    dropZone: {
        width: "90%",
        height: "150px",
        border: "1px dashed #3D3D3D",
        borderRadius: "15px",
        padding: "20px",
        textAlign: "center",
        ":hover": {
            transition: "0.3s",
            opacity: 0.8,
            cursor: "pointer",
        },
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
    },
    iconGroup: {
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        margin: 5,
    },
    iconGroupHeading: {
        margin: 5,
    },
    iconGroupText: {
        margin: 5,
    },
    fileRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: 2,
        paddingLeft: 10,
        paddingRight: 10,
        borderRadius: "10px",
        backgroundColor: "#292929",
    },
    fileList: {
        width: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 10,
    },
    fileNameGroup: {
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: 10,
    },
    closeIcon: {
        cursor: "pointer",
        ":hover": {
            color: "gray",
        },
    },
});
