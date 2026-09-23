function formatNumber(num: number): string {
    const absNum = Math.abs(num);
    const sign = num < 0 ? "-" : "";
    if (absNum >= 1000000000000) {
        return sign + (absNum / 1000000000000).toFixed(1) + "T";
    } else if (absNum >= 1000000000) {
        return sign + (absNum / 1000000000).toFixed(1) + "B";
    } else if (absNum >= 1000000) {
        return sign + (absNum / 1000000).toFixed(1) + "M";
    } else if (absNum >= 1000) {
        return sign + (absNum / 1000).toFixed(1) + "k";
    } else {
        return num.toString();
    }
}
export default formatNumber;
