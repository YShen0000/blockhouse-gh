import React, { useReducer, useState } from "react";
import GridLayout, { WidthProvider } from "react-grid-layout";

import { css, StyleSheet } from "aphrodite";
import { useParams } from "react-router-dom";
import { Menu } from '@headlessui/react'

import SlippageHeatMap from "../../components/Charts/containers/SlippageHeatMap";
import ExecutionsPieChart from "../../components/Charts/containers/ExecutionsPieChart/MockPieChart";
import TradeEvaluationBarGraph from "../../components/Charts/TradeEvaluationBarGraph";
import SlippageOverTimeChart from "../../components/Charts/SlippageOverTimeChart/MockChart";
import LiquidityPentagonChart from "../../components/Charts/containers/LiquidityPentagonChart";
import SegmentedBidAskSpreadChart from "../../components/Charts/containers/SegmentedBidAskSpreadChart";
import TradingVolumeBarChart from "../../components/Charts/containers/TradingVolumeBarChart";

import Button from "../../components/Button/Button";
import ChatOverlay from "../../components/Chat/ChatOverlay";
import { EVENT, EVENT_NAME, logEvent } from "../../utils/analytics";
import { Layout } from "react-grid-layout";
import { Add } from "@mui/icons-material";
import { ChartType } from "./ChartType";

const WidthAwareGridLayout = WidthProvider(GridLayout);



const DASHBOARD_CONFIG = {
    [ChartType.SLIPPAGE_HEAT_MAP]: { label: 'Slippage', Component: SlippageHeatMap },
    [ChartType.EXECUTIONS_PIE_CHART]: { label: 'Executions', Component: ExecutionsPieChart },
    [ChartType.TRADE_EVALUATION_BAR_GRAPH]: { label: 'Trade Evaluation', Component: TradeEvaluationBarGraph },
    [ChartType.SLIPPAGE_OVER_TIME_CHART]: { label: 'Slippage Over Time', Component: SlippageOverTimeChart },
    [ChartType.LIQUIDITY_PENTAGON_CHART]: { label: 'Liquidity Pentagon', Component: LiquidityPentagonChart },
    [ChartType.SEGMENTED_BID_ASK_SPREAD_CHART]: { label: 'Segmented BidAsk Spread', Component: SegmentedBidAskSpreadChart },
    [ChartType.TRADING_VOLUME_BAR_CHART]: { label: 'Trading Volume', Component: TradingVolumeBarChart }
};

const useDashboardLayout = () => {
    const COLUMNS = 2;
    const generateChartLayout: (chartType: ChartType) => Layout = (chartType) => {
        const layoutRows = Math.max(...reactGridLayout.map(item => item.y)) + 1;
        let nextAvailableX = 0;
        let nextAvailableY = 0;
        for (let row = 0; row <= layoutRows; row++) {
            const rowItems = reactGridLayout.filter(item => item.y === row);
            if (rowItems.length < COLUMNS) {
                nextAvailableY = row;
                nextAvailableX = rowItems.length ? 1 : 0;
                break;
            }
        }
        return { i: chartType, x: nextAvailableX, y: nextAvailableY, w: 1, h: 1 };
    }

    const initializeLayout = () => Object.entries(DASHBOARD_CONFIG).map(([chartType], index) => ({
        i: chartType,
        x: index % COLUMNS,
        y: Math.floor(index / COLUMNS),
        w: 1,
        h: 1,
    }));

    const [reactGridLayout, setReactGridLayout] = useState<Layout[]>(initializeLayout());
    const addChart = (chartType: ChartType) => setReactGridLayout([...reactGridLayout, generateChartLayout(chartType)]);
    const removeChart = (chartType: ChartType) => setReactGridLayout(reactGridLayout.filter((chart) => chart.i !== chartType));
    const toggleChart = (chartType: ChartType) => {
        logEvent(EVENT.CLICK, { event_name: EVENT_NAME.ANALYTICS_PAGE.CHART_TOGGLE, chart_type: chartType });
        isVisible(chartType) ? removeChart(chartType) : addChart(chartType)};

    const isVisible = (chartType: ChartType) => !!reactGridLayout.find((chart) => chart.i === chartType);
    return {
        reactGridLayout,
        setLayout: (layout: Layout[]) => setReactGridLayout(layout),
        toggleChart,
        isVisible,
    }
}

const useDataSources = () => {
    const [dataSources, setDataSources] = useState([
        { name: 'Bloomberg', icon: 'bloomberg.png', isVisible: true },
        { name: 'Excel', icon: 'excel.png', isVisible: true },
    ]);

    const toggleDataSourceVisibility = (name: string) => {
        setDataSources(dataSources.map(dataSource =>
            dataSource.name === name ? { ...dataSource, isVisible: !dataSource.isVisible } : dataSource
        ));
    };

    return { dataSources, toggleDataSourceVisibility };
}

const Analytics = () => {
    const {
        reactGridLayout: layout,
        toggleChart,
        isVisible,
        setLayout
    } = useDashboardLayout();
    const { key } = useParams();
    const [isChatOpen, setIsChatOpen] = useState<boolean>(false);
    const [hasSeenChat, setHasSeenChat] = useState<boolean>(false);
    const toggleChat = () => {
        setHasSeenChat(true);
        setIsChatOpen(!isChatOpen);
    }

    const { dataSources, toggleDataSourceVisibility } = useDataSources();
    return (
        <>
            <div className={css(styles.ribbon)}>
                <Menu as={"div"} style={{ position: "relative" }}>
                    <Menu.Button as={"div"}>
                        <Button customStyles={styles.ribbonButton}>
                            <Add />
                            Add Chart
                        </Button>
                    </Menu.Button>
                    <Menu.Items className={css(styles.dropdownMenuWrapper)}>
                        {layout.map(({ i: chartType }) => (
                            <Menu.Item key={chartType} >
                                <div className={css(styles.chartSelector)} onClick={() => toggleChart(chartType as ChartType)}>
                                    <input type="checkbox" className={css(styles.checkbox)} checked={isVisible(chartType as ChartType)} />
                                    {DASHBOARD_CONFIG[chartType as ChartType].label}
                                </div>
                            </Menu.Item>
                        ))}
                        <div className={css(styles.lineSeparator)}></div>
                        {Object.entries(DASHBOARD_CONFIG).filter(([chartType, { label }]) => !isVisible(chartType as ChartType)).map(([chartType, { label }]) => (
                            <Menu.Item key={chartType} >
                                <div className={css(styles.chartSelector)} onClick={() => toggleChart(chartType as ChartType)}>
                                    <input type="checkbox" className={css(styles.checkbox)} checked={isVisible(chartType as ChartType)} />

                                    {label}
                                </div>
                            </Menu.Item>
                        ))}
                    </Menu.Items>
                </Menu>
                <Menu as={"div"} style={{ position: "relative" }}>
                    <Menu.Button as={"div"}>
                        <Button customStyles={styles.ribbonButton}>
                            <Add />
                            Add Data Source
                        </Button>
                    </Menu.Button>
                    <Menu.Items className={css(styles.dropdownMenuWrapper)}>
                        <Menu.Item>
                            <div className={css(styles.chartSelector)}>
                                External sources coming soon
                            </div>
                        </Menu.Item>
                        {dataSources.map(({ name, icon, isVisible }) => (
                            <Menu.Item key={name} >
                                <div className={css(styles.chartSelector)} onClick={() => {
                                    logEvent(EVENT.CLICK, { event_name: EVENT_NAME.ANALYTICS_PAGE.DATA_SOURCE_TOGGLE, data_source: name });
                                    toggleDataSourceVisibility(name)
                                }}>
                                    <input type="checkbox" className={css(styles.checkbox)} checked={isVisible} />
                                    <img src={`/static/data_sources/${icon}`} className={css(styles.dataSourceIcon)} alt={name} />
                                    {name}
                                </div>
                            </Menu.Item>
                        ))}
                    </Menu.Items>
                </Menu>
            </div>
            <Button onClick={() => {
                logEvent(EVENT.CLICK, { event_name: EVENT_NAME.CHATBOT.OPEN });
                toggleChat();
            }} customStyles={[
                styles.chatButton,
                ...(!hasSeenChat ? [styles.chatButtonAnimation] : [])
            ]}>
                Show Chat
            </Button>

            {isChatOpen && <ChatOverlay file_id={key!} onClose={() => { logEvent(EVENT.CLICK, { event_name: EVENT_NAME.CHATBOT.CLOSE }); toggleChat() }} />}
            <div className={css(styles.charts)}>
                <WidthAwareGridLayout
                    style={{ position: "relative" }}
                    layout={layout}
                    cols={2}
                    rowHeight={550}
                    autoSize={true}
                    draggableHandle=".draggable"
                    margin={[24, 24]}
                    containerPadding={[60, 18]}
                    useCSSTransforms={true}
                    compactType="vertical"
                    onLayoutChange={(layout) => { setLayout(layout) }}
                >
                    {Object.entries(DASHBOARD_CONFIG).map(([chartType, { Component }]) => isVisible(chartType as ChartType) && (
                        <div key={chartType} className={css(styles.chartContainer)}>
                            <Component fileId={key!} />
                        </div>
                    ))}
                </WidthAwareGridLayout>
            </div>
        </>
    );
};

export default Analytics;

const styles = StyleSheet.create({
    dropdownMenuWrapper: {
        display: "flex",
        flexDirection: "column",
        gap: "4px",
        position: "absolute",
        top: "100%",
        backgroundColor: "#1f1f1f",
        borderRadius: "12px",
        width: "260px",
        boxSizing: "border-box",
        zIndex: 1000,
        padding: "4px"
    },
    checkbox: {
        transform: "scale(1.2)",
        cursor: "pointer",
        borderRadius: "4px",
        // selection color of checkbox
        accentColor: "#7962E7",
    },
    lineSeparator: {
        height: "1px",
        backgroundColor: "#2c2c2c",
        margin: "2px 0",
    },
    charts: {
    },
    chartContainer: {
        backgroundColor: "#141414",
        borderRadius: "1rem",
    },
    ribbon: {
        position: "relative",
        marginLeft: "60px",
        marginRight: "60px",
        display: "flex",
        flexWrap: "wrap",
        paddingTop: "10px",
        paddingBottom: "10px",
        gap: "10px",
    },
    ribbonButton: {
        display: "flex",
        alignItems: "center",
        height: "44px",
        gap: "12px",
        padding: "12px",
        borderRadius: "8px",
        boxSizing: "border-box",
        textAlign: "left",
        cursor: "pointer",
    },
    chartSelector: {
        display: "flex",
        alignItems: "center",
        height: "44px",
        gap: "12px",
        padding: "12px",
        borderRadius: "8px",
        boxSizing: "border-box",
        textAlign: "left",
        cursor: "pointer",
        ":hover": {
            backgroundColor: "#2c2c2c",
        }
    },
    ribbonButtonShow: {
        color: "rgba(255, 255, 255, 0.2)"
    },
    dataSourceIcon: {
        width: "20px",
        height: "20px",
        objectFit: "contain",
    },
    chatButton: {
        position: "fixed",
        bottom: "20px",
        right: "20px",
        zIndex: 1000,
    },
    chatButtonAnimation: {
        animationName: "bounceWithDelay",
        animationDuration: "4s",
        animationTimingFunction: "ease",
        animationDelay: "2s",
        animationIterationCount: "infinite",
        animationDirection: "normal",
        animationFillMode: "forwards",
        animationPlayState: "running",
    },
    chatOverlay: {
        position: "fixed",
        backgroundColor: "#0A0A0A",
        bottom: "0",
        right: "0",
        height: "400px",
        width: "300px",
        zIndex: 1001,
    },
});
