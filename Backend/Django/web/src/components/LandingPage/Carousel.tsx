import React, { useState } from "react";
import { StyleSheet, css } from "aphrodite";
import chevron_up from "../../Assets/chevron-up.svg";
import HeatMap from "../Charts/containers/SlippageHeatMap/index";
import PieChart from "../Charts/containers/ExecutionsPieChart/MockPieChart";
import SlippageOverTimeChart from "../Charts/SlippageOverTimeChart/MockChart";
import LiquidityPentagonChart from "../Charts/containers/LiquidityPentagonChart";
import TradingVolumeBarChart from "../Charts/containers/TradingVolumeBarChart";
export type ImageData = {
    src: string;
    alt: string;
    text?: string;
};

type Data = {
    images: ImageData[];
};

const Carousel: React.FC<Data> = ({ images }) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [forceUpdate, setForceUpdate] = useState(0);
    const goToPrevious = () => {
        setCurrentIndex((prevIndex) =>
            prevIndex > 0 ? prevIndex - 1 : images.length - 1
        );
    };

    const goToNext = () => {
        setCurrentIndex((prevIndex) => (prevIndex + 1) % images.length);
    };

    const goToSlide = (index: number) => {
        setCurrentIndex(index);
        //  force re-render
        setForceUpdate(forceUpdate + 1);
    };

    const getSlideStyle = (index: number) => {
        let style = [styles.slide];
        if (index === currentIndex) {
            style.push(styles.activeSlide);
        } else if (
            index === currentIndex - 1 ||
            (currentIndex === 0 && index === images.length - 1)
        ) {
            style.push(styles.prevSlide);
        } else if (
            index === currentIndex + 1 ||
            (currentIndex === images.length - 1 && index === 0)
        ) {
            style.push(styles.nextSlide);
        }
        return style;
    };

    return (
        <div className={css(styles.carouselContainer)}>
            <div className={css(styles.imageContainer)}>
                <button
                    className={css(styles.button, styles.prevButton)}
                    onClick={goToPrevious}
                >
                    <img src={chevron_up} alt="chevron-up" className={css(styles.chevron_left)} />
                </button>

                <div className={css(styles.slidesContainer)}>
                    <>
                        {window.innerWidth < 768 ? (
                            images.map((image, index) => (
                                <div
                                    key={index}
                                    className={css(...getSlideStyle(index))}
                                >
                                    <div
                                        className={css(styles.image)}
                                    >
                                        <img className={css(styles.img)} src={image.src} alt={image.alt} />
                                    </div>
                                </div>
                            ))
                        ) : (
                            [<PieChart />, <SlippageOverTimeChart />, <HeatMap />, <LiquidityPentagonChart fileId="1" />, <TradingVolumeBarChart fileId="1" />].map((Component, index) => (
                                <div
                                    key={index}
                                    className={css(...getSlideStyle(index))}
                                >
                                    <div
                                        className={css(styles.chartCarousel)}
                                    >
                                        {Component}
                                    </div>
                                </div>
                            ))
                        )}
                    </>
                </div>

                <button
                    className={css(styles.button, styles.nextButton)}
                    onClick={goToNext}
                >
                    <img src={chevron_up} alt="chevron-up" />
                </button>
            </div>

            <div className={css(styles.indicatorContainer)}>
                {images.map((_, index) => (
                    <span
                        key={index}
                        className={css(
                            styles.dot,
                            index === currentIndex && styles.activeDot
                        )}
                        onClick={() => goToSlide(index)}
                    />
                ))}
            </div>
        </div>
    );
};

export default Carousel;

const styles = StyleSheet.create({
    carouselContainer: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        overflow: "hidden",

        "@media (max-width: 768px)": {
            height: "fit-content",
        },
    },
    imageContainer: {
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        gap: "2%",
        width: "100%",
        height: "550px",
        "@media (max-width: 768px)": {
            height: "fit-content",
        },
    },
    slidesContainer: {
        display: "flex",
        position: "relative",
        width: "85%",
        maxWidth: "800px",
        height: "100%",
        justifyContent: "center",
        "@media (max-width: 768px)": {
            height: "fit-content",
        },
    },
    slide: {
        pointerEvents: "none",
        opacity: 0,
        backgroundColor: "black",
        height: "fit-content",
        width: "100%",
        transition: "opacity 0.5s, transform 0.5s",
        "@media (max-width: 768px)": {
            display: "none",
        },
        "@media (min-width: 768px)": {
            position: "absolute",
        },
        transform: "translateX(-50%)", // Center and scale down
        left: "50%",
    },
    activeSlide: {
        pointerEvents: "auto",
        position: "relative",
        "@media (max-width: 768px)": {
            display: "block",
        },
        opacity: 1,
        zIndex: 1,
        "@media (min-width: 768px)": {
            transform: "translateX(-50%) scale(1)", // Active slide is full size
        },
    },
    prevSlide: {
        opacity: 0.5,
        transform: "translateX(calc(-100% - 10%)) scale(0.8)", // Positioned to the left

        "@media (max-width: 768px)": {
            display: "none",
        },
    },
    nextSlide: {
        opacity: 0.5,
        transform: "translateX(10%) scale(0.8)", // Positioned to the right

        "@media (max-width: 768px)": {
            display: "none",
        },
    },
    button: {
        cursor: "pointer",
        zIndex: 2,
        border: "none",
        backgroundColor: "white",
        borderRadius: "55%",
        width: "50px",
        height: "50px",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        ":hover": {
            backgroundColor: "lightGray",
        },

        fontSize: "20px",
        fontWeight: 800,
        // breakpoint, move to bottom right
        "@media (max-width: 768px)": {
            bottom: "-80px",
            position: "absolute",
        },
    },
    prevButton: {
        left: "55%",
    },
    chevron_left: {
        transform: "rotate(180deg)",
    },
    nextButton: {
        right: "15%",
    },
    image: {
        height: "100%",
        width: "100%",
        objectFit: "cover",

    },
    img: {
        width: "100%",
        height: "auto"
    },
    chartCarousel: {
        height: "550px",
        border: "1px solid #444",
        borderRadius: "10px",
        boxSizing: "border-box",
        width: "100%",
    },

    indicatorContainer: {
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#191919",
        padding: "7px",
        margin: "30px",
        borderRadius: "10px",

        "@media (max-width: 768px)": {
            alignSelf: "flex-start"
        },
    },
    dot: {
        height: "10px",
        width: "10px",
        backgroundColor: "#3D3D3D",
        borderRadius: "50%",
        margin: "0 5px",
        display: "inline-block",
        cursor: "pointer",
        transition: "background-color 0.3s",
    },
    activeDot: {
        backgroundColor: "white", // Or any color to indicate the active slide
    },
});
