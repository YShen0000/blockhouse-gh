from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from datetime import datetime
import os
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.section import WD_ORIENT
from django.http import HttpResponse
from Analytics.utils import reportCalculation
import base64
from io import BytesIO

# Font names available in Microsoft Word
FONT_NAME = "Source Sans Pro"
DEFAULT_FONT_SIZE = Pt(12)  # Default font size
HEADING_FONT_SIZE = Pt(13.5)


def add_paragraph(doc, text, align=None, font_size=None, bold=False, space_before=None, underline=None, color=None, bullet=False):
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)

    font = run.font
    font.name = FONT_NAME
    font.size = font_size if font_size else DEFAULT_FONT_SIZE

    run.bold = bold

    if align:
        paragraph.alignment = align

    if space_before is not None:
        paragraph.space_before = space_before

    if underline is not None:
        font.underline = underline

    if color is not None:
        font.color.rgb = RGBColor(*color)

    if bullet:
        paragraph.style = 'ListBullet'

    return paragraph

def set_cell_border(cell, **kwargs):
    """
    Set cell border
    Usage:
    set_cell_border(
        cell,
        top={"sz": 12, "val": "single", "color": "FF0000"},
        bottom={"sz": 12, "val": "single", "color": "00FF00"},
        start={"sz": 24, "val": "dashed", "color": "0000FF"},
        end={"sz": 12, "val": "dashed", "color": "FF00FF"},
    )
    """
    tc = cell._element
    tcPr = tc.get_or_add_tcPr()

    for border_name in ["top", "start", "bottom", "end", "insideH", "insideV"]:
        if border_name in kwargs:
            border = OxmlElement(f'w:{border_name}')
            for key, value in kwargs[border_name].items():
                border.set(qn(f'w:{key}'), str(value))  # Ensure the value is a string
            tcPr.append(border)

def add_horizontal_line(doc):
    # Add the paragraph for the horizontal line
    paragraph = doc.add_paragraph()
    run = paragraph.add_run()

    # Set the paragraph formatting
    paragraph_format = paragraph.paragraph_format
    paragraph_format.space_before = Pt(0)  # Set space before to 0
    paragraph_format.space_after = Pt(0)   # Set space after to 0

    # Add the border element for the bottom border
    p = paragraph._element
    pPr = p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '0')  # Adjust line size if needed
    bottom.set(qn('w:space'), '0')  # Set space to 0 for no extra spacing
    bottom.set(qn('w:color'), 'auto')
    pBdr.append(bottom)
    pPr.append(pBdr)

    # Remove any space before and after the paragraph
    pPr.remove(pPr.find(qn('w:spacing')))

def create_chart(doc, buffer_slippage, buffer_line_chart):
    # Add Performance Analysis section title
    add_paragraph(doc, "2. Average Cost Savings and Excess Returns Over Time By Strategy", font_size=HEADING_FONT_SIZE, bold=True, space_before=Pt(14))

    # Ensure 'charts' directory exists
    if not os.path.exists('charts'):
        os.makedirs('charts')

    # Create a table to hold the image and text side by side
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    table.allow_autofit = False

    # Add chart image to the first cell
    cell1 = table.cell(0, 0)
    paragraph1 = cell1.paragraphs[0]
    run1 = paragraph1.add_run()
    run1.add_picture(buffer_slippage, width=Inches(3.5), height=Inches(2.0))

    # Add descriptive text to the second cell
    cell2 = table.cell(0, 1)
    paragraph2 = cell2.paragraphs[0]
    run2 = paragraph2.add_run()
    run2.add_picture(buffer_line_chart, width=Inches(3.5), height=Inches(1.8))

    # Set font properties for both images
    font1 = run1.font
    font1.name = FONT_NAME
    font1.size = DEFAULT_FONT_SIZE

    font2 = run2.font
    font2.name = FONT_NAME
    font2.size = DEFAULT_FONT_SIZE

    # Adjust space before for the second paragraph
    paragraph2.paragraph_format.space_before = Pt(14)  # Adjust this value as needed

    # Add a small gap between the images
    paragraph2.paragraph_format.space_before = Pt(10)  # Adjust this value to move the picture down

def add_paragraph_with_bold_text(doc, text, bold_text_template, align=None, font_size=None, bold=False, space_before=None, underline=None, color=None, bullet=False, left_indent=None, **kwargs):
    # Replace placeholders in the text with provided values
    for key, value in kwargs.items():
        text = text.replace(f"{{{key}}}", str(value))
        bold_text_template = bold_text_template.replace(f"{{{key}}}", str(value))

    paragraph = doc.add_paragraph()
    
    if left_indent:
        paragraph_format = paragraph.paragraph_format
        paragraph_format.left_indent = left_indent

    # Split the text into the bold part and the remaining part
    bold_text_length = len(bold_text_template)
    run_bold = paragraph.add_run(bold_text_template)
    run_bold.bold = True
    run_bold.font.size = font_size if font_size else DEFAULT_FONT_SIZE
    run_bold.font.name = FONT_NAME

    run_normal = paragraph.add_run(text[bold_text_length:])
    run_normal.bold = False
    run_normal.font.size = font_size if font_size else DEFAULT_FONT_SIZE
    run_normal.font.name = FONT_NAME

    if align:
        paragraph.alignment = align

    if space_before is not None:
        paragraph.space_before = space_before

    if underline is not None:
        run_normal.font.underline = underline

    if color is not None:
        run_normal.font.color.rgb = RGBColor(*color)

    if bullet:
        paragraph.style = 'ListBullet'

    return paragraph
   
def add_timeframe_analyzed(doc, start_date, end_date):
    text = f"The data analyzed is from {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}."
    add_paragraph_with_bold_text(doc, text, "Time Frame Analyzed: ", font_size=DEFAULT_FONT_SIZE, bold=True)

# Example usage

def add_table(doc, table_data):
    headers = ["Date", "Direction", "Stock", "Executed Price", "TWAP Price", "Slippage", "Order Size", "Market Condition"]

    table = doc.add_table(rows=1, cols=len(headers))

    # Set table style
    table.style = 'Table Grid'

    # Add headers to the table
    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        run = cell.paragraphs[0].runs[0]
        run.bold = True
        run.font.size = Pt(10)
        run.font.name = FONT_NAME
        set_cell_border(cell, 
                top={"sz": 12, "val": "single", "color": "000000"},
                bottom={"sz": 12, "val": "single", "color": "000000"},
                start={"sz": 12, "val": "single", "color": "000000"},
                end={"sz": 12, "val": "single", "color": "000000"},)

    # Add rows to the table
    for row_data in table_data:
        cells = table.add_row().cells
        for i, header in enumerate(headers):
            cell = cells[i]
            value = row_data[header]
            if header in ["Executed Price", "TWAP Price", "Slippage"]:  # Columns that need formatting
                try:
                    # Remove any non-numeric characters like $, % etc.
                    cleaned_value = ''.join(filter(lambda x: x.isdigit() or x == '.', value))
                    value = f"{float(cleaned_value):.2f}"  # Format to 2 decimal places
                    if "%" in row_data[header]:
                        value += "%"
                    elif "$" in row_data[header]:
                        value = "$" + value
                except ValueError:
                    pass  # If value cannot be converted to float, leave it as is
            cell.text = value
            run = cell.paragraphs[0].runs[0]
            run.font.size = Pt(10)
            run.font.name = FONT_NAME
            set_cell_border(cell, 
                top={"sz": 12, "val": "single", "color": "000000"},
                bottom={"sz": 12, "val": "single", "color": "000000"},
                start={"sz": 12, "val": "single", "color": "000000"},
                end={"sz": 12, "val": "single", "color": "000000"},
                                 )

    table.autofit = False
    for col in table.columns:
        for cell in col.cells:
            if cell.text == "Market Condition":
                cell.width = Inches(2.0)  # Set a larger width for the "Market Condition" column
            else:
                cell.width = Inches(1.0)  
    return table

def add_backtesting_results_table(doc, backtesting_data):
    # Define table data
    headers = [
        "Strategy",
        "Your Average BUY Price",
        "Average Strategy Buy Price",
        "Your Average SELL Price",
        "Average Strategy Sell Price",
        "Total Savings"
    ]

    # Add the table to the document
    table = doc.add_table(rows=1, cols=len(headers))

    # Add headers to the table
    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        run = cell.paragraphs[0].runs[0]
        run.bold = True
        cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        run.font.size = DEFAULT_FONT_SIZE
        run.font.name = FONT_NAME

    # Add data rows to the table
    for row in backtesting_data:
        row_cells = table.add_row().cells
        row_data = [
            row["Strategy"],
            row["Your Average BUY Price"],
            row["Average Strategy Buy Price"],
            row["Your Average SELL Price"],
            row["Average Strategy Sell Price"],
            row["Total Savings"]
        ]
        for i, cell_data in enumerate(row_data):
            cell = row_cells[i]
            cell.text = str(cell_data)
            run = cell.paragraphs[0].runs[0]
            cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            run.font.size = DEFAULT_FONT_SIZE
            run.font.name = FONT_NAME

    # Set cell borders
    for row in table.rows:
        for cell in row.cells:
            set_cell_border(cell,
                top={"sz": 12, "val": "single", "color": "000000"},
                bottom={"sz": 12, "val": "single", "color": "000000"},
                start={"sz": 12, "val": "single", "color": "000000"},
                end={"sz": 12, "val": "single", "color": "000000"},
            )

    table.style = 'Table Grid'

def add_paragraph_with_value_bold(doc, text, bold_text, space_before=None):
    p = doc.add_paragraph()
    if space_before:
        p.paragraph_format.space_before = space_before
    
    # Split the text into parts
    parts = text.split(str(bold_text))
    
    # Add the first part
    if parts[0]:
        run = p.add_run(parts[0])
        run.font.name = FONT_NAME
        run.font.size = DEFAULT_FONT_SIZE
    
    # Add the bold text
    # Add the bold text
    run_bold = p.add_run(str(bold_text))
    run_bold.bold = True
    run_bold.font.name = FONT_NAME
    run_bold.font.size = DEFAULT_FONT_SIZE
    
    # Add the remaining part
    if parts[1]:
        run = p.add_run(parts[1])
        run.font.name = FONT_NAME
        run.font.size = DEFAULT_FONT_SIZE

def generate_report(report_calculation):
    
    # start_date = datetime(2022, 8, 17)
    start_date = report_calculation['trading_overview']['start_date']
    # end_date = datetime(2024, 5, 7)
    end_date = report_calculation['trading_overview']['end_date']
    
    
    #dynamic timeframe
    # delta = end_date - start_date
    # total_days = delta.days
    # total_days = round(total_days/30,1)
    
    
    
    # Placeholder values
    # assets_analyzed = ['V', 'NFLX', 'META', 'NVDA', 'AMZN', 'AAPL', 'GOOGL', 'BABA', 'TSLA', 'MSFT']
    assets_analyzed = report_calculation['trading_overview']['assets_analyzed']
    # total_trades = "9,876"
    total_trades = report_calculation['trading_overview']['total_trades']
    # average_trades_per_month = "6.681818181818182"
    average_trades_per_month = report_calculation['trading_overview']['trades_per_month']
    # average_trades_per_week = "1.6359300476947536"
    average_trades_per_week = report_calculation['trading_overview']['trades_per_week']

    rounded_avg_monthly = round(float(average_trades_per_month), 1)
    rounded_avg_weekly = round(float(average_trades_per_week), 1)

    # Average_Order_Size= "17"
    Average_Order_Size= report_calculation['trading_overview']['avg_order_size']
    # Average_Trading_Day= "Friday"
    Average_Trading_Day= report_calculation['actionable_recommendations']['average_trading_day']
    # Average_Trading_Time ="09:03:00"
    Average_Trading_Time =report_calculation['actionable_recommendations']['average_trading_time']

    # Final report of top stocks including buy and sell limit
    Final_Report_Summary = report_calculation['actionable_recommendations']['final_report']

    # Average_First_stock ="NVDA"
    # First_Stock_Buy_Limit="6.14"
    # First_Stock_Sell_Limit="6.58"

    # Average_Second_stock ="V"
    # Second_Stock_Buy_Limit="0.63"
    # Second_Stock_Sell_Limit="0.87"

    # Average_Third_stock ="TSLA"
    # Third_Stock_Buy_Limit="1.77"
    # Third_Stock_Sell_Limit="1.74"

    # Average_Forth_stock ="META"
    # Forth_Stock_Buy_Limit="2.80"
    # Forth_Stock_Sell_Limit="2.05"

    # Average_Fifth_stock ="BABA"
    # Fifth_Stock_Buy_Limit="3.62"
    # Fifth_Stock_Sell_Limit="5.27"

    # Average_Optimal_Strategy ="$152479.89"
    Average_Optimal_Strategy =report_calculation['calculate_potential_savings']['total_savings']

    # table_data = [
    #     {
    #         "Date": "2022-12-15",
    #         "Direction": "sell",
    #         "Stock": "BABA",
    #         "Executed Price": "$93.089996",
    #         "TWAP Price": "$87.382142",
    #         "Slippage": "0.065321%",
    #         "Order Size": "20 shares",
    #         "Market Condition": "High Volume, Sideways, Medium Volatility"
    #     },
    #     {
    #         "Date": "2024-02-06",
    #         "Direction": "buy",
    #         "Stock": "TSLA",
    #         "Executed Price": "$177.210007",
    #         "TWAP Price": "$183.506971",
    #         "Slippage": "0.034315%",
    #         "Order Size": "14 shares",
    #         "Market Condition": "Medium Volume, Upward Momentum, Low Volatility"
    #     },
    #     {
    #         "Date": "2023-05-17",
    #         "Direction": "buy",
    #         "Stock": "TSLA",
    #         "Executed Price": "$168.410004",
    #         "TWAP Price": "$173.255585",
    #         "Slippage": "0.027968%",
    #         "Order Size": "13 shares",
    #         "Market Condition": "High Volume, Downward Momentum, Medium Volatility"
    #     },
    #     {
    #         "Date": "2023-02-02",
    #         "Direction": "buy",
    #         "Stock": "NVDA",
    #         "Executed Price": "$21.000000",
    #         "TWAP Price": "$21.534178",
    #         "Slippage": "0.024806%",
    #         "Order Size": "5 shares",
    #         "Market Condition": "Medium Volume, Downward Momentum, Medium Volatility"
    #     },
    #     {
    #         "Date": "2024-05-01",
    #         "Direction": "sell",
    #         "Stock": "NVDA",
    #         "Executed Price": "$85.077003",
    #         "TWAP Price": "$83.242783",
    #         "Slippage": "0.022035%",
    #         "Order Size": "1 share",
    #         "Market Condition": "High Volume, Upward Momentum, Medium Volatility"
    #     }
    # ]

    table_data = report_calculation['trades_most_slippage']

    backtesting_data = report_calculation['calculate_potential_savings']['potential_saving_table']
    # backtesting_data = [
    #     ["Open", "$188.94", "$188.89", "$186.28", "$186.11", "$125.56"],
    #     ["Close", "$188.94", "$189.08", "$186.28", "$186.40", "$71.59"],
    #     ["TWAP", "$188.94", "$188.74", "$186.28", "$186.16", "$152.61"],
    #     ["VWAP", "$188.94", "$188.75", "$186.28", "$186.19", "$172.37"],
    #     ["HWOE", "$188.94", "$183.15", "$186.28", "$193.08", "$15981.06"]
    # ]
    # Create a Word document
    doc = Document()

    # Set page orientation to landscape
    section = doc.sections[0]
    new_width, new_height = section.page_height, section.page_width
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = new_width
    section.page_height = new_height

    # Add title
    add_paragraph(doc, 'Trade Like a Pro with Your Hoodwinked Execution Report', font_size=HEADING_FONT_SIZE, bold=True)

    # Add introduction
    delta = end_date - start_date
    total_days = delta.days
    total_days = int(total_days)
    if total_days <=30:
        total_days = round(total_days/30,1)
        add_paragraph_with_value_bold(doc, f"Based on an analysis of your stock trades over the last {total_days} months, you could have saved {Average_Optimal_Strategy} in trading costs by using Hoodwinked Optimal Execution (HWOE) Strategy. Read our report and find out how", Average_Optimal_Strategy, space_before=Pt(3))
    else:
        total_days = round(total_days/365,1)
        add_paragraph_with_value_bold(doc, f"Based on an analysis of your stock trades over the last {total_days} years, you could have saved {Average_Optimal_Strategy} in trading costs by using Hoodwinked Optimal Execution (HWOE) Strategy. Read our report and find out how", Average_Optimal_Strategy, space_before=Pt(3))
        

    add_horizontal_line(doc)
    
    # Add Trading Overview
    add_paragraph(doc, "1. An Overview of Your Trades", font_size=HEADING_FONT_SIZE, bold=True, space_before=Pt(6))
    add_timeframe_analyzed(doc, start_date, end_date)
    # Example usage in report generation
    add_paragraph_with_bold_text(doc, "Assets analyzed: {assets}", "Assets analyzed:", space_before=Pt(6), assets=", ".join(assets_analyzed))
    add_paragraph_with_bold_text(doc, "Frequency of trading: {total} trades in total, with an average of {avg_monthly} trades per month and {avg_weekly} trades per week", "Frequency of trading:", space_before=Pt(6), total=total_trades, avg_monthly=rounded_avg_monthly, avg_weekly=rounded_avg_weekly)
    add_paragraph_with_bold_text(doc, "Average order size: {order_size} shares", "Average order size:", space_before=Pt(6), order_size=Average_Order_Size)

    # Add section separator
    add_horizontal_line(doc)

    # Add Performance Analysis
    create_chart(doc, report_calculation['generate_buffer_slippage'], report_calculation['generate_buffer_line_chart'])
    add_paragraph(doc, '(see FAQ section for further explanation on charts)', space_before=Pt(3))

    # Add Actionable Recommendations
    add_paragraph(doc, "3. Trading Recommendations Snapshot", font_size=HEADING_FONT_SIZE, bold=True, space_before=Pt(6))
    add_paragraph_with_bold_text(doc, "Optimal Timings: Based on our analysis of the stocks you trade, the time segment in which you will receive the best trading execution are {trading_day} at {trading_time}", "Optimal Timings: ", bullet=True, space_before=Pt(6), trading_day=Average_Trading_Day, trading_time=Average_Trading_Time)
    add_paragraph_with_bold_text(doc, "Use Limit Orders When Possible: Based on a backtest of your data, we found the optimal buy and sell limits for a couple stocks based on the 5 day moving average of the close:", "Use Limit Orders When Possible:", bullet=True, space_before=Pt(6))
    # add_paragraph_with_bold_text(doc, "{first_stock} – Set BUY limit for {first_buy_time}% below 5 day MA, SELL limit {first_sell_time}% above", "{first_stock}", bullet=True, space_before=Pt(6), left_indent=Inches(0.5), first_stock=Average_First_stock, first_buy_time=First_Stock_Buy_Limit, first_sell_time=First_Stock_Sell_Limit )
    # add_paragraph_with_bold_text(doc, "{second_stock} – Set BUY limit for {second_buy_time}% below 5 day MA, SELL limit {second_sell_time}% above", "{second_stock}", bullet=True, space_before=Pt(6), left_indent=Inches(0.5), second_stock=Average_Second_stock, second_buy_time=Second_Stock_Buy_Limit, second_sell_time=Second_Stock_Sell_Limit )
    # add_paragraph_with_bold_text(doc, "{third_stock} – Set BUY limit for {third_buy_time}% below 5 day MA, SELL limit {third_sell_time}% above", "{third_stock}", bullet=True, space_before=Pt(6), left_indent=Inches(0.5), third_stock=Average_Third_stock, third_buy_time=Third_Stock_Buy_Limit, third_sell_time=Third_Stock_Sell_Limit )
    # add_paragraph_with_bold_text(doc, "{forth_stock} – Set BUY limit for {forth_buy_time}% below 5 day MA, SELL limit {forth_sell_time}% above", "{forth_stock}", bullet=True, space_before=Pt(6), left_indent=Inches(0.5), forth_stock=Average_Forth_stock, forth_buy_time=Forth_Stock_Buy_Limit, forth_sell_time=Forth_Stock_Sell_Limit )
    # add_paragraph_with_bold_text(doc, "{fifth_stock} – Set BUY limit for {fifth_buy_time}% below 5 day MA, SELL limit {fifth_sell_time}% above", "{fifth_stock}", bullet=True, space_before=Pt(6), left_indent=Inches(0.5), fifth_stock=Average_Fifth_stock, fifth_buy_time=Fifth_Stock_Buy_Limit, fifth_sell_time=Fifth_Stock_Sell_Limit )
    # Generate paragraphs for each stock
    for stock in Final_Report_Summary:
        add_paragraph_with_bold_text(
            doc, 
            "{ticker} – Set BUY limit for {buy_limit}% below 5 day MA, SELL limit {sell_limit}% above", 
            "{ticker}", 
            bullet=True, 
            space_before=Pt(6), 
            left_indent=Inches(0.5), 
            ticker=stock["ticker"], 
            buy_limit=stock["buy_limit"], 
            sell_limit=stock["sell_limit"]
        )
    add_paragraph(doc, 'Above we analyzed your past trades and based on our algorithm, have recommended limit orders that would have maximized your trading returns. For real time limit order recommendations, please sign up for our Hoodwinked Pro Product.', space_before=Pt(3))

    # Add section separator
    add_horizontal_line(doc)


    # Add Top 5 Trades With Slippage
    add_paragraph(doc, "4. Potential Savings  from Using Different Execution Strategies", font_size=HEADING_FONT_SIZE, bold=True, space_before=Pt(12))
    add_backtesting_results_table(doc, backtesting_data)

     # Add section separator
    add_horizontal_line(doc)

    add_paragraph(doc, "5. Your Top 5 Trades with the Worst Executions", font_size=HEADING_FONT_SIZE, bold=True, space_before=Pt(12))
    add_table(doc, table_data)
    
     # Add section separator
    add_horizontal_line(doc)
    
   
    # Add Backtesting Results and Potential Savings
    add_paragraph(doc, "6. How Can I Use Your Analytics to Improve My Trades?", font_size=HEADING_FONT_SIZE, bold=True, space_before=Pt(12))
    add_paragraph(doc, "For personalized assistance and to start implementing these recommendations, please contact our support team. We are here to help you achieve better trading outcomes and maximize your profits. For options TCA, forward looking recommendations, and backtesting more complex execution strategies consider signing up for Hoodwinked Pro.", space_before=Pt(3))

    # Add section separator
    add_horizontal_line(doc)

     # FAQ section 
    add_paragraph(doc, "Frequently Asked Questions (FAQ) Section", font_size=HEADING_FONT_SIZE, align=WD_PARAGRAPH_ALIGNMENT.CENTER, bold=True, space_before=Pt(12))

    add_paragraph(doc, "Why should I care about trade execution?", font_size=HEADING_FONT_SIZE, bold=True, space_before=Pt(6))
    add_paragraph(doc, "There are two things that affect your trading returns, the investment idea you have (alpha) and how you BUY / SELL the asset. If you put a large market order in at one time, or put in orders when markets are highly volatile, then there is a good chance you could be eating into your trading returns with bad trade prices. Save your hard-earned alpha by executing your trades at the right timing, sizing, and order type. In this report, we compare your trades to four different execution strategies for the same stocks within the same week, over the last two years of trades, and show you how much excess returns you could have made by planning and trading in different ways.", space_before=Pt(6))

    add_paragraph(doc, "What is slippage, and what do Open, Close, TWAP, VWAP, and HWOE mean?", font_size=HEADING_FONT_SIZE, bold=True, space_before=Pt(6))
    add_paragraph_with_bold_text(doc, "Slippage is the word used by traders to describe the difference in your expected price and the price you traded at. In this report, we are comparing your trade prices to the prices you would expect with different execution strategies. The slippage for a BUY = your_price – strategy_price, and the slippage for SELL = strategy_price – your_price. With these formulas a positive value means that the strategy_price was better than your execution (your BUY was higher than strategy BUY, your SELL was lower than strategy sell)", "Slippage", space_before=Pt(6))
    add_paragraph(doc, "The charts and values we are displaying in this report are the difference (slippage) between YOUR trade prices and 5 different strategies. Open and Close represent the strategy of buying at market “Open” or “Close” on the same day you traded. TWAP represents the strategy of splitting your order into equal size pieces and buying that many shares at the start of every hour during the same day you traded. VWAP is similar to TWAP, but instead of equal size pieces, the size of each individual order gets adjusted depending on how much volume is expected to be traded that hour (more volume expected means larger chunk is traded). The HWOE strategy represents our own algorithm, which chooses the best time during the week you traded to perform the trade, and splits order sizes depending on a host of different market liquidity factors. As displayed in the charts in section 2, HWOE does far better than TWAP / VWAP on an average trade basis, and results in significant trade savings over time.", space_before=Pt(6))

    # Add section separator
    add_horizontal_line(doc)
   
    # Save the document
    # doc.save('report_hoodwinked_landscape.docx')
    # Save the document to a BytesIO object
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # Create an HTTP response with the document
    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename=report_hoodwinked_landscape.docx'
    
    return response

# Generate the report
# generate_report()
