import { Option } from "../Dropdown/Dropdown";

export enum Benchmark {
    LAST_PRICE = "LAST_PRICE",
    TWAP = "TWAP",
    VWAP = "VWAP",
}

export const BenchmarkFilterOptions: Option[] = [
    { value: Benchmark.LAST_PRICE, name: "Last Price" },
    { value: Benchmark.TWAP, name: "TWAP" },
    { value: Benchmark.VWAP, name: "VWAP" },
];

export enum TimeFilter {
    LAST_1_DAY = "last_1_day",
    LAST_7_DAYS = "last_7_days",
    LAST_30_DAYS = "last_30_days",
    LAST_90_DAYS = "last_90_days",
    LAST_365_DAYS = "last_365_days",
}

export const timeFilterOptions: Option[] = [
    { value: TimeFilter.LAST_1_DAY, name: "Last 1 day" },
    { value: TimeFilter.LAST_7_DAYS, name: "Last 7 days" },
    { value: TimeFilter.LAST_30_DAYS, name: "Last 30 days" },
    { value: TimeFilter.LAST_90_DAYS, name: "Last 90 days" },
    { value: TimeFilter.LAST_365_DAYS, name: "Last 365 days" },
];

export enum TimeFilterLast5Days {
    LAST_1_DAY = "last_1_day",
    LAST_2_DAYS = "last_2_days",
    LAST_3_DAYS = "last_3_days",
    LAST_4_DAYS = "last_4_days",
    LAST_5_DAYS = "last_5_days",
}

export const timeFilterOptionsLast5Days: Option[] = [
    { value: TimeFilter.LAST_1_DAY, name: "Last 1 day" },
    { value: TimeFilterLast5Days.LAST_2_DAYS, name: "Last 2 days" },
    { value: TimeFilterLast5Days.LAST_3_DAYS, name: "Last 3 days" },
    { value: TimeFilterLast5Days.LAST_4_DAYS, name: "Last 4 days" },
    { value: TimeFilterLast5Days.LAST_5_DAYS, name: "Last 5 days" },
];
