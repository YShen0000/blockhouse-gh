import React, { useEffect } from "react";

interface ExternalRedirectProps {
    to: string;
}

const ExternalRedirect: React.FC<ExternalRedirectProps> = ({ to }) => {
    useEffect(() => {
        window.location.href = to;
    }, [to]);

    return null;
};

export default ExternalRedirect;
