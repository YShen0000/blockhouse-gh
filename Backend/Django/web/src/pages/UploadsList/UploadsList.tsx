import * as React from "react";
import axios from "axios";
import moment from "moment";

import UploadsTable from "../../components/UploadsTable/UploadsTable";
import { logEvent } from "../../utils/analytics";

interface File {
    id: number;
    user_id: number;
    file_name: string;
    upload_date: string;
    file_size: number;
}


const UploadsList = () => {
    const [uploads, setUploads] = React.useState<File[]>([]);

    const token = localStorage.getItem("token");

    React.useEffect(() => {
        axios
            .get("api/analytics/files/", {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            })
            .then((res) => {
                const convertedUploads = res.data.uploads.map(
                    (upload: File) => ({
                        ...upload,
                        LastModified: moment(upload.upload_date).format(
                            "YYYY-MM-DD HH:mm:ss"
                        ),
                    })
                );
                setUploads(convertedUploads);
            })
            .catch((err) => {
                console.log(err);
            });
    }, [token]);

    const handleFileDelete = React.useCallback(async (file_id: number) => {
        try {
            console.log(file_id);
            const response = await axios.post("api/analytics/delete_file/", {
                file_id: file_id,
            });
            console.log(response.data);

            const newUploads = uploads.filter((upload) => upload.id !== file_id);
            setUploads(newUploads);
            
        } catch (error) {
            console.error("Error deleting file:", error);
        }
    }, [uploads]);


    return (
        <div>
            <UploadsTable
                uploads={uploads}
                handleFileDelete={handleFileDelete}
            />
        </div>
    );
};

export default UploadsList;