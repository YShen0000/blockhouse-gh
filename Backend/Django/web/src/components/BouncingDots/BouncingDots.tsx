import React from "react";
import "./BouncingDots.css";

const BouncingDots = (props: any) => {
    return (
        <>
            <div className="bouncing-loader">
                <div></div>
                <div></div>
                <div></div>
            </div>
        </>
    );
};

export default BouncingDots;
