from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from io import BytesIO
import base64
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from Analytics.utils import reportCalculation
from Analytics.models import UploadHoodWinked
from reportlab.lib.utils import ImageReader
import boto3
from django.conf import settings
import pandas as pd
from io import StringIO
from reportlab.lib.colors import HexColor
from io import BytesIO
import tempfile
import os
from datetime import datetime, timedelta


pdfmetrics.registerFont(TTFont('CraftworkGrotesk-Bold', 'Analytics/fonts/CraftworkGrotesk-Bold.ttf'))
pdfmetrics.registerFont(TTFont('CraftworkGrotesk-Regular', 'Analytics/fonts/CraftworkGrotesk-Regular.ttf'))
pdfmetrics.registerFont(TTFont('CraftworkGrotesk-SemiBold', 'Analytics/fonts/CraftworkGrotesk-SemiBold.ttf'))
pdfmetrics.registerFont(TTFont('CraftworkGrotesk-Medium', 'Analytics/fonts/CraftworkGrotesk-Medium.ttf'))

class ImageWithBox2(Flowable):
    def __init__(self, image_data, width, height, padding=30):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.padding = padding

        if isinstance(image_data, BytesIO):
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                tmp_file.write(image_data.getvalue())
                tmp_file_path = tmp_file.name

            # Use the temporary file path for the Image
            self.img = Image(tmp_file_path, width=width-2*padding, height=height-2*padding)
            
            # Schedule the temporary file for deletion
            self._tmp_file_path = tmp_file_path
        else:
            self.img = Image(image_data, width=width-2*padding, height=height-2*padding)
            self._tmp_file_path = None

    def draw(self):
        self.canv.rect(0, 0, self.width, self.height)
        self.img.drawOn(self.canv, self.padding, self.padding)

    def __del__(self):
        # Clean up the temporary file if it exists
        if self._tmp_file_path and os.path.exists(self._tmp_file_path):
            os.unlink(self._tmp_file_path)

class ImageWithBox(Flowable):
    def __init__(self, image_path, width, height, padding=30):  # Added padding parameter
        Flowable.__init__(self)
        self.img = Image(image_path, width=width - 2 * padding, height=height - 2 * padding)  # Adjusted image size
        self.width = width
        self.height = height
        self.padding = padding  # Store padding value

    def draw(self):
        self.canv.rect(0, 0, self.width, self.height)
        self.img.drawOn(self.canv, self.padding, self.padding)  # Added padding to image position

def generate_report(report_calculation):
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        elements = []
        styles = getSampleStyleSheet()

        # Add content to the PDF (you'll need to implement this based on your report structure)
        elements.extend(create_report_content(report_calculation, styles, doc))
        # Build the PDF
        doc.build(elements)
        buffer.seek(0)

        #Upload the PDF to S3
        # s3 = boto3.client('s3',
        #                   aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        #                   aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        #                   region_name=settings.AWS_REGION)
        # s3_file_name = f"reports/trade_report_{file_id}.pdf"  # Unique file name
        # s3.upload_fileobj(buffer, settings.AWS_STORAGE_BUCKET, s3_file_name)

        # # Generate the S3 link
        # s3_link = f"https://{settings.AWS_STORAGE_BUCKET}.s3.amazonaws.com/{s3_file_name}"
        
        # 5. Download pdf directly
        # Create the HTTP response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="trade_report.pdf"'
        response.write(buffer.getvalue())

        # response = JsonResponse({'report_link': s3_link}, status=200)

        buffer.close()
        
        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def fetch_file_from_s3(file_id):
    try:
        upload = UploadHoodWinked.objects.get(id=file_id)
        s3 = boto3.client('s3',
                          aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                          region_name=settings.AWS_REGION)
        user_folder = str(upload.user_email)
        s3_file_path = f"hoodwinked/app/{user_folder}/{upload.file_name}"
        obj = s3.get_object(Bucket=settings.AWS_STORAGE_BUCKET, Key=s3_file_path)
        file_content = obj['Body'].read().decode('utf-8')
        df = pd.read_csv(StringIO(file_content))
        return df
    except Exception as e:
        print(f"Error fetching file from S3: {str(e)}")
        return None

def create_report_content(report_calculation, styles, doc):
    # start_date = datetime(2022, 8, 17)
    start_date = report_calculation['trading_overview']['start_date']
    # end_date = datetime(2024, 5, 7)
    end_date = report_calculation['trading_overview']['end_date']
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
    
    # Average_Optimal_Strategy ="$152479.89"
    Average_Optimal_Strategy =report_calculation['calculate_potential_savings']['total_savings']

    
    table_data = report_calculation['trades_most_slippage']

    backtesting_data = report_calculation['calculate_potential_savings']['potential_saving_table']
    
    # Add introduction
    delta = end_date - start_date
    total_days = delta.days
    total_days = int(total_days)

    elements = []

    # Modify the existing 'Title' and 'Normal' styles
    title_style = styles['Title']
    title_style.fontSize = 40
    title_style.leading = 40

    normal_style = styles['Normal']
    normal_style.fontSize = 12
    normal_style.leading = 14

    title_style.fontName = 'CraftworkGrotesk-Bold'
    normal_style.fontName = 'CraftworkGrotesk-SemiBold'
    
    # Add custom styles if needed
    styles.add(ParagraphStyle(name='Subtitle', fontSize=18, leading=22))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Spacer(1, 0.2*inch))
    # Title
    # Add custom styles if needed
    title_style2 = ParagraphStyle('title_style2', parent=styles['Title'], fontSize=32, leading=32 , alignment=1)  # 1 for center alignment
    title_style3 = ParagraphStyle('title_style3', parent=styles['Title'], fontSize=32, leading=32, alignment=1)

    # ________________________-_________________________- PAGE 1 - __________________________________________________________
    
    # Create data for the table For Header
    data = [
        [Paragraph('Trade Like a Pro with', title_style)],  # First row
        [Paragraph('Your <img src="Analytics/images/hoodwinked-logo-pdf.png" width="277" height="53"></img>', title_style)],
        [Paragraph('Execution Report', title_style)],  # second row
    ]

    # Create the table with the rows in a single column
    table = Table(data, colWidths=[10*inch, None])  # Set a wide column width to fit all text

    # Define the style of the table to add padding and other styling options
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align text in the middle
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Vertically align text in the middle
        ('LEAING', (0, 0), (0, 0), 40),  # Vertically align text in the middle
        ('LEADING', (0, 1), (0, 1), 40),  # Vertically align text in the middle
        ('TOPPADDING', (0, 1), (0, 1), 0),  # Vertically align text in the middle
        ('TOPPADDING', (0, 2), (0, 2), 0),  # Vertically align text in the middle
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))
    # Introduction
    intro_text = f"Based on an analysis of your stock trades over the last {total_days} months, you could have saved {Average_Optimal_Strategy} in trading costs by using Hoodwinked Optimal Execution (HWOE) Strategy. Read our report and find out how ->"
    normal_style.fontSize = 16  # Updated font size to 16 px
    normal_style.leading = 16    # Updated line height to 16 px
    normal_style.alignment = 1   # Center alignment
    elements.append(Paragraph(intro_text, normal_style))
    elements.append(Spacer(1, 1*inch))

    # Add generation date and source side by side
    generation_style = ParagraphStyle('Generation', 
                                      fontName='CraftworkGrotesk-Medium', 
                                      fontSize=10, 
                                      textColor=colors.black,
                                      alignment=1)  # Center alignment
    generation_date = datetime.now().strftime("%d %b, %Y")
    generation_text = f"Generated on {generation_date}"
    source_text = "Generated by <u><a href='https://hoodwinkedtrades.com'>hoodwinked.trades</a></u>"  # Made underlined and linked
    
    # ________________________-_________________________- PAGE 2 - __________________________________________________________
    
    # Create a table to hold the date and source side by side
    generation_table = Table([[Paragraph(generation_text, generation_style), 
                                Paragraph(source_text, generation_style)]], 
                             colWidths=[4*inch, 4*inch])  # Adjust widths as needed
    elements.append(generation_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # add image here
    img_path = 'Analytics/images/pdf-first-image.png'  # Replace with actual path to your image
    img_width, img_height = 480, 319.3
    img_with_box = ImageWithBox(img_path, img_width, img_height)
    elements.append(img_with_box)
    
    elements.append(Spacer(1, 0.2*inch))

    # New page content
    # Add custom styles if needed
    styles.add(ParagraphStyle(name='Subtitle30', fontSize=30, leading=30, fontName='CraftworkGrotesk-Bold', alignment=1))  # New subtitle style with center alignment
    elements.append(Paragraph('An <font  backcolor="#C3F53C">&nbsp;Overview&nbsp;</font> of Your Trades', styles['Subtitle30']))  # Use new subtitle style
    elements.append(Spacer(1, 0.2*inch))

    # Function to create a box with content
    def create_box(title, content, width):
        box_style = ParagraphStyle(
            'BoxStyle',
            parent=styles['Normal'],
            fontName='CraftworkGrotesk-SemiBold',
            fontSize=12,
            leading=14,
            alignment=0,  # Left alignment
        )

        content_style = ParagraphStyle(
            'BoxStyle',
            parent=styles['Normal'],
            fontName='CraftworkGrotesk-Medium',
            fontSize=12,
            leading=14,
            alignment=0,  # Left alignment
        )
        
        # Set a maximum width for the content
        max_content_width = width  # Adjust as needed for padding
        content_paragraph = Paragraph(content, content_style)
        content_paragraph.wrap(max_content_width, 0)  # Set height to 0 for dynamic height

        # Calculate dynamic height based on content
        dynamic_height = content_paragraph.height

        # Add condition to adjust height if content length exceeds a certain limit
        if len(content) > 100:  # Adjust the threshold as needed
            dynamic_height = content_paragraph.height / 2  # Halve the height if content is too long
        
        if content_paragraph.height > 700 :
            # only show part of the content
            content_paragraph = Paragraph(content[:700], content_style)

        box = Table([
            [Paragraph(f'<font  backcolor="#C3F53C">&nbsp;{title}&nbsp;</font>', box_style)],
            [content_paragraph]
        ], colWidths=[None], rowHeights=[30, dynamic_height + 15])  # Use dynamic height
        
        box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#FFFFFF')),
            ('BOX', (0, 0), (-1, -1), 1, HexColor('#000000')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 15),  # Added uniform padding for all sides
        ]))
        return box

    # Function to create a box with content
    def create_box2(title, content, width, height):
        box_style = ParagraphStyle(
            'BoxStyle',
            parent=styles['Normal'],
            fontName='CraftworkGrotesk-SemiBold',
            fontSize=12,
            leading=14,
            alignment=0,  # Left alignment
        )

        content_style = ParagraphStyle(
            'BoxStyle',
            parent=styles['Normal'],
            fontName='CraftworkGrotesk-Medium',
            fontSize=12,
            leading=14,
            alignment=0,  # Left alignment
        )
        
        # Set a maximum width for the content
        max_content_width = width - 20  # Adjust as needed for padding
        content_paragraph = Paragraph(content, content_style)
        content_paragraph.wrap(max_content_width, 0)  # Set height to 0 for dynamic height

        # Calculate dynamic height based on content
        dynamic_height = content_paragraph.height

        # Add condition to adjust height if content length exceeds a certain limit
        if len(content) > 100:  # Adjust the threshold as needed
            dynamic_height = content_paragraph.height / 2.5  # Halve the height if content is too long

        if len(title)  > 0:
            box = Table([
                [Paragraph(title, box_style)],
                [content_paragraph]
            ], colWidths=[None], rowHeights=[40, dynamic_height + 20])  # Use dynamic height
        else :
            box = Table([
                [content_paragraph]
                ], colWidths=[None], rowHeights=[dynamic_height + 40])  # Use dynamic height
        
        box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#FFFFFF')),
            ('BOX', (0, 0), (-1, -1), 1, HexColor('#000000')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 15),  # Uniform padding for all sides inside the box
            ('LEFTPADDING', (0, 0), (-1, -1), 20),  # Extra left padding between box and content
            ('RIGHTPADDING', (0, 0), (-1, -1), 20),  # Extra right padding between box and content
            ('TOPPADDING', (0, 0), (-1, -1), 50),  # Extra top padding between box and content
            ('BOTTOMPADDING', (0, 0), (-1, -1), 50),  # Extra bottom padding between box and content
        ]))
        return box

    # Create boxes
    box_width = 2.5 * inch
    # Create boxes without fixed height
    box1 = create_box('Time Frame Analyzed', f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}", box_width)
    box2 = create_box('Average Order Size', f'{Average_Order_Size} shares', box_width)
    box3 = create_box('Assets Analyzed', ', '.join(assets_analyzed), box_width)  # Join array elements with a comma
    box4 = create_box('Frequency of Trading', f'{total_trades} trades in total, with an average of {rounded_avg_monthly} trades per month and {rounded_avg_weekly} trades per week.', box_width)
    # Add boxes vertically
    elements.append(box1)
    elements.append(Spacer(1, 0.2*inch))  # Add space between boxes
    elements.append(box2)
    elements.append(Spacer(1, 0.2*inch))  # Add space between boxes
    elements.append(box3)
    elements.append(Spacer(1, 0.2*inch))  # Add space between boxes
    elements.append(box4)

    #go to next page
    elements.append(PageBreak())

    styles.add(ParagraphStyle(name='Footer', fontSize=16, leading=16))
    styles.add(ParagraphStyle(name='table_header', fontSize=12, leading=12))
    styles.add(ParagraphStyle(name='table_header_small', fontSize=10, leading=10))
    
    # __________________________- Styles - _________________
    title_style = styles['Title']
    footer_style = styles['Footer']
    table_header = styles['table_header']
    table_header_small = styles['table_header_small']
    table_header.alignment = 1
    table_header_small.alignment = 1
    title_style.fontSize = 32
    title_style.leading = 40
    title_style.color = "#101010"
    footer_style.color = "#101010"
    
    normal_style = styles['Normal']
    normal_style.fontSize = 16
    normal_style.leading = 20
    normal_style.alignment=0
    normal_style.color = "#101010"

    title_style.fontName = 'CraftworkGrotesk-Bold'
    footer_style.fontName = 'CraftworkGrotesk-Bold'
    normal_style.fontName = 'CraftworkGrotesk-SemiBold'
    table_header.fontName = 'CraftworkGrotesk-Bold'
    table_header_small.fontName = 'CraftworkGrotesk-Bold'

    # ________________________-_________________________- PAGE 3 - __________________________________________________________
        
    # Create data for the table For Header
    data = [
        [Paragraph('Average<font  backcolor="#C3F53C">&nbsp;Cost Savings&nbsp;</font>and', title_style)],  # First row
        [Paragraph('Excess Returns Over Time', title_style2)],  # second row
        [Paragraph('By Strategy', title_style3)],  # Third row
    ]

    # Create the table with the rows in a single column
    table = Table(data, colWidths=[10*inch])  # Set a wide column width to fit all text

    # Define the style of the table to add padding and other styling options
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align text in the middle
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Vertically align text in the middle
        ('LEAING', (0, 0), (0, 0), 40),  # Vertically align text in the middle
        ('LEADING', (0, 1), (0, 1), 32),  # Vertically align text in the middle
        ('TOPPADDING', (0, 1), (0, 1), -7),  # Vertically align text in the middle
        ('TOPPADDING', (0, 2), (0, 2), -2),  # Vertically align text in the middle
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))

    # add these two images in the table report_calculation['generate_buffer_slippage'], report_calculation['generate_buffer_line_chart']
    img_width, img_height = 450, 250

    if isinstance(report_calculation['generate_buffer_slippage'], BytesIO):
        img_with_box = ImageWithBox2(report_calculation['generate_buffer_slippage'], img_width, img_height)
        elements.append(img_with_box)
    else:
        print('Skipping image append: generate_buffer_slippage is not a BytesIO object')

    
    elements.append(Spacer(1, 0.2*inch))

    if isinstance(report_calculation['generate_buffer_line_chart'], BytesIO):
        img_with_box = ImageWithBox2(report_calculation['generate_buffer_line_chart'], img_width, img_height)
        elements.append(img_with_box)
    else:
        print('Skipping image append: generate_buffer_line_chart is not a BytesIO object')

    elements.append(Spacer(1, 0.1*inch))
    footer_style.fontSize = 16
    footer_style.alignment = 1
    footer = Paragraph("(see FAQ section for further explanation on charts)", footer_style)
        # Build the PDF and save it to the file path
    elements.append(footer)
    
    
    # ________________________-_________________________- PAGE 4 - __________________________________________________________
        #go to next page
    elements.append(PageBreak())

    #  Create data for the table For Header
    data = [
        [Paragraph('Trading<font  backcolor="#C3F53C">&nbsp;Recommendations&nbsp;</font>', title_style)],  # First row
        [Paragraph('Snapshot', title_style2)],  # second row
    ]

    # Create the table with the rows in a single column
    table = Table(data, colWidths=[10*inch])  # Set a wide column width to fit all text

    # Define the style of the table to add padding and other styling options
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align text in the middle
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Vertically align text in the middle
        ('LEAING', (0, 0), (0, 0), 40),  # Vertically align text in the middle
        ('LEADING', (0, 1), (0, 1), 32),  # Vertically align text in the middle
        ('TOPPADDING', (0, 1), (0, 1), -7),  # Vertically align text in the middle
        ('TOPPADDING', (0, 2), (0, 2), -2),  # Vertically align text in the middle
        # ('BACKGROUND', (0, 1), (0, 1), colors.HexColor('#C3F53C')),  # Add background color to the second row (highlighted)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    normal_style.fontSize = 12
      # Create data for the table For Header
    data = [
       [Paragraph(f"<font backcolor='#C3F53C' name = 'CraftworkGrotesk-Bold'>&nbsp;Optimal Timings:&nbsp; </font> Based on our analysis of the stocks you <br/> trade, the time segment in which you will receive the best <br/> trading execution are {Average_Trading_Day} at {Average_Trading_Time}",normal_style)]
    ]

    # Create the table with the rows in a single column
    table = Table(data, colWidths=[doc.width])  # Set a wide column width to fit all text

     # Add border around the table (i.e., box)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Add thick black grid line (border) around the table
        ('TOPPADDING', (0, 0), (0, 0), 20),  # Vertically align text in the middle
        ('BOTTOMPADDING', (0, -1), (0, -1), 20),  # Vertically align text in the middle
        ('LEFTPADDING', (0, 0), (0, -1), 20),  # Vertically align text in the middle
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align content in the middle
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Horizontally align content in the middle
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
      # Create data for the table For Header
    data = [
       [Paragraph(" <font backcolor='#C3F53C' name = 'CraftworkGrotesk-Bold'>&nbsp;Use Limit Orders When Possible:&nbsp; </font> Based on a backtest of <br/>your data, we found the optimal buy and sell limits for a <br/> couple stocks based on the 5 day moving average of the <br/> close:",normal_style)],
    ]

    for stock in Final_Report_Summary:
        data.append([Paragraph(f" <font backcolor='#C3F53C' name = 'CraftworkGrotesk-Bold'>&nbsp;{stock['ticker']}&nbsp;</font>– Set BUY limit for {stock['buy_limit']} below 5 day MA, SELL limit <br/> {stock['sell_limit']} above", normal_style)])

    # Create the table with the rows in a single column
    table = Table(data, colWidths=[doc.width])  # Set a wide column width to fit all text
    table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),  # Add a black border around the whole table
        ('TOPPADDING', (0, 0), (0, 0), 20),  # Vertically align text in the middle
        ('BOTTOMPADDING', (0, 5), (0, 5), 20),  # Vertically align text in the middle
        ('LEFTPADDING', (0, 0), (0, -1), 20),  # Vertically align text in the middle
        ('LEFTPADDING', (0, 1), (0, -1), 40),  # Vertically align text in the middle
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align content in the middle
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Horizontally align content in the middle
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
      # Create data for the table For Header
    data = [
       [Paragraph("Above we analyzed your past trades and based on our <br/> algorithm, have recommended limit orders that would <br/> have maximized your trading returns. For real time limit <br/> order recommendations, please sign up for our <br/> Hoodwinked Pro Product.",normal_style)]
    ]

    # Create the table with the rows in a single column
    table = Table(data, colWidths=[doc.width])  # Set a wide column width to fit all text

    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Add thick black grid line (border) around the table
        ('TOPPADDING', (0, 0), (0, 0), 20),  # Vertically align text in the middle
        ('BOTTOMPADDING', (0, -1), (0, -1), 20),  # Vertically align text in the middle
        ('LEFTPADDING', (0, 0), (0, -1), 20),  # Vertically align text in the middle
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align content in the middle
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Horizontally align content in the middle
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    elements.append(PageBreak())
    
    
    # ________________________-_________________________- PAGE 5 - __________________________________________________________
    
    # Create data for the table For Header
    data = [
        [Paragraph('Potential<font  backcolor="#C3F53C">&nbsp;Savings&nbsp;</font>from', title_style)],  # First row
        [Paragraph('Using Different Execution', title_style2)],  # second row
        [Paragraph('Strategies', title_style3)],  # Third row
    ]

    # Create the table with the rows in a single column
    table = Table(data, colWidths=[10*inch])  # Set a wide column width to fit all text

    # Define the style of the table to add padding and other styling options
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align text in the middle
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Vertically align text in the middle
        ('LEAING', (0, 0), (0, 0), 40),  # Vertically align text in the middle
        ('LEADING', (0, 1), (0, 1), 32),  # Vertically align text in the middle
        ('TOPPADDING', (0, 1), (0, 1), -7),  # Vertically align text in the middle
        ('TOPPADDING', (0, 2), (0, 2), -2),  # Vertically align text in the middle
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Create data for the table For Header
    data = [
        [
            Paragraph('Strategy', table_header),
            Paragraph('Your average buy price', table_header),
            Paragraph('Average strategy buy price', table_header),
            Paragraph('Your average sell price', table_header),
            Paragraph('Average strategy sell price', table_header),
            Paragraph('Total Savings', table_header),
           
        ],
    ]
    # Add data rows to the table
    for row in backtesting_data:
        row_data = [
            row["Strategy"],
            row["Your Average BUY Price"],
            row["Average Strategy Buy Price"],
            row["Your Average SELL Price"],
            row["Average Strategy Sell Price"],
            row["Total Savings"]
        ]
        # Replace $nan with '-'
        row_data = [str(cell) if cell != "$nan" else "-" for cell in row_data]
        data.append([Paragraph(str(cell), normal_style) for cell in row_data])  # Fill cells with data
    # Create the table with the rows in a 5 columns
    table = Table(data,rowHeights=[60,50,50,50,50,50],colWidths=[doc.width * .2, doc.width * .2, doc.width * .2, doc.width * .2, doc.width * .2, doc.width * .2])  
    table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),  # Add a black border around the whole table
        ('LINEBEFORE', (1, 0), (-1, -1), 1, colors.black),  # Add a black border around the whole table
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),  # Add a black border around the whole table
        ('TOPPADDING', (0, 0), (-1, -1), 12),  # Vertically align text in the middle
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),  # Vertically align text in the middle
        ('LEFTPADDING', (0, 0), (-1, -1), 14),  # Vertically align text in the middle
        ('RIGHTPADDING', (0, -1), (-1, -1), 14),  # Vertically align text in the middle
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align content in the middle
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Horizontally align content in the middle
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C3F53C')),  # Add background color to the first row (highlighted)
        
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    #go to next page
    elements.append(PageBreak())
    # Create data for the table For Header
    data = [
        [Paragraph('Your Top 5 Trades with the', title_style)],  # First row
        [Paragraph('Worst Executions', title_style2)],  # second row
    ]

    # Create the table with the rows in a single column
    table = Table(data, colWidths=[10*inch])  # Set a wide column width to fit all text

    # Define the style of the table to add padding and other styling options
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align text in the middle
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Vertically align text in the middle
        ('LEAING', (0, 0), (0, 0), 40),  # Vertically align text in the middle
        ('LEADING', (0, 1), (0, 1), 32),  # Vertically align text in the middle
        ('TOPPADDING', (0, 1), (0, 1), -7),  # Vertically align text in the middle
        ('TOPPADDING', (0, 2), (0, 2), -2),  # Vertically align text in the middle
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
          # Create data for the table For Header
    data = [
        [
            Paragraph('Date', table_header_small),
            Paragraph('Direction', table_header_small),
            Paragraph('Stock', table_header_small),
            Paragraph('Executed Price', table_header_small),
            Paragraph('TWAP Price', table_header_small),
            Paragraph('Slippage', table_header_small),
            Paragraph('Order Size', table_header_small),
            Paragraph('Market Condition', table_header_small),
           
        ],
    ]
    # Fill cells with table data
    for row in table_data:
        row_data = [
            row["Date"],
            row["Direction"],
            row["Stock"],
            row["Executed Price"],
            row["TWAP Price"],
            row["Slippage"],
            row["Order Size"],
            row["Market Condition"]
        ]
        data.append([Paragraph(str(cell), normal_style) for cell in row_data])  # Fill cells with data
    # Create the table with the rows in a 5 columns
    table = Table(data, rowHeights=[None] * len(data), colWidths=[doc.width * .130] * 3 + [doc.width * .165] * 2 + [doc.width * .130] * 2 + [doc.width * .2])  
    table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),  # Add a black border around the whole table
        ('LINEBEFORE', (1, 0), (-1, -1), 1, colors.black),  # Add a black border around the whole table
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),  # Add a black border around the whole table
        ('LINEBELOW', (0, 1), (-1, -1), 1, colors.black),  # Added horizontal lines after each row
        ('TOPPADDING', (0, 0), (-1, -1), 12),  # Vertically align text in the middle
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),  # Vertically align text in the middle
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align content in the middle
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Horizontally align content in the middle
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C3F53C')),  # Add background color to the first row (highlighted)
    ]))
    
    elements.append(table)
    #go to next page
    elements.append(PageBreak())

    # ________________________-_________________________- PAGE 6 - __________________________________________________________
    
    #add subtitle - How Can I Use Your Analytics to Improve My Trades?
    elements.append(Paragraph('How Can I Use Your Analytics to <font  backcolor="#C3F53C">&nbsp;Improve&nbsp;</font> My Trades?', styles['Subtitle30']))  # Use new subtitle style
    elements.append(Spacer(1, 0.2*inch))

    elements.append(Spacer(1, 0.2*inch))  # Add space between boxes
    #crate box with text
    box_width = 2.5 * inch
    box5 = create_box2('', 'For personalized assistance and to start implementing these recommendations, please contact our support team. We are here to help you achieve better trading outcomes and maximize your profits. For options TCA, forward looking recommendations, and backtesting more complex execution strategies consider signing up for Hoodwinked Pro.', box_width, 80 )
    # Set the background color for box5
    box5.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#C3F53C')),  # Updated background color
    ]))
    elements.append(box5)


    elements.append(Spacer(1, 0.2*inch))  # Add space between boxes
    elements.append(Spacer(1, 0.2*inch))  # Add space between boxes
    elements.append(Spacer(1, 0.2*inch))  # Add space between boxes
    #add subtitle - How Can I Use Your Analytics to Improve My Trades?
    elements.append(Paragraph('Frequently Asked Questions <font  backcolor="#C3F53C">&nbsp;(FAQ)&nbsp;</font> Section', styles['Subtitle30']))  # Use new subtitle style
    elements.append(Spacer(1, 0.2*inch))

    elements.append(Spacer(1, 0.2*inch))  # Add space between boxes
    #crate box with text
    box_width = 2.5 * inch
    box5 = create_box2('Why should I care about <font  backcolor="#C3F53C">&nbsp;trade execution&nbsp;</font>?', 'There are two things that affect your trading returns, the investment idea you have (alpha) and how you BUY / SELL the asset. If you put a large market order in at one time, or put in orders when markets are highly volatile, then there is a good chance you could be eating into your trading returns with bad trade prices. Save your hard-earned alpha by executing your trades at the right timing, sizing, and order type. In this report, we compare your trades to four different execution strategies for the same stocks within the same week, over the last two years of trades, and show you how much excess returns you could have made by planning and trading in different ways.', box_width, 170 )
    
    elements.append(box5)

    #go to next page
    elements.append(PageBreak())

    # ________________________-_________________________- PAGE 7 - __________________________________________________________
    
    #crate box with text
    box_width = 2.5 * inch
    box5 = create_box2('What is <font  backcolor="#C3F53C">&nbsp;slippage&nbsp;</font>, and what do Open, Close, TWAP, VWAP, and HWOE mean?', 
                      'Slippage is the word used by traders to describe the difference in your expected price and the price you traded at. In this report, we are comparing your trade prices to the prices you would expect with different execution strategies. The slippage for a BUY = your_price – strategy_price, and the slippage for SELL = strategy_price – your_price. With these formulas a positive value means that the strategy_price was better than your execution (your BUY was higher than strategy BUY, your SELL was lower than strategy sell) The charts and values we are displaying in this report are the difference (slippage) between YOUR trade prices and 5 different strategies. Open and Close represent the strategy of buying at market “Open” or “Close” on the same day you traded. TWAP represents the strategy of splitting your order into equal size pieces and buying that many shares at the start of every hour during the same day  you traded. VWAP is similar to TWAP, but instead of equal size pieces, the size of each individual order gets adjusted depending on how much volume is expected to be traded that hour (more volume expected means larger chunk is traded). The HWOE strategy represents our own algorithm, which chooses the best time during the week you traded to perform the trade, and splits order sizes depending on a host of different market liquidity factors. As displayed in the charts in section 2, HWOE does far better than TWAP / VWAP on an average trade basis, and results in significant trade savings over time.', 
                      box_width, 380 )
    
    elements.append(box5)
    
    return elements
