from postProcessing import PostProcessing
import pandas as pd

# TODO : Need to Clarify the method of taking input for currently I'm just taking a sample data input which was used in hoodwink's reports
# csvFile = "robinhood_trade_data_07_22_2024_20_46_23.csv"


def main():
    df = pd.read_csv(csvFile)
    report = PostProcessing(df)
    genReport = report.genReport()

    for i in genReport:
        if i == "potential_savings_table":
            for i in genReport[i]:
                print(i)
        else:
            print(f"{i} : {genReport[i]}")

    return genReport

if __name__ == "__main__":
    main()