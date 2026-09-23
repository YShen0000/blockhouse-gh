import React, { useState } from "react";
import { css, StyleSheet } from "aphrodite";
import card_img_1 from "../../Assets/LandingPage/card_img_1.svg";
import card_img_2 from "../../Assets/LandingPage/card_img_2.svg";
import card_img_3 from "../../Assets/LandingPage/card_img_3.svg";
import card_img_4 from "../../Assets/LandingPage/card_img_4.svg";



import backgroundSVG from "../../Assets/LandingPage/LandingPageBackground.svg";
import backgroundSVGMobile from "../../Assets/backgroundMobile.svg";

import chart_1 from "../../Assets/LandingPage/chart_1.png";
import chart_2 from "../../Assets/LandingPage/chart_2.png";
import chart_3 from "../../Assets/LandingPage/chart_3.png";
import chart_4 from "../../Assets/LandingPage/chart_4.png";
import chart_5 from "../../Assets/LandingPage/chart_5.png";

import chat_img from "../../Assets/LandingPage/chat_img.svg";
import chat_large from "../../Assets/LandingPage/chat_large.svg";

import Section5 from "../../components/LandingPage/Section5";
import DemoEmailModal from "../../components/LandingPage/DemoEmailModal";

import Footer from "../../components/Footer/Footer";

import Card from "../../components/LandingPage/Card";
import Carousel, { ImageData } from "../../components/LandingPage/Carousel";

import { Swiper, SwiperSlide } from "swiper/react";
import "swiper/css";
import "swiper/css/pagination";
import { Pagination } from "swiper/modules";



import Hero from "../../components/LandingPage/Hero";
import ProductFlow from "../../components/LandingPage/ProductFlow";

const cardData = [
    {
        title: "Visualize",
        subtitle:
            "Upload your unstructured data, create real-time data feeds, and view customizable dashboards around your trade execution",
        image: card_img_1,
    },
    {
        title: "Communicate",
        subtitle:
            "Query information directly in natural language - eliminating development of complex macros / scripts.",
        image: card_img_2,
    },
    {
        title: "Learn",
        subtitle:
            "Receive intelligence on execution quality scores, smart counterparty analysis, and liquidity profiles - to improve desk P&L.",
        image: card_img_3,
    },
    {
        title: "Report",
        subtitle:
            "Apply execution quality insights, manage fixed income order flow, and improve desk performance.",
        image: card_img_4,
    },
];

const carouselImages: ImageData[] = [
    {
        src: chart_1,
        alt: "Image 1",
    },
    {
        src: chart_2,
        alt: "Image 2",
    },
    {
        src: chart_3,
        alt: "Image 3",
    },
    {
        src: chart_4,
        alt: "Image 4",
    },
    {
        src: chart_5,
        alt: "Image 5",
    },
];


const HomePage: React.FC = () => {
    const [isDemoEmailModalOpen, setIsDemoEmailModalOpen] = useState(false);

    return (
        <div className={css(styles.container)}>
            {isDemoEmailModalOpen && <DemoEmailModal isOpen={isDemoEmailModalOpen} setIsOpen={setIsDemoEmailModalOpen}/>}
            <Hero setIsDemoEmailModalOpen={() => {
                    setIsDemoEmailModalOpen(true)
                }}/>
            <ProductFlow />

            <div className={css(styles.section, styles.section2)}>
                <div>
                    <p className={css(styles.subtitle2)}>FEATURES</p>
                    <h2 className={css(styles.title)}>Modern Tool Suite</h2>
                </div>
                <div className={css(styles.cardRow)}>
                    {cardData.map((card) => {
                        return (
                            <Card
                                title={card.title}
                                description={card.subtitle}
                                image={card.image}
                                key={card.title}
                            />
                        );
                    })}
                </div>

                <div className={css(styles.mySwiper)}>
                    <Swiper
                        modules={[Pagination]}
                        spaceBetween={50}
                        pagination={{
                            clickable: true,
                            el: ".custom-swiper-pagination", // Targeting external pagination container
                        }}
                    >
                        {cardData.map((card) => {
                            return (
                                <SwiperSlide key={card.title}>
                                    <div className={css(styles.swiperCard)}>
                                        <div
                                            className={css(
                                                styles.cardTitleContainer
                                            )}
                                        >
                                            <p
                                                className={css(
                                                    styles.cardTitle
                                                )}
                                            >
                                                {card.title}
                                            </p>
                                            <p
                                                className={css(
                                                    styles.cardDescription
                                                )}
                                            >
                                                {card.subtitle}
                                            </p>
                                        </div>
                                        <img
                                            src={card.image}
                                            alt={card.title}
                                            className={css(styles.cardImage)}
                                        />
                                    </div>
                                </SwiperSlide>
                            );
                        })}
                    </Swiper>
                    <div className="custom-swiper-pagination"></div>
                </div>
            </div>

            <div className={css(styles.section, styles.section3)}>
                <p className={css(styles.subtitle2)}>DASHBOARDS</p>
                <h2 className={css(styles.title)}>Unmatched Visualizations</h2>
                <div className={css(styles.subtitle)}>
                    Blockhouse visualizes real time data feeds into customizable
                    components to allow for an unparalleled view into trade
                    execution data.
                </div>

                <br />
                <br />

                <Carousel images={carouselImages} />
            </div>

            <div className={css(styles.section, styles.section4)}>
                <div>
                    <p className={css(styles.subtitle2)}>
                        NATURAL LANGUAGE PROCESSING
                    </p>
                    <h2 className={css(styles.title)}>Talk To Your Data</h2>
                    {/* <p className={css(styles.subtitle)}>
                        Communicate with your data in natural language
                    </p> */}

                    <div>
                        <img
                            src={chat_img}
                            alt="Chatbot"
                            className={css(styles.chatbotImg)}
                        />
                        <img
                            src={chat_large}
                            alt="Chatbot"
                            className={css(styles.chatLargeImg)}
                        />
                    </div>
                </div>
            </div>

            <Section5 />

            <div className={css(styles.section, styles.section6)}>
                <Footer />
            </div>
        </div>
    );
};

export default HomePage;

const styles = StyleSheet.create({
    container: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        // backgroundPosition: "top",
    },

    section: {
        height: "95vh",
        display: "flex",
        flexDirection: "column",
    },

    section1: {
        justifyContent: "center",
        alignItems: "center",
        width: "100%",
        backgroundImage: `url(${backgroundSVG})`,
        backgroundRepeat: "no-repeat",

        "@media (max-width: 768px)": {
            backgroundImage: `url(${backgroundSVGMobile})`,
            backgroundSize: "cover",
            backgroundPosition: "center top -150px",
            backgroundRepeat: "no-repeat",
            height: "80vh",
            justifyContent: "flex-start",
            paddingTop: "60px",
        },

        "@media (max-width: 1280px)": {
            backgroundPosition: "center top -200px",
        },
    },

    // Section 2
    section2: {
        minHeight: "auto",
        marginTop: "200px",

        "@media (max-width: 768px)": {
            height: "100%",
            padding: "50px 0",
            width: "100%",
        },
    },
    // Section 3
    section3: {
        width: "100%",

        // "@media (max-width: 768px)": {
        //     height: "70vh",
        //     marginTop: "50px",
        // },
    },

    // Section 4
    section4: {
        alignItems: "center",
        textAlign: "center",
        paddingTop: "100px",

        "@media (max-width: 768px)": {
            padding: "50px 0",
            height: "70vh",
        },
    },

    // Section 5
    section6: {
        width: "100%",
        height: "60vh",
        justifyContent: "flex-end",
        alignItems: "center",
        bottom: 0,
    },

    headerTitleContainer: {
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        marginBottom: "20px",
    },
    headerTitle: {
        fontSize: "64px",
        margin: "0",
        background:
            "linear-gradient(to right, #FFFFFF, #808080), rgba(0, 0, 0, 0.8)",
        WebkitBackgroundClip: "text", // Use vendor prefix
        WebkitTextFillColor: "transparent",

        "@media (max-width: 768px)": {
            fontSize: "36px",
        },
    },
    title: {
        fontSize: "32px",
        margin: "10px",
    },
    subtitle: {
        fontSize: "20px",
        fontWeight: 700,
        margin: "0",
        color: "gray",
        padding: "0 300px",

        "@media (max-width: 768px)": {
            fontSize: "18px",
            textAlign: "center",
            padding: "0 20px",
        },
    },
    subtitle2: {
        fontSize: "15px",
        fontWeight: 800,
        margin: "0",
        color: "gray",
        textAlign: "center",
    },
    cardRow: {
        display: "flex",
        // justifyContent: "space-between",
        alignItems: "flex-start",
        padding: "50px 50px 0 50px",
        gap: "24px",
        "@media (max-width: 768px)": {
            display: "none", // change it later
            flexDirection: "column",
            alignItems: "center",
        },
    },
    chatbotImg: {
        display: "none",

        "@media (max-width: 768px)": {
            display: "block",
            height: "400px",
            marginTop: 30,
        },
    },

    chatLargeImg: {
        height: "60vh",
        paddingTop: "50px",

        "@media (max-width: 768px)": {
            display: "none",
        },
    },

    // Carousel
    mySwiper: {
        display: "none",

        "@media (max-width: 768px)": {
            display: "block",
            marginTop: 20,
            padding: "20px",
        },
    },

    swiperCard: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#0F0F0F",
        borderRadius: "1rem",
        padding: "1.5rem",
        height: "400px",
        color: "white",
        textAlign: "center",
        gap: "1rem",
    },

    cardTitleContainer: {
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
    },
    cardTitle: {
        fontSize: "24px",
        fontWeight: 500,
        color: "white",
        margin: 0,
    },
    cardDescription: {
        textAlign: "left",
        fontSize: "14px",
        color: "gray",
    },
    cardImage: {
        margin: "auto",
        width: "250px",
        height: "250px",
    },
});
